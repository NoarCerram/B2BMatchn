import json

REPETITIVE_SIGNALS = [
    "saisie", "saisie de données", "relances", "relance", "suivi", "mise à jour",
    "traitement", "traitement de dossiers", "gestion des dossiers", "reporting",
    "rapports", "planification", "coordination", "prise de rendez-vous",
    "gestion des emails", "tri", "classement", "archivage", "back-office",
    "administration", "assistanat", "secrétariat",
    "data entry", "follow-up", "follow up", "scheduling",
    "tracking", "processing", "administrative support", "back office",
    "coordination", "inbox management", "filing", "logging",
]

STRUCTURED_INPUT_SIGNALS = [
    "excel", "google sheets", "tableur", "crm", "erp", "logiciel", "outil",
    "formulaire", "base de données", "salesforce", "hubspot", "sage",
    "dossiers", "documents", "pièces justificatives", "factures", "bons de commande",
    "ats", "applicant tracking", "candidatures",
    "spreadsheet", "database", "forms", "invoices", "purchase orders",
    "ticketing", "helpdesk",
]

MEASURABLE_OUTPUT_SIGNALS = [
    "volume", "délai", "fréquence", "hebdomadaire", "mensuel", "quotidien",
    "indicateurs", "kpi", "tableaux de bord", "tableau de bord",
    "nombre de", "traiter", "gérer",
    "daily", "weekly", "monthly", "throughput",
    "dashboard", "metrics", "turnaround",
]

TITLE_SIGNALS = [
    "assistant administratif", "assistante administrative", "chargé de",
    "gestionnaire", "coordinateur", "coordinatrice", "office manager",
    "assistant rh", "assistante rh", "assistant comptable", "chargé de gestion",
    "responsable back office", "technicien de saisie", "opérateur de saisie",
    "assistant commercial", "assistant marketing", "chargé de reporting",
    "operations coordinator", "administrative assistant", "data coordinator",
    "sales operations", "marketing operations", "recruitment coordinator",
    "finance assistant", "accounts payable", "order management",
]

PENALTY_SIGNALS = [
    "directeur", "directrice", "direction", "stratégie", "stratégique",
    "développement commercial senior", "conseil", "consulting", "associé",
    "thérapie", "thérapeute", "psychologue", "médecin", "avocat", "notaire",
    "création artistique", "direction artistique", "conception créative",
    "director", "vp ", "vice president", "chief ", "head of",
    "strategy", "senior partner", "therapist", "attorney", "creative director",
]

POINTS_PER_HIT = 20
MAX_SUB_SCORE = 100


def _match(text: str, signals: list) -> list:
    return [s for s in signals if s in text]


def _sub_score(matches: list) -> int:
    return min(MAX_SUB_SCORE, len(matches) * POINTS_PER_HIT)


def score_job(title: str, description_clean: str) -> dict:
    title_lower = title.lower()
    text = description_clean  # already lowercased

    rep_matches = _match(text, REPETITIVE_SIGNALS) + _match(title_lower, REPETITIVE_SIGNALS)
    struct_matches = _match(text, STRUCTURED_INPUT_SIGNALS) + _match(title_lower, STRUCTURED_INPUT_SIGNALS)
    output_matches = _match(text, MEASURABLE_OUTPUT_SIGNALS) + _match(title_lower, MEASURABLE_OUTPUT_SIGNALS)
    title_matches = _match(title_lower, TITLE_SIGNALS)
    penalty_matches = _match(text, PENALTY_SIGNALS) + _match(title_lower, PENALTY_SIGNALS)

    # Deduplicate
    rep_matches = list(dict.fromkeys(rep_matches))
    struct_matches = list(dict.fromkeys(struct_matches))
    output_matches = list(dict.fromkeys(output_matches))
    title_matches = list(dict.fromkeys(title_matches))
    penalty_matches = list(dict.fromkeys(penalty_matches))

    rep_score = _sub_score(rep_matches)
    struct_score = _sub_score(struct_matches)
    output_score = _sub_score(output_matches)
    title_score = _sub_score(title_matches)
    penalty_score = _sub_score(penalty_matches)

    raw = (
        rep_score * 0.30
        + struct_score * 0.25
        + output_score * 0.20
        + title_score * 0.15
        - penalty_score * 0.20
    )
    final_score = int(max(0, min(100, raw)))

    all_matched = rep_matches + struct_matches + output_matches + title_matches

    return {
        "automation_score": final_score,
        "repetitive_signal_score": rep_score,
        "structured_input_score": struct_score,
        "measurable_output_score": output_score,
        "human_judgment_penalty": penalty_score,
        "matched_signals": json.dumps(list(dict.fromkeys(all_matched))),
        "_rep_matches": rep_matches,
        "_struct_matches": struct_matches,
        "_output_matches": output_matches,
    }
