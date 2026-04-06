import os

try:
    import streamlit as st
    CLIENT_ID = st.secrets.get("FRANCE_TRAVAIL_CLIENT_ID") or os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
    CLIENT_SECRET = st.secrets.get("FRANCE_TRAVAIL_CLIENT_SECRET") or os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
except Exception:
    CLIENT_ID = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
    CLIENT_SECRET = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")

FRANCE_TRAVAIL_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
)
FRANCE_TRAVAIL_SEARCH_URL = (
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
)

DEPARTEMENTS = ["06", "13", "83", "84", "04", "05"]

DEPT_LABELS = {
    "06": "06 — Alpes-Maritimes",
    "13": "13 — Bouches-du-Rhône",
    "83": "83 — Var",
    "84": "84 — Vaucluse",
    "04": "04 — Alpes-de-Haute-Provence",
    "05": "05 — Hautes-Alpes",
}

SCORE_HIGH = 80
SCORE_MODERATE = 60
TOKEN_TTL = 1499

DB_PATH = "leads.db"
