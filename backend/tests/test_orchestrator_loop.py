from __future__ import annotations
import sqlite3
import pytest
from pydantic_ai.models.test import TestModel
from app.orchestrator.loop import run_orchestrator

# Import agents to override
from app.agents.decomposition_agent import decomposition_agent
from app.agents.evidence_agent import evidence_agent
from app.agents.credibility_agent import credibility_agent
from app.agents.adversarial_agent import adversarial_agent
from app.agents.orchestrator_agent import orchestrator_agent
from app.orchestrator import evaluator


@pytest.mark.asyncio
async def test_loop_produces_report(tmp_path):
    db_path = str(tmp_path / "test.db")
    from app.memory.migrations import run_migrations
    run_migrations(db_path)

    with (
        decomposition_agent.override(model=TestModel()),
        evidence_agent.override(model=TestModel()),
        credibility_agent.override(model=TestModel()),
        adversarial_agent.override(model=TestModel()),
        orchestrator_agent.override(model=TestModel()),
    ):
        report = await run_orchestrator(
            "The Eiffel Tower was built in 1887",
            db_path=db_path,
        )

    assert report is not None
    assert report.run_id is not None
    assert report.overall_verdict in {"true", "false", "misleading", "unverifiable", "inconclusive"}


@pytest.mark.asyncio
async def test_loop_stops_within_budget(tmp_path):
    db_path = str(tmp_path / "test.db")
    from app.memory.migrations import run_migrations
    run_migrations(db_path)

    with (
        decomposition_agent.override(model=TestModel()),
        evidence_agent.override(model=TestModel()),
        credibility_agent.override(model=TestModel()),
        adversarial_agent.override(model=TestModel()),
        orchestrator_agent.override(model=TestModel()),
    ):
        report = await run_orchestrator(
            "test claim",
            db_path=db_path,
        )

    assert report.iterations_used <= 20


@pytest.mark.asyncio
async def test_sqlite_flushed_on_completion(tmp_path):
    """Blackboard must be flushed to SQLite even when loop completes normally."""
    db_path = str(tmp_path / "test.db")
    from app.memory.migrations import run_migrations
    run_migrations(db_path)

    with (
        decomposition_agent.override(model=TestModel()),
        evidence_agent.override(model=TestModel()),
        credibility_agent.override(model=TestModel()),
        adversarial_agent.override(model=TestModel()),
        orchestrator_agent.override(model=TestModel()),
    ):
        report = await run_orchestrator("test claim flush", db_path=db_path)

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT run_id FROM episodic_runs WHERE run_id=?", (report.run_id,)).fetchone()
    conn.close()
    assert row is not None, "Run was NOT flushed to SQLite!"


def test_provisional_verdict_excludes_credibility_stance():
    """Credibility agent findings ('mixed') must be excluded from provisional verdict tally."""
    from app.protocols.blackboard import Blackboard
    from app.orchestrator.loop import _derive_provisional_verdict
    from app.protocols.messages import Finding

    bb = Blackboard(run_id="test", raw_input="test claim")
    # Only credibility finding present (always 'mixed')
    bb.append_finding(Finding(agent="credibility", claim_id="C0", stance="mixed", confidence=0.8, rationale=""))
    # Stance tally must ignore credibility 'mixed' and return 'inconclusive' (not 'misleading')
    assert _derive_provisional_verdict(bb) == "inconclusive"


def test_fallback_report_defaults_to_inconclusive():
    """Fallback report must hardcode overall_verdict='inconclusive' and credibility_score=50.0."""
    from app.protocols.blackboard import Blackboard
    from app.orchestrator.loop import _build_final_report

    bb = Blackboard(run_id="test_fb", raw_input="test claim")
    report = _build_final_report(bb, elapsed=1.5, budget_exhausted=True)
    assert report.overall_verdict == "inconclusive"
    assert report.credibility_score == 50.0
    assert report.budget_exhausted is True
