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
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='calibration_log'"
        ).fetchone()
        if not table_exists:
            return 0.0

        rows = conn.execute(
            "SELECT stated_confidence, actual_outcome FROM calibration_log WHERE actual_outcome IS NOT NULL"
        ).fetchall()

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

    with sqlite3.connect(db_path, timeout=30.0) as conn:
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='calibration_log'"
        ).fetchone()
        if not table_exists:
            total = 0
            correct = 0
        else:
            total = conn.execute("SELECT COUNT(*) FROM calibration_log").fetchone()[0]
            correct = conn.execute(
                "SELECT COUNT(*) FROM calibration_log WHERE actual_outcome='correct'"
            ).fetchone()[0]

    table = Table(title="Calibration Report", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Total Evaluated Runs", str(total))
    table.add_row("Correct Verdicts", str(correct))
    accuracy = (correct / total * 100) if total > 0 else 0.0
    table.add_row("Raw Accuracy", f"{accuracy:.1f}%")
    table.add_row("Expected Calibration Error (ECE)", f"{ece:.4f}")

    console.print(table)


# ── Quantitative Evaluation Metrics Harness ───────────────────────────────────

def evaluate_verdict_precision_recall(predictions: list[tuple[str, str]]) -> dict[str, float]:
    """
    Calculate Verdict Accuracy, Precision, Recall, and F1 score against ground truth.
    predictions: list of (predicted_verdict, ground_truth_verdict) tuples.
    Returns dict with 'accuracy', 'precision', 'recall', 'f1_score'.
    """
    if not predictions:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0}

    correct_count = sum(1 for pred, truth in predictions if pred.lower().strip() == truth.lower().strip())
    total_count = len(predictions)
    accuracy = correct_count / total_count

    # Binary precision/recall metric for true/false claims
    tp = sum(1 for p, t in predictions if p.lower() in ("true", "supports") and t.lower() in ("true", "supports"))
    fp = sum(1 for p, t in predictions if p.lower() in ("true", "supports") and t.lower() not in ("true", "supports"))
    fn = sum(1 for p, t in predictions if p.lower() not in ("true", "supports") and t.lower() in ("true", "supports"))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0 if total_count > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0 if total_count > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
    }


def evaluate_evidence_relevance(claim_text: str, evidence_snippets: list[str]) -> float:
    """
    Calculate semantic relevance score between claim and evidence snippets.
    Returns average score (0.0 to 1.0).
    """
    if not claim_text or not evidence_snippets:
        return 0.0

    keywords = set(w.lower() for w in claim_text.split() if len(w) > 3)
    if not keywords:
        return 0.5

    scores = []
    for snippet in evidence_snippets:
        s_words = set(w.lower() for w in snippet.split() if len(w) > 3)
        overlap = len(keywords.intersection(s_words))
        scores.append(min(1.0, overlap / len(keywords)))

    return round(sum(scores) / len(scores), 4) if scores else 0.0
