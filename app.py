import json
import csv
import io
import re
import time
import requests
from datetime import datetime, timedelta, timezone

import streamlit as st

from config import (
    CLIENT_ID, CLIENT_SECRET,
    FRANCE_TRAVAIL_TOKEN_URL, FRANCE_TRAVAIL_SEARCH_URL,
    DEPARTEMENTS, DEPT_LABELS,
    SCORE_HIGH, SCORE_MODERATE, TOKEN_TTL,
)
from db import (
    init_db, insert_job, insert_score, insert_review_queue,
    update_review_status, get_leads, get_job_description,
    get_stats, get_approved_leads_for_export,
)
from scorer import score_job
from hypothesis import generate_hypothesis, generate_offer_angle

# ── DB init on every cold start ───────────────────────────────────────────────
init_db()

st.set_page_config(page_title="Leads Automation — PACA", layout="wide")

# ── Token cache (session-scoped) ──────────────────────────────────────────────
if "ft_token" not in st.session_state:
    st.session_state.ft_token = None
    st.session_state.ft_token_expires = 0.0
if "collect_log" not in st.session_state:
    st.session_state.collect_log = []


def get_token() -> str:
    now = time.time()
    if st.session_state.ft_token and now < st.session_state.ft_token_expires:
        return st.session_state.ft_token

    resp = requests.post(
        FRANCE_TRAVAIL_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
        auth=(CLIENT_ID, CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    if resp.status_code != 200:
        st.error(
            f"Erreur token France Travail — HTTP {resp.status_code}\n\n"
            f"Réponse : {resp.text[:500]}"
        )
        st.stop()
    data = resp.json()
    if "access_token" not in data:
        st.error(f"Réponse token inattendue : {str(data)[:500]}")
        st.stop()
    st.session_state.ft_token = data["access_token"]
    st.session_state.ft_token_expires = now + TOKEN_TTL
    return st.session_state.ft_token


def fetch_dept(dept: str, min_date: str, max_date: str, token: str, log_fn) -> list:
    listings = []
    start = 0
    page_size = 150

    while True:
        params = {
            "departement": dept,
            "minCreationDate": min_date,
            "maxCreationDate": max_date,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Range": f"offres={start}-{start + page_size - 1}",
            "Accept": "application/json",
        }

        resp = requests.get(
            FRANCE_TRAVAIL_SEARCH_URL, params=params, headers=headers, timeout=20
        )

        if resp.status_code == 401:
            log_fn(f"❌ [{dept}] Token expiré — rechargez la page pour rafraîchir.")
            break

        if resp.status_code == 429:
            log_fn(f"⏳ [{dept}] Rate limit, retry dans 2s...")
            time.sleep(2)
            resp = requests.get(
                FRANCE_TRAVAIL_SEARCH_URL, params=params, headers=headers, timeout=20
            )
            if resp.status_code == 429:
                log_fn(f"❌ [{dept}] Rate limit persistant, page ignorée.")
                break

        if resp.status_code in (200, 206):
            data = resp.json()
            results = data.get("resultats", [])
            listings.extend(results)
            log_fn(f"  [{dept}] start={start} → {len(results)} offres")

            content_range = resp.headers.get("Content-Range", "")
            try:
                total = int(content_range.split("/")[1]) if content_range else 0
            except (IndexError, ValueError):
                total = 0

            if total and start + page_size >= total:
                break
            if len(results) < page_size:
                break
            start += page_size
        else:
            log_fn(f"❌ [{dept}] HTTP {resp.status_code}: {resp.text[:500]}")
            break

    return listings


def parse_listing(raw: dict, dept: str, fetched_at: str) -> dict | None:
    job_id = raw.get("id")
    title = (raw.get("intitule") or "").strip()
    description = (raw.get("description") or "").strip()

    if not job_id or not title or not description:
        return None

    entreprise = raw.get("entreprise") or {}
    company_name = (entreprise.get("nom") or "Inconnu").strip()

    source_url = (raw.get("origineOffre") or {}).get("urlOrigine") or (
        f"https://candidat.francetravail.fr/offres/recherche/detail/{job_id}"
    )

    return {
        "id": job_id,
        "source": "france_travail",
        "source_url": source_url,
        "title": title,
        "company_name": company_name,
        "company_sector": raw.get("secteurActiviteLibelle") or "",
        "location_text": (raw.get("lieuTravail") or {}).get("libelle") or "",
        "departement": dept,
        "contract_type": raw.get("typeContratLibelle") or "",
        "posted_at": raw.get("dateCreation") or "",
        "description_raw": description,
        "description_clean": description.lower().strip(),
        "salary_text": (raw.get("salaire") or {}).get("libelle") or "",
        "fetched_at": fetched_at,
    }


def run_fetch(selected_depts: list, log_fn) -> tuple[int, int]:
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error("Identifiants manquants — configurez FRANCE_TRAVAIL_CLIENT_ID et CLIENT_SECRET.")
        st.stop()

    token = get_token()
    now_dt = datetime.now(timezone.utc)
    since = (now_dt - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    until = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    fetched_at = now_dt.isoformat()

    total_new = 0
    total_scored = 0

    for dept in selected_depts:
        log_fn(f"📡 Département {DEPT_LABELS.get(dept, dept)}...")
        listings = fetch_dept(dept, since, until, token, log_fn)
        log_fn(f"  → {len(listings)} offres récupérées")

        for raw in listings:
            job = parse_listing(raw, dept, fetched_at)
            if job is None:
                continue

            inserted = insert_job(job)
            if not inserted:
                continue

            total_new += 1
            result = score_job(job["title"], job["description_clean"])

            hypothesis = generate_hypothesis(
                result["_rep_matches"], result["_struct_matches"],
                result["_output_matches"], job["title"], job["company_name"],
            )
            offer_angle = generate_offer_angle(
                result["automation_score"], result["_rep_matches"], result["_struct_matches"],
            )

            insert_score({
                "job_id": job["id"],
                "automation_score": result["automation_score"],
                "repetitive_signal_score": result["repetitive_signal_score"],
                "structured_input_score": result["structured_input_score"],
                "measurable_output_score": result["measurable_output_score"],
                "human_judgment_penalty": result["human_judgment_penalty"],
                "matched_signals": result["matched_signals"],
                "hypothesis": hypothesis,
                "offer_angle": offer_angle,
            })
            insert_review_queue(job["id"])
            total_scored += 1

    return total_new, total_scored


# ── UI helpers ────────────────────────────────────────────────────────────────

def score_badge(score: int) -> str:
    if score >= SCORE_HIGH:
        return f"🟢 {score}"
    elif score >= SCORE_MODERATE:
        return f"🟠 {score}"
    return f"🔴 {score}"


def truncate(text: str, n: int = 120) -> str:
    if not text:
        return ""
    return text[:n] + "…" if len(text) > n else text


# ── Header ────────────────────────────────────────────────────────────────────

st.title("Leads Automation — PACA")

stats = get_stats()
c1, c2, c3 = st.columns(3)
c1.metric("En attente", stats["pending"])
c2.metric("Approuvés", stats["approved"])
c3.metric("Dernière collecte", stats["last_fetch"] or "jamais")

st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Collecte")

    fetch_depts = st.multiselect(
        "Départements à collecter",
        options=DEPARTEMENTS,
        default=DEPARTEMENTS,
        format_func=lambda d: DEPT_LABELS.get(d, d),
    )

    if st.button("🔄 Collecter les nouvelles offres", type="primary", use_container_width=True):
        if not fetch_depts:
            st.warning("Sélectionnez au moins un département.")
        else:
            st.session_state.collect_log = []
            log_box = st.empty()

            def log(msg):
                st.session_state.collect_log.append(msg)
                log_box.text("\n".join(st.session_state.collect_log[-30:]))

            with st.spinner("Collecte en cours..."):
                new_count, scored_count = run_fetch(fetch_depts, log)

            st.success(f"✅ {new_count} nouvelles offres ajoutées, {scored_count} scorées.")
            st.rerun()

    if st.session_state.collect_log:
        st.text_area("Journal", "\n".join(st.session_state.collect_log), height=200)
        if st.button("Effacer le journal"):
            st.session_state.collect_log = []
            st.rerun()

    st.divider()
    st.header("Filtres")

    min_score = st.slider("Score minimum", 0, 100, 60, step=5)

    filter_depts = st.multiselect(
        "Département",
        options=DEPARTEMENTS,
        default=DEPARTEMENTS,
        format_func=lambda d: DEPT_LABELS.get(d, d),
        key="filter_depts",
    )

    status_options = ["pending", "approved", "rejected", "snoozed"]
    selected_statuses = st.multiselect(
        "Statut",
        options=status_options,
        default=["pending"],
    )

    show_low_fit = st.toggle("Afficher les leads faible potentiel (<60)", value=False)

# ── Lead list ─────────────────────────────────────────────────────────────────

leads = get_leads(
    min_score=min_score,
    departements=filter_depts or None,
    statuses=selected_statuses or None,
    include_low_fit=show_low_fit,
)

st.subheader(f"{len(leads)} lead(s) trouvé(s)")

if not leads:
    st.info("Aucun lead. Utilisez le bouton **Collecter** dans la barre latérale.")

for lead in leads:
    score = lead["automation_score"] or 0
    try:
        signals = json.loads(lead.get("matched_signals") or "[]")
    except Exception:
        signals = []
    top_signals = ", ".join(signals[:4]) or "—"
    status = lead.get("status") or "pending"

    label = (
        f"{score_badge(score)} — **{lead['company_name'] or 'Inconnu'}** | "
        f"{lead['title']} | {lead['location_text'] or ''} | `{status.upper()}`"
    )

    with st.expander(label):
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown(f"**Secteur :** {lead.get('company_sector') or '—'}")
            st.markdown(f"**Département :** {DEPT_LABELS.get(lead.get('departement'), lead.get('departement') or '—')}")
            st.markdown(f"**Contrat :** {lead.get('contract_type') or '—'}")
            st.markdown(f"**Publié le :** {lead.get('posted_at') or '—'}")
            if lead.get("source_url"):
                st.markdown(f"[Voir l'offre ↗]({lead['source_url']})")

            st.markdown(f"**Signaux :** {top_signals}")

            hypothesis = lead.get("hypothesis") or ""
            st.markdown("**Hypothèse :**")
            st.markdown(truncate(hypothesis, 300))
            if len(hypothesis) > 300:
                with st.popover("Lire la suite"):
                    st.write(hypothesis)

            st.markdown(f"**Angle :** {lead.get('offer_angle') or '—'}")

            with st.expander("Description complète"):
                st.text(get_job_description(lead["id"]))

        with col_right:
            st.markdown("**Scores détaillés**")
            st.markdown(f"- Répétitif : {lead.get('repetitive_signal_score', 0)}")
            st.markdown(f"- Structuré : {lead.get('structured_input_score', 0)}")
            st.markdown(f"- Mesurable : {lead.get('measurable_output_score', 0)}")
            st.markdown(f"- Pénalité : -{lead.get('human_judgment_penalty', 0)}")
            st.markdown(f"- **Total : {score}**")

        st.markdown("---")
        notes_key = f"notes_{lead['id']}"
        notes = st.text_area("Notes", value=lead.get("reviewer_notes") or "", key=notes_key, height=70)

        b1, b2, b3 = st.columns(3)
        if b1.button("✅ Approuver", key=f"approve_{lead['id']}", type="primary"):
            update_review_status(lead["id"], "approved", notes)
            st.rerun()
        if b2.button("❌ Rejeter", key=f"reject_{lead['id']}"):
            update_review_status(lead["id"], "rejected", notes)
            st.rerun()
        if b3.button("⏸ Snooze", key=f"snooze_{lead['id']}"):
            update_review_status(lead["id"], "snoozed", notes)
            st.rerun()

# ── Export ────────────────────────────────────────────────────────────────────

st.divider()
if st.button("📥 Exporter les leads approuvés (CSV)"):
    approved = get_approved_leads_for_export()
    if not approved:
        st.warning("Aucun lead approuvé à exporter.")
    else:
        def extract_emails(text: str) -> str:
            return " | ".join(re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text or ""))

        def extract_phones(text: str) -> str:
            pattern = r"(?:(?:\+|00)33[\s.\-]?|0)[1-9](?:[\s.\-]?\d{2}){4}"
            return " | ".join(re.findall(pattern, text or ""))

        def extract_websites(text: str) -> str:
            return " | ".join(re.findall(r"https?://[^\s\"'<>]+", text or ""))

        def clean(text: str) -> str:
            return re.sub(r"[\r\n]+", " ", text or "").strip()

        fieldnames = [
            "Entreprise", "Poste", "Lieu", "Secteur",
            "Lien offre", "Publié le",
            "Email", "Téléphone", "Site web",
            "Score automation", "Signaux", "Hypothèse", "Angle",
            "Notes",
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in approved:
            desc = row.get("description_raw") or ""
            writer.writerow({
                "Entreprise": clean(row.get("company_name")),
                "Poste": clean(row.get("title")),
                "Lieu": clean(row.get("location_text")),
                "Secteur": clean(row.get("company_sector")),
                "Lien offre": row.get("source_url") or "",
                "Publié le": row.get("posted_at") or "",
                "Email": extract_emails(desc),
                "Téléphone": extract_phones(desc),
                "Site web": extract_websites(desc),
                "Score automation": row.get("automation_score") or "",
                "Signaux": clean(row.get("matched_signals")),
                "Hypothèse": clean(row.get("hypothesis")),
                "Angle": clean(row.get("offer_angle")),
                "Notes": clean(row.get("reviewer_notes")),
            })

        st.download_button(
            label="Télécharger leads_approuves.csv",
            data=output.getvalue().encode("utf-8-sig"),
            file_name="leads_approuves.csv",
            mime="text/csv",
        )
