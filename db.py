import sqlite3
from config import DB_PATH


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
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
            description_clean TEXT,
            salary_text TEXT,
            fetched_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lead_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT REFERENCES jobs(id),
            automation_score INTEGER,
            repetitive_signal_score INTEGER,
            structured_input_score INTEGER,
            measurable_output_score INTEGER,
            human_judgment_penalty INTEGER,
            matched_signals TEXT,
            hypothesis TEXT,
            offer_angle TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT REFERENCES jobs(id),
            status TEXT DEFAULT 'pending',
            reviewer_notes TEXT,
            outreach_angle TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def insert_job(job: dict) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO jobs
            (id, source, source_url, title, company_name, company_sector,
             location_text, departement, contract_type, posted_at,
             description_raw, description_clean, salary_text, fetched_at)
        VALUES
            (:id, :source, :source_url, :title, :company_name, :company_sector,
             :location_text, :departement, :contract_type, :posted_at,
             :description_raw, :description_clean, :salary_text, :fetched_at)
    """, job)
    inserted = cur.rowcount == 1
    conn.commit()
    conn.close()
    return inserted


def insert_score(score: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM lead_scores WHERE job_id = ?", (score["job_id"],))
    cur.execute("""
        INSERT INTO lead_scores
            (job_id, automation_score, repetitive_signal_score,
             structured_input_score, measurable_output_score,
             human_judgment_penalty, matched_signals, hypothesis, offer_angle)
        VALUES
            (:job_id, :automation_score, :repetitive_signal_score,
             :structured_input_score, :measurable_output_score,
             :human_judgment_penalty, :matched_signals, :hypothesis, :offer_angle)
    """, score)
    conn.commit()
    conn.close()


def insert_review_queue(job_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO review_queue (job_id) VALUES (?)", (job_id,)
    )
    conn.commit()
    conn.close()


def update_review_status(job_id: str, status: str, notes: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE review_queue
        SET status = ?, reviewer_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE job_id = ?
    """, (status, notes, job_id))
    conn.commit()
    conn.close()


def get_leads(min_score: int = 60, departements: list = None,
              statuses: list = None, include_low_fit: bool = False) -> list:
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT
            j.id, j.title, j.company_name, j.company_sector,
            j.location_text, j.departement, j.contract_type,
            j.posted_at, j.source_url,
            ls.automation_score, ls.repetitive_signal_score,
            ls.structured_input_score, ls.measurable_output_score,
            ls.human_judgment_penalty, ls.matched_signals,
            ls.hypothesis, ls.offer_angle,
            COALESCE(rq.status, 'pending') AS status,
            rq.reviewer_notes
        FROM jobs j
        JOIN lead_scores ls ON ls.job_id = j.id
        LEFT JOIN review_queue rq ON rq.job_id = j.id
        WHERE 1=1
    """
    params = []

    if not include_low_fit:
        query += " AND ls.automation_score >= ?"
        params.append(min_score)

    if departements:
        placeholders = ",".join("?" * len(departements))
        query += f" AND j.departement IN ({placeholders})"
        params.extend(departements)

    if statuses:
        placeholders = ",".join("?" * len(statuses))
        query += f" AND COALESCE(rq.status, 'pending') IN ({placeholders})"
        params.extend(statuses)

    query += " ORDER BY ls.automation_score DESC"

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_job_description(job_id: str) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT description_raw FROM jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else ""


def get_stats() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE COALESCE(rq.status, 'pending') = 'pending') AS pending,
            COUNT(*) FILTER (WHERE rq.status = 'approved') AS approved,
            MAX(j.fetched_at) AS last_fetch
        FROM jobs j
        LEFT JOIN review_queue rq ON rq.job_id = j.id
    """)
    row = cur.fetchone()
    conn.close()
    return {"pending": row[0] or 0, "approved": row[1] or 0, "last_fetch": row[2]}


def get_approved_leads_for_export() -> list:
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT
            j.company_name, j.title, j.location_text, j.company_sector,
            j.source_url, j.posted_at, j.description_raw,
            ls.automation_score, ls.matched_signals, ls.hypothesis,
            ls.offer_angle,
            rq.reviewer_notes
        FROM jobs j
        JOIN lead_scores ls ON ls.job_id = j.id
        JOIN review_queue rq ON rq.job_id = j.id
        WHERE rq.status = 'approved'
        ORDER BY ls.automation_score DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
