from __future__ import annotations
import asyncio
import sqlite3
import pytest
import pytest_asyncio
from app.memory import episodic, longterm
from app.memory.migrations import run_migrations


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_scrutin.db")
    run_migrations(path)
    return path


@pytest.mark.asyncio
async def test_record_and_recall_run(db_path):
    await episodic.record_run(
        run_id="ep-001",
        raw_input="The Eiffel Tower was built in 1887",
        input_type="text",
        overall_verdict="false",
        credibility_score=15.0,
        confidence=0.88,
        data_json="{}",
        iterations_used=4,
        budget_exhausted=False,
        processing_time_seconds=7.2,
        db_path=db_path,
    )
    results = await episodic.find_similar_run("Eiffel Tower built", db_path=db_path)
    assert len(results) >= 1
    assert results[0]["overall_verdict"] == "false"


@pytest.mark.asyncio
async def test_wal_mode_is_active(db_path):
    import aiosqlite
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        async with db.execute("PRAGMA journal_mode") as cursor:
            row = await cursor.fetchone()
    assert row[0].lower() == "wal"


@pytest.mark.asyncio
async def test_edc_commits_new_domain(db_path):
    result = await longterm.propose_reputation_update("bbc.co.uk", check_failed=False, db_path=db_path)
    assert result["committed"] is True
    assert result["new_score"] == 100.0


@pytest.mark.asyncio
async def test_edc_no_commit_on_small_delta(db_path):
    # First commit
    await longterm.propose_reputation_update("reuters.com", check_failed=False, db_path=db_path)
    # Second commit — same outcome, delta should be 0
    result = await longterm.propose_reputation_update("reuters.com", check_failed=False, db_path=db_path)
    assert result["committed"] is False   # delta < 2.0 threshold


@pytest.mark.asyncio
async def test_get_reputation_returns_none_for_unknown(db_path):
    result = await longterm.get_reputation("never-seen-domain.xyz", db_path=db_path)
    assert result is None
