# tests/test_memory_integration.py
from __future__ import annotations
import asyncio
import pytest


@pytest.mark.asyncio
async def test_second_run_hits_episodic(tmp_path):
    """
    Run the same claim twice. The second run should find the first in episodic memory
    (SQLite text search, since Pinecone may not be configured in tests).
    """
    from app.memory.episodic import record_run, find_similar_run

    db_path = str(tmp_path / "test.db")
    from app.memory.migrations import run_migrations
    run_migrations(db_path)

    # First run — record it
    await record_run(
        run_id="run-001",
        raw_input="The COVID vaccine causes autism",
        input_type="text",
        overall_verdict="false",
        credibility_score=8.0,
        confidence=0.91,
        data_json="{}",
        iterations_used=5,
        budget_exhausted=False,
        processing_time_seconds=9.1,
        db_path=db_path,
    )

    # Second run — should find it
    similar = await find_similar_run("vaccine causes autism", db_path=db_path)
    assert len(similar) >= 1
    assert similar[0]["overall_verdict"] == "false"


@pytest.mark.asyncio
async def test_reputation_committed_for_new_domain(tmp_path):
    from app.memory.longterm import propose_reputation_update, get_reputation
    db_path = str(tmp_path / "test.db")
    from app.memory.migrations import run_migrations
    run_migrations(db_path)

    result = await propose_reputation_update("snopes.com", check_failed=False, db_path=db_path)
    assert result["committed"] is True

    rep = await get_reputation("snopes.com", db_path=db_path)
    assert rep is not None
    assert rep["credibility_score"] == 100.0
