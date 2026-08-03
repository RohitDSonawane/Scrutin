from __future__ import annotations
import pytest
from app.graph.state import ScrutinGraphState
from app.protocols.blackboard import Blackboard
from app.agents.base import AgentDeps

@pytest.mark.asyncio
async def test_graph_state_initialization():
    state = ScrutinGraphState(run_id="test_123", raw_input="The Eiffel Tower is in Paris.")
    assert state.run_id == "test_123"
    assert state.raw_input == "The Eiffel Tower is in Paris."
    assert state.iterations == 0
    assert state.is_complete is False

@pytest.mark.asyncio
async def test_graph_engine_run():
    from app.graph.engine import run_graph_engine

    bb = Blackboard(run_id="test_run", raw_input="Vaccines cause autism.")
    deps = AgentDeps(blackboard=bb, config={})
    state = ScrutinGraphState(run_id="test_run", raw_input="Vaccines cause autism.")

    events = []
    async def dummy_emit(event_type: str, data: dict):
        events.append((event_type, data))

    try:
        report = await run_graph_engine(state, deps, dummy_emit)
        assert report is not None
        assert report.run_id == "test_run"
        assert len(events) > 0
    except Exception as e:
        # Ignore external Groq 429 rate limit errors during unit test execution
        if "429" in str(e) or "rate_limit" in str(e).lower():
            pytest.skip("Skipping test due to external Groq API rate limit (429)")
        else:
            raise e

