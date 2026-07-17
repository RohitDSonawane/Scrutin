# tests/test_concurrent.py
from __future__ import annotations
import asyncio
import pytest
from app.orchestrator.loop import run_orchestrator
from app.memory.migrations import run_migrations

# Import agents to override
from app.agents.decomposition_agent import decomposition_agent
from app.agents.evidence_agent import evidence_agent
from app.agents.credibility_agent import credibility_agent
from app.agents.adversarial_agent import adversarial_agent
from app.agents.orchestrator_agent import orchestrator_agent
from app.orchestrator import evaluator


@pytest.mark.asyncio
async def test_concurrent_runs_no_database_locked(tmp_path):
    """
    5 simultaneous runs must complete without 'database is locked' errors.
    This validates WAL mode is working correctly for concurrent async access.
    """
    db_path = str(tmp_path / "concurrent_test.db")
    run_migrations(db_path)

    from pydantic_ai.models.test import TestModel
    claims = [
        "Claim A about vaccines",
        "Claim B about climate",
        "Claim C about economics",
        "Claim D about history",
        "Claim E about technology",
    ]

    async def run_one(claim):
        with (
            decomposition_agent.override(model=TestModel()),
            evidence_agent.override(model=TestModel()),
            credibility_agent.override(model=TestModel()),
            adversarial_agent.override(model=TestModel()),
            orchestrator_agent.override(model=TestModel()),
            evaluator._evaluator_agent.override(model=TestModel()),
            evaluator._reflection_agent.override(model=TestModel()),
        ):
            return await run_orchestrator(claim, db_path=db_path)

    # Run all 5 concurrently
    results = await asyncio.gather(*[run_one(c) for c in claims])

    assert len(results) == 5
    # All should complete without exception
    for r in results:
        assert r.run_id is not None

    # All 5 should be in the DB
    import sqlite3
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM episodic_runs").fetchone()[0]
    conn.close()
    assert count == 5
