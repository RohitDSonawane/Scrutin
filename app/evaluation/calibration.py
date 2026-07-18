from __future__ import annotations
import sqlite3
import aiosqlite
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


async def log_calibration_entry(
    run_id: str,
    agent: str,
    stated_confidence: float,
    actual_outcome: str | None,
    db_path: str = "scrutin.db",
) -> None:
    """
    Record an agent's stated confidence vs. actual outcome.
    actual_outcome: "correct" | "incorrect" | None (unknown, for live runs)
    Called by the Orchestrator after ground-truth test runs.
    """
    async with aiosqlite.connect(db_path, timeout=30.0, isolation_level=None) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("BEGIN IMMEDIATE")
        try:
            await db.execute(
                """INSERT INTO calibration_log (run_id, agent, stated_confidence, actual_outcome, created_at)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (run_id, agent, stated_confidence, actual_outcome)
            )
            await db.execute("COMMIT")
        except Exception as e:
            try:
                await db.execute("ROLLBACK")
            except Exception:
                pass
            raise e


def compute_ece(db_path: str = "scrutin.db") -> float:
    """
    Expected Calibration Error (ECE).
    A well-calibrated system: ECE < 0.05 (right ~80% of time when it says 80%).
    Returns 0.0 if no calibration data exists yet.
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    # Check if table exists first before querying to avoid operational errors
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='calibration_log'"
    ).fetchone()
    if not table_exists:
        conn.close()
        return 0.0

    rows = conn.execute(
        "SELECT stated_confidence, actual_outcome FROM calibration_log WHERE actual_outcome IS NOT NULL"
    ).fetchall()
    conn.close()

    if not rows:
        return 0.0

    buckets: dict[int, list[int]] = {i: [] for i in range(10)}
    for confidence, outcome in rows:
        bucket_idx = min(int(float(confidence) * 10), 9)
        buckets[bucket_idx].append(1 if outcome == "correct" else 0)

    ece = 0.0
    n_total = len(rows)
    for i, outcomes in buckets.items():
        if not outcomes:
            continue
        bucket_confidence = (i + 0.5) / 10
        bucket_accuracy = sum(outcomes) / len(outcomes)
        ece += (len(outcomes) / n_total) * abs(bucket_accuracy - bucket_confidence)

    return round(ece, 4)


def print_calibration_report(db_path: str = "scrutin.db") -> None:
    ece = compute_ece(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0)
    # Check if table exists first
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='calibration_log'"
    ).fetchone()
    if not table_exists:
        conn.close()
        total = 0
        correct = 0
    else:
        total = conn.execute("SELECT COUNT(*) FROM calibration_log").fetchone()[0]
        correct = conn.execute(
            "SELECT COUNT(*) FROM calibration_log WHERE actual_outcome='correct'"
        ).fetchone()[0]
        conn.close()

    table = Table(title="Calibration Report", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Total calibration entries", str(total))
    if total > 0:
        table.add_row("Correct verdicts", f"{correct} ({100*correct//total}%)")
    ece_color = "green" if ece < 0.05 else "yellow" if ece < 0.15 else "red"
    table.add_row("Expected Calibration Error (ECE)", f"[{ece_color}]{ece}[/]")
    table.add_row("ECE target", "< 0.05 (production) | < 0.15 (hackathon)")
    console.print(table)
