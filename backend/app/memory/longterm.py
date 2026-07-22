from __future__ import annotations
import aiosqlite


DB_PATH_DEFAULT = "scrutin.db"
EDC_DELTA_THRESHOLD = 2.0   # Only commit if score changes by > 2 points


async def propose_reputation_update(
    domain: str,
    check_failed: bool,
    db_path: str = DB_PATH_DEFAULT,
) -> dict:
    """
    EDC Pipeline (Extract-Deduplicate-Commit):
    1. EXTRACT — Read existing profile
    2. DEDUPLICATE — Compute new score and delta
    3. COMMIT — Write only if delta > EDC_DELTA_THRESHOLD (avoids noise commits)

    Returns {'committed': bool, 'new_score': float, 'domain': str}
    Called by Credibility agent. Only committed by Orchestrator confirmation.
    """
    async with aiosqlite.connect(db_path, timeout=30.0, isolation_level=None) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("BEGIN IMMEDIATE")
        try:
            # 1. EXTRACT
            async with db.execute(
                "SELECT credibility_score, total_checks, failed_checks FROM source_reputation WHERE domain = ?",
                (domain,)
            ) as cursor:
                row = await cursor.fetchone()

            # 2. DEDUPLICATE
            if row:
                score, total, failed = row
                total += 1
                if check_failed:
                    failed += 1
                new_score = max(0.0, min(100.0, 100.0 * (1.0 - failed / total)))
                delta = abs(new_score - score)
            else:
                total, failed = 1, (1 if check_failed else 0)
                new_score = 0.0 if check_failed else 100.0
                delta = 100.0  # Always commit new domains

            # 3. COMMIT
            if delta >= EDC_DELTA_THRESHOLD:
                await db.execute(
                    """INSERT INTO source_reputation (domain, credibility_score, total_checks, failed_checks, last_updated)
                       VALUES (?, ?, ?, ?, datetime('now'))
                       ON CONFLICT(domain) DO UPDATE SET
                           credibility_score = excluded.credibility_score,
                           total_checks = excluded.total_checks,
                           failed_checks = excluded.failed_checks,
                           last_updated = excluded.last_updated""",
                    (domain, new_score, total, failed)
                )
                await db.execute("COMMIT")
                return {"committed": True, "new_score": new_score, "domain": domain}
            else:
                await db.execute("COMMIT")
                return {"committed": False, "new_score": new_score, "domain": domain}
        except Exception as e:
            try:
                await db.execute("ROLLBACK")
            except Exception:
                pass
            raise e


async def get_reputation(domain: str, db_path: str = DB_PATH_DEFAULT) -> dict | None:
    """Fast-path reputation lookup. Returns None if domain is unknown."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        async with db.execute(
            "SELECT credibility_score, total_checks, failed_checks, is_recent_domain, last_updated FROM source_reputation WHERE domain = ?",
            (domain,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "domain": domain,
                "credibility_score": row[0],
                "total_checks": row[1],
                "failed_checks": row[2],
                "is_recent_domain": bool(row[3]),
                "last_updated": row[4],
            }
