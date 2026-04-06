# PRD: Job-Board Automation Lead Scanner (Refined for Claude Code)

## Context and goal

This is a local tool that runs on a laptop, manually triggered. Its job is to pull job listings from France Travail for the PACA region, score them for automation potential using keyword rules, generate a plain-language outreach hypothesis for each, and present a simple dashboard where leads can be reviewed and approved.

The person using it is an automation consultant looking for companies to pitch. Week 1 is internal use only. The tool may later be productised.

No schedulers, no cloud, no LLM calls, no paid APIs, no crawling. Everything runs locally.

---

## Tech stack (decided, not optional)

- **Language:** Python 3.11+
- **Database:** SQLite (single file, local, no server needed)
- **Dashboard:** Streamlit
- **HTTP:** `requests` library for France Travail API calls
- **No ORM needed:** raw SQL with sqlite3 is fine
- **Dependencies managed via:** `requirements.txt`

---

## How it runs

The user runs two commands:

```
python fetch.py       # pulls new listings, scores them, saves to DB
streamlit run app.py  # opens the dashboard in browser
```

That is the entire interface. No daemon, no cron, no background workers.

---

## Data source

**France Travail API Offres d'emploi** — official REST API, requires a registered client ID and secret (OAuth2 client credentials flow).

Base URL: `https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search`

### Region filter

PACA region only. Filter by `departement` parameter using codes:
- `06` — Alpes-Maritimes (Nice, Antibes, Sophia Antipolis)
- `13` — Bouches-du-Rhône (Marseille, Aix-en-Provence)
- `83` — Var (Toulon, Fréjus)
- `84` — Vaucluse (Avignon)
- `04` — Alpes-de-Haute-Provence
- `05` — Hautes-Alpes

Note: Monaco is not in France and will not appear in France Travail data.

### Fetch logic

- Fetch runs per-département in a loop
- Paginate through results using `start` and `range` parameters (France Travail returns max 150 per call)
- Only fetch listings published in the last 7 days (use `minCreationDate` param)
- Store raw JSON response per listing
- Deduplicate by `id` field from the API (France Travail's own listing ID)

### Auth

France Travail uses OAuth2 client credentials. The fetch script should:
1. POST to token endpoint with client_id and client_secret from `.env` file
2. Use bearer token for all subsequent requests
3. Refresh token when expired (token TTL is 1499 seconds)

---

## Data model (SQLite)

### table: jobs

```sql
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,                -- France Travail listing ID
    source TEXT DEFAULT 'france_travail',
    source_url TEXT,
    title TEXT,
    company_name TEXT,
    company_sector TEXT,
    location_text TEXT,
    departement TEXT,
    contract_type TEXT,
    posted_at TEXT,
    description_raw TEXT,
    description_clean TEXT,             -- lowercased, stripped
    salary_text TEXT,
    fetched_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### table: lead_scores

```sql
CREATE TABLE IF NOT EXISTS lead_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT REFERENCES jobs(id),
    automation_score INTEGER,           -- 0 to 100
    repetitive_signal_score INTEGER,
    structured_input_score INTEGER,
    measurable_output_score INTEGER,
    human_judgment_penalty INTEGER,
    matched_signals TEXT,               -- JSON array of matched keyword strings
    hypothesis TEXT,                    -- generated outreach hypothesis
    offer_angle TEXT,                   -- suggested pitch
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### table: review_queue

```sql
CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT REFERENCES jobs(id),
    status TEXT DEFAULT 'pending',      -- pending / approved / rejected / snoozed
    reviewer_notes TEXT,
    outreach_angle TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## Scoring engine

Pure Python, rule-based. No ML, no embeddings, no API calls.

### Scoring formula

Final score (0–100) is computed as:

```
score = (
    repetitive_signal_score * 0.30
  + structured_input_score   * 0.25
  + measurable_output_score  * 0.20
  + role_title_match_score   * 0.15
  - human_judgment_penalty   * 0.20
)
score = max(0, min(100, score))
```

Each sub-score runs from 0 to 100 based on keyword hits, capped and scaled.

### Keyword dictionaries (French-first, English secondary)

All matching is case-insensitive against `description_clean` and `title`.

#### Repetitive task signals (repetitive_signal_score)

Each match adds points. Cap at 100.

```python
REPETITIVE_SIGNALS = [
    # French
    "saisie", "saisie de données", "relances", "relance", "suivi", "mise à jour",
    "traitement", "traitement de dossiers", "gestion des dossiers", "reporting",
    "rapports", "planification", "coordination", "prise de rendez-vous",
    "gestion des emails", "tri", "classement", "archivage", "back-office",
    "administration", "assistanat", "secrétariat",
    # English
    "data entry", "follow-up", "follow up", "reporting", "scheduling",
    "tracking", "processing", "administrative support", "back office",
    "coordination", "inbox management", "filing", "logging"
]
```

#### Structured input signals (structured_input_score)

```python
STRUCTURED_INPUT_SIGNALS = [
    # French
    "excel", "google sheets", "tableur", "crm", "erp", "logiciel", "outil",
    "formulaire", "base de données", "salesforce", "hubspot", "sage",
    "dossiers", "documents", "pièces justificatives", "factures", "bons de commande",
    "ats", "applicant tracking", "candidatures",
    # English
    "spreadsheet", "database", "forms", "invoices", "purchase orders",
    "crm", "erp", "ticketing", "helpdesk"
]
```

#### Measurable output signals (measurable_output_score)

```python
MEASURABLE_OUTPUT_SIGNALS = [
    # French
    "volume", "délai", "fréquence", "hebdomadaire", "mensuel", "quotidien",
    "indicateurs", "kpi", "tableaux de bord", "tableau de bord",
    "nombre de", "traiter X", "gérer X dossiers",
    # English
    "daily", "weekly", "monthly", "volume", "throughput", "kpi",
    "dashboard", "metrics", "turnaround"
]
```

#### Role title match signals (role_title_match_score)

Check against `title` field only.

```python
TITLE_SIGNALS = [
    # French
    "assistant administratif", "assistante administrative", "chargé de",
    "gestionnaire", "coordinateur", "coordinatrice", "office manager",
    "assistant rh", "assistante rh", "assistant comptable", "chargé de gestion",
    "responsable back office", "technicien de saisie", "opérateur de saisie",
    "assistant commercial", "assistant marketing", "chargé de reporting",
    # English
    "operations coordinator", "administrative assistant", "data coordinator",
    "sales operations", "marketing operations", "recruitment coordinator",
    "finance assistant", "accounts payable", "order management"
]
```

#### Human judgment penalties (human_judgment_penalty)

```python
PENALTY_SIGNALS = [
    # French
    "directeur", "directrice", "direction", "stratégie", "stratégique",
    "développement commercial senior", "conseil", "consulting", "associé",
    "thérapie", "thérapeute", "psychologue", "médecin", "avocat", "notaire",
    "création artistique", "direction artistique", "conception créative",
    # English
    "director", "vp ", "vice president", "chief ", "head of",
    "strategy", "senior partner", "therapist", "attorney", "creative director"
]
```

### Score bands

- 80–100: high fit (shown first in dashboard)
- 60–79: moderate fit (shown second)
- Below 60: low fit (filtered out by default, toggle to show)

---

## Hypothesis generation

Pure Python string templates. No API calls.

Each hypothesis is assembled from the matched signal categories.

```python
def generate_hypothesis(matched_repetitive, matched_structured, matched_output, title, company):
    parts = []

    if matched_repetitive:
        parts.append(
            f"Ce poste implique des tâches récurrentes : {', '.join(matched_repetitive[:3])}."
        )
    if matched_structured:
        parts.append(
            f"L'environnement de travail repose sur des outils structurés : {', '.join(matched_structured[:3])}."
        )
    if matched_output:
        parts.append(
            f"Des livrables mesurables sont attendus ({', '.join(matched_output[:2])})."
        )

    hypothesis = " ".join(parts)
    hypothesis += (
        f" {company} recrute probablement pour absorber un volume de travail manuel "
        f"qui pourrait être partiellement automatisé."
    )
    return hypothesis


def generate_offer_angle(score, matched_repetitive, matched_structured):
    if score >= 80:
        return "Proposition : audit de workflow + pilote d'automatisation (reporting, saisie, relances)."
    elif score >= 60:
        return "Proposition : diagnostic rapide pour identifier les tâches à fort ROI d'automatisation."
    else:
        return "Potentiel limité — à évaluer manuellement."
```

---

## Dashboard (Streamlit app.py)

Single-page Streamlit app. Layout:

### Header
- Title: "Leads Automation — PACA"
- Last fetch timestamp
- Count: X leads pending review, Y approved

### Filters (sidebar)
- Score minimum (slider, default 60)
- Département (multiselect, default all)
- Status filter (pending / approved / rejected / all)
- Show low-fit toggle (default off)

### Lead table
Columns shown:
- Score (coloured: green ≥80, orange 60–79)
- Company name
- Job title
- Location
- Department / sector
- Top matched signals (comma-separated, max 4)
- Hypothesis (truncated to 120 chars, expandable)
- Offer angle
- Status badge
- Link to France Travail listing (clickable)

### Lead detail (click to expand or sidebar panel)
- Full job description
- All matched signals with category labels
- Full hypothesis text
- Offer angle
- Action buttons: Approve / Reject / Snooze
- Notes text area (saved to review_queue)

### Export
- "Export approved leads to CSV" button at bottom
- CSV columns: company, title, location, sector, score, signals, hypothesis, offer_angle, source_url, status, notes, posted_at

---

## File structure

```
/
├── fetch.py              # pulls from France Travail API, scores, saves to DB
├── app.py                # Streamlit dashboard
├── scorer.py             # scoring logic and keyword dictionaries
├── hypothesis.py         # hypothesis and offer angle generation
├── db.py                 # SQLite helpers (init, insert, query)
├── config.py             # loads .env, holds constants (score thresholds, dept codes)
├── .env                  # FRANCE_TRAVAIL_CLIENT_ID, FRANCE_TRAVAIL_CLIENT_SECRET
├── requirements.txt
└── leads.db              # auto-created on first run
```

---

## Environment variables (.env)

```
FRANCE_TRAVAIL_CLIENT_ID=your_client_id
FRANCE_TRAVAIL_CLIENT_SECRET=your_client_secret
```

---

## requirements.txt

```
requests
streamlit
python-dotenv
```

---

## Error handling

- If France Travail API returns 401, print clear message: "Token expired or credentials invalid — check .env"
- If API returns 429 (rate limit), wait 2 seconds and retry once
- If a listing is missing required fields (title, description), skip and log to console
- All errors print to console with the listing ID and reason — no silent failures

---

## What is explicitly out of scope

- No scheduler or cron — run manually
- No LLM calls — pure rules only
- No external enrichment APIs
- No email sending
- No user authentication on the dashboard
- No cloud deployment
- No Monaco data (not in France Travail)
- No multi-country support
- No vector search or embeddings
- No Indeed scraping

---

## France Travail API registration description (for the application form)

Use this text verbatim or adapt it for the registration:

> "Nous développons un outil interne d'analyse des offres d'emploi à des fins de prospection commerciale B2B. L'outil interroge l'API Offres d'emploi pour identifier les entreprises qui recrutent sur des postes à fort potentiel d'automatisation de processus (saisie, reporting, coordination back-office). Les données sont utilisées uniquement en lecture pour générer des pistes commerciales qualifiées. Aucune donnée personnelle de candidats n'est collectée ni stockée. L'accès est réservé à un usage interne sur notre propre infrastructure. Le volume de requêtes sera limité à une synchronisation quotidienne ou hebdomadaire par département."

---

## Definition of done for week 1

- `fetch.py` runs without errors and saves scored leads to `leads.db`
- At least one PACA département returns real listings
- Each listing in DB has a score, matched signals, hypothesis, and offer angle
- Dashboard opens in browser and shows leads filtered by score
- Approve/reject actions persist to DB
- CSV export works
- Setup takes under 30 minutes from a fresh clone (documented in a short setup note, not a README essay)
