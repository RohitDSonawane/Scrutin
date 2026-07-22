# app/memory/migrations.py
from __future__ import annotations
import sqlite3

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS episodic_runs (
    run_id              TEXT PRIMARY KEY,
    raw_input           TEXT NOT NULL,
    input_type          TEXT NOT NULL DEFAULT 'text',
    overall_verdict     TEXT,
    credibility_score   REAL,
    confidence          REAL,
    data_json           TEXT NOT NULL,
    iterations_used     INTEGER NOT NULL DEFAULT 0,
    budget_exhausted    INTEGER NOT NULL DEFAULT 0,
    processing_time_seconds REAL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_episodic_verdict ON episodic_runs(overall_verdict);
CREATE INDEX IF NOT EXISTS idx_episodic_created ON episodic_runs(created_at);

CREATE TABLE IF NOT EXISTS source_reputation (
    domain              TEXT PRIMARY KEY,
    credibility_score   REAL NOT NULL DEFAULT 50.0,
    total_checks        INTEGER NOT NULL DEFAULT 0,
    failed_checks       INTEGER NOT NULL DEFAULT 0,
    registrar           TEXT,
    registered_date     TEXT,
    is_recent_domain    INTEGER NOT NULL DEFAULT 0,
    last_updated        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS calibration_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT NOT NULL REFERENCES episodic_runs(run_id),
    agent               TEXT NOT NULL,
    stated_confidence   REAL NOT NULL,
    actual_outcome      TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS claim_similarity_cache (
    claim_id            TEXT PRIMARY KEY,
    claim_text          TEXT NOT NULL,
    pinecone_vector_id  TEXT NOT NULL,
    run_id              TEXT NOT NULL REFERENCES episodic_runs(run_id),
    verdict             TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

def run_migrations(db_path: str = "scrutin.db") -> None:
    """Run once on startup. Idempotent — safe to call every time."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.close()
    print(f"[DB] Migrations applied to {db_path}")

if __name__ == "__main__":
    run_migrations()
