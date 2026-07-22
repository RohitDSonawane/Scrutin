from __future__ import annotations
import json
import aiosqlite
from typing import Optional


DB_PATH_DEFAULT = "scrutin.db"


async def record_run(
    run_id: str,
    raw_input: str,
    input_type: str,
    overall_verdict: Optional[str],
    credibility_score: Optional[float],
    confidence: Optional[float],
    data_json: str,
    iterations_used: int,
    budget_exhausted: bool,
    processing_time_seconds: Optional[float],
    db_path: str = DB_PATH_DEFAULT,
) -> None:
    """
    Write a completed run to episodic memory.
    Called by the Orchestrator at run completion — even on crash (use try/finally).
    """
    async with aiosqlite.connect(db_path, timeout=30.0, isolation_level=None) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("BEGIN IMMEDIATE")
        try:
            await db.execute(
                """INSERT OR REPLACE INTO episodic_runs
                   (run_id, raw_input, input_type, overall_verdict, credibility_score,
                    confidence, data_json, iterations_used, budget_exhausted,
                    processing_time_seconds, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (run_id, raw_input, input_type, overall_verdict, credibility_score,
                 confidence, data_json, iterations_used, int(budget_exhausted),
                 processing_time_seconds)
            )
            await db.execute("COMMIT")
        except Exception as e:
            try:
                await db.execute("ROLLBACK")
            except Exception:
                pass
            raise e


async def find_similar_run(
    claim_text: str,
    db_path: str = DB_PATH_DEFAULT,
    limit: int = 3,
) -> list[dict]:
    """
    Simple full-text search in episodic memory for similar past claims.
    This is a fallback when Pinecone is unavailable — use semantic search in Phase 8 for quality.
    Returns list of {run_id, raw_input, overall_verdict, credibility_score, created_at}.
    """
    keywords = [w.strip() for w in claim_text.lower().split() if len(w) > 4]
    if not keywords:
        return []

    # Use first 3 keywords for a simple LIKE search
    search_terms = keywords[:3]
    where_clauses = " AND ".join([f"raw_input LIKE ?" for _ in search_terms])
    params = [f"%{term}%" for term in search_terms]

    async with aiosqlite.connect(db_path, timeout=30.0) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""SELECT run_id, raw_input, overall_verdict, credibility_score, created_at
                FROM episodic_runs
                WHERE {where_clauses} AND overall_verdict IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?""",
            params + [limit]
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_run_stats(db_path: str = DB_PATH_DEFAULT) -> dict:
    """Stats for the `python -m app.cli stats` command."""
    async with aiosqlite.connect(db_path, timeout=30.0) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        total = (await (await db.execute("SELECT COUNT(*) FROM episodic_runs")).fetchone())[0]
        verdicts = {}
        async with db.execute(
            "SELECT overall_verdict, COUNT(*) FROM episodic_runs GROUP BY overall_verdict"
        ) as cursor:
            async for row in cursor:
                verdicts[row[0] or "null"] = row[1]
        return {"total_runs": total, "verdicts": verdicts}
