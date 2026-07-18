from __future__ import annotations
import sqlite3
import pytest
from app.protocols.messages import (
    EvidenceItem, AgentRequest, Task, Plan, Finding,
    EvidenceEvaluation, compute_stopping_score, VerificationReport,
)
from app.protocols.blackboard import Blackboard


# ── Schema validation tests ───────────────────────────────────────────────────

def test_finding_stance_is_literal():
    with pytest.raises(Exception):
        Finding(agent="test", claim_id="C1", stance="maybe", confidence=0.5, rationale="x")

def test_finding_confidence_bounds():
    with pytest.raises(Exception):
        Finding(agent="test", claim_id="C1", stance="supports", confidence=1.5, rationale="x")

def test_plan_next_task_skips_completed():
    plan = Plan(tasks=[
        Task(task_id="T1", agent="decomposition", claim_id="C1", completed=True),
        Task(task_id="T2", agent="evidence", claim_id="C1", completed=False),
    ])
    assert plan.next_task().task_id == "T2"

def test_plan_requeue():
    plan = Plan(tasks=[Task(task_id="T1", agent="evidence", claim_id="C1", completed=True)])
    plan.requeue("T1", reason="only wire sources found")
    t = plan.tasks[0]
    assert t.completed is False
    assert t.retry_count == 1
    assert t.retry_reason == "only wire sources found"


# ── Deterministic-picker tests ────────────────────────────────────────────────

def test_all_booleans_true_gives_full_score():
    ev = EvidenceEvaluation(
        sources_are_independent=True,
        adversarial_critique_addressed=True,
        confidence_matches_evidence=True,
        claim_fully_decomposed=True,
        quality_note="strong",
    )
    assert compute_stopping_score(ev) == 1.0

def test_no_booleans_gives_zero():
    ev = EvidenceEvaluation(
        sources_are_independent=False,
        adversarial_critique_addressed=False,
        confidence_matches_evidence=False,
        claim_fully_decomposed=False,
        quality_note="weak",
    )
    assert compute_stopping_score(ev) == 0.0

def test_stopping_threshold():
    """Score >= 0.85 is the stopping criterion (architecture §6)."""
    ev = EvidenceEvaluation(
        sources_are_independent=True,
        adversarial_critique_addressed=True,
        confidence_matches_evidence=True,
        claim_fully_decomposed=False,
        quality_note="partial",
    )
    score = compute_stopping_score(ev)
    assert score == 0.85


# ── Blackboard tests ──────────────────────────────────────────────────────────

def test_store_evidence_auto_id():
    bb = Blackboard(run_id="test-001", raw_input="test claim")
    id1 = bb.store_evidence("WB", {"url": "https://a.com", "snippet": "text"})
    id2 = bb.store_evidence("WB", {"url": "https://b.com", "snippet": "text"})
    id3 = bb.store_evidence("FC", {"url": "https://c.com", "snippet": "text"})
    assert id1 == "WB1"
    assert id2 == "WB2"
    assert id3 == "FC1"

def test_append_finding_is_append_only():
    bb = Blackboard(run_id="test-002", raw_input="test claim")
    f1 = Finding(agent="evidence", claim_id="C1", stance="supports", confidence=0.8, rationale="r1")
    f2 = Finding(agent="adversarial", claim_id="C1", stance="contradicts", confidence=0.7, rationale="r2")
    bb.append_finding(f1)
    bb.append_finding(f2)
    assert len(bb.findings) == 2
    assert bb.findings[0]["agent"] == "evidence"
    assert bb.findings[1]["agent"] == "adversarial"

def test_flush_to_sqlite_roundtrip(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE episodic_runs (
        run_id TEXT PRIMARY KEY,
        raw_input TEXT NOT NULL,
        input_type TEXT NOT NULL DEFAULT 'text',
        data_json TEXT NOT NULL,
        iterations_used INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.commit()

    bb = Blackboard(run_id="flush-test", raw_input="A test claim", iterations=3)
    bb.flush_to_sqlite(conn)
    conn.commit()

    row = conn.execute("SELECT run_id, iterations_used FROM episodic_runs WHERE run_id='flush-test'").fetchone()
    assert row[0] == "flush-test"
    assert row[1] == 3
    conn.close()

def test_get_findings_for_claim():
    bb = Blackboard(run_id="test-003", raw_input="test claim")
    bb.append_finding(Finding(agent="evidence", claim_id="C1", stance="supports", confidence=0.8, rationale="r"))
    bb.append_finding(Finding(agent="evidence", claim_id="C2", stance="contradicts", confidence=0.7, rationale="r"))
    assert len(bb.get_findings_for_claim("C1")) == 1
    assert len(bb.get_findings_for_claim("C2")) == 1
    assert len(bb.get_findings_for_claim("C3")) == 0
