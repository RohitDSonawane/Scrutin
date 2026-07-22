# Database Schema — Scrutin Platform (SQLite + Pinecone)

All persistence definitions for the demo/MVP build. WAL mode is mandatory on all SQLite connections.

---

## 1. SQLite Database: `scrutin.db`

One file. Two logical sections: episodic memory (past runs) and long-term reputation (source credibility).

### Connection Setup (apply to EVERY connection)

```python
# app/memory/_db.py
from __future__ import annotations
import aiosqlite

DB_PATH = "scrutin.db"

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")   # MANDATORY — prevents "database is locked" in async
    await db.execute("PRAGMA foreign_keys=ON")
    return db
```

---

### Table 1: `episodic_runs` — Past Verification Runs

```sql
CREATE TABLE IF NOT EXISTS episodic_runs (
    run_id          TEXT PRIMARY KEY,
    raw_input       TEXT NOT NULL,
    input_type      TEXT NOT NULL DEFAULT 'text',   -- 'text' | 'url' | 'image' | 'video'
    overall_verdict TEXT,                            -- 'true' | 'false' | 'misleading' | 'inconclusive'
    credibility_score REAL,                          -- 0.0 – 100.0
    confidence      REAL,                            -- 0.0 – 1.0
    data_json       TEXT NOT NULL,                   -- Full Blackboard serialized as JSON
    iterations_used INTEGER NOT NULL DEFAULT 0,
    budget_exhausted INTEGER NOT NULL DEFAULT 0,     -- SQLite bool: 0 or 1
    processing_time_seconds REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Fast recall: "have we seen a similar claim before?"
CREATE INDEX IF NOT EXISTS idx_episodic_verdict ON episodic_runs(overall_verdict);
CREATE INDEX IF NOT EXISTS idx_episodic_created ON episodic_runs(created_at);
```

---

### Table 2: `source_reputation` — Long-Term Source Credibility

```sql
CREATE TABLE IF NOT EXISTS source_reputation (
    domain              TEXT PRIMARY KEY,
    credibility_score   REAL NOT NULL DEFAULT 50.0,  -- 0.0 (worst) to 100.0 (best)
    total_checks        INTEGER NOT NULL DEFAULT 0,
    failed_checks       INTEGER NOT NULL DEFAULT 0,   -- claims from this domain marked false/misleading
    registrar           TEXT,                          -- WHOIS registrar name
    registered_date     TEXT,                          -- WHOIS creation date YYYY-MM-DD
    is_recent_domain    INTEGER NOT NULL DEFAULT 0,    -- 1 if registered < 180 days ago
    last_updated        TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### Table 3: `calibration_log` — Agent Confidence vs. Outcome Tracking

```sql
CREATE TABLE IF NOT EXISTS calibration_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES episodic_runs(run_id),
    agent           TEXT NOT NULL,                     -- which agent's confidence is being tracked
    stated_confidence REAL NOT NULL,                   -- the confidence float the agent reported
    actual_outcome  TEXT,                              -- 'correct' | 'incorrect' | 'unknown'
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### Table 4: `claim_similarity_cache` — Fast Duplicate Claim Lookup

```sql
-- Lightweight lookup table. Pinecone handles vector search;
-- this table is the metadata store for matched claim IDs.
CREATE TABLE IF NOT EXISTS claim_similarity_cache (
    claim_id        TEXT PRIMARY KEY,
    claim_text      TEXT NOT NULL,
    pinecone_vector_id TEXT NOT NULL,
    run_id          TEXT NOT NULL REFERENCES episodic_runs(run_id),
    verdict         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### Full Migration Script

```python
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
```

---

## 2. Pinecone Index: `scrutin-claims`

One index (free tier limit). Two namespaces to separate claim similarity from media hashing.

### Index Configuration

```python
# app/memory/semantic.py
from __future__ import annotations
from pinecone import Pinecone, ServerlessSpec

INDEX_NAME = "scrutin-claims"
DIMENSION = 768        # gemini-embedding-001 output dimension
METRIC = "cosine"

NAMESPACES = {
    "claims": "claims",      # Claim text embeddings (gemini-embedding-001)
    "media":  "media",       # Perceptual hash vectors (imagehash → fixed-dim float vector)
}

def init_pinecone(api_key: str) -> Pinecone:
    pc = Pinecone(api_key=api_key)
    if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric=METRIC,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"[Pinecone] Created index '{INDEX_NAME}'")
    return pc
```

### Embedding Model

```python
# Use gemini-embedding-001 for claim text similarity
# Do NOT use text-embedding-3-small — that is an OpenAI model name, not a Gemini one.

import google.generativeai as genai

def embed_claim(text: str, api_key: str) -> list[float]:
    genai.configure(api_key=api_key)
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]
```

### Media Perceptual Hash (Forensics fast-path)

```python
# Use imagehash for image deduplication — NOT semantic embeddings.
# pHash catches the SAME image re-uploaded with different filenames.
# Semantic embeddings would catch "similar" images — wrong tool for this job.

import imagehash
from PIL import Image

def compute_media_hash(image_path: str) -> str:
    img = Image.open(image_path)
    return str(imagehash.phash(img))   # Returns hex string like "d4f8c9a2..."

def hash_to_vector(hex_hash: str) -> list[float]:
    """Convert 64-bit pHash to a float vector for Pinecone storage."""
    bits = bin(int(hex_hash, 16))[2:].zfill(64)
    return [float(b) for b in bits]   # 64-dim binary vector — matches DIMENSION=64 for media namespace
```

> [!IMPORTANT]
> For the media namespace, create the Pinecone index with `dimension=64` and `metric="hamming"`.
> Since Pinecone free tier allows only ONE index, use the `claims` namespace with `dimension=768`
> and store media hashes in a separate SQLite table with raw hex for now. Promote to Pinecone later.
