"""
2026 Real-World Mixed (True & False) Verification Test Benchmark
================================================================
Evaluates Scrutin's state graph engine against a balanced test suite of
verified TRUE facts and debunked FALSE viral claims from 2025-2026.
"""

from __future__ import annotations
import pytest
from app.graph.state import ScrutinGraphState
from app.graph.engine import run_graph_engine
from app.protocols.blackboard import Blackboard
from app.agents.base import AgentDeps

REALWORLD_2026_BENCHMARK = [
    # 🟢 VERIFIED TRUE REAL-WORLD CLAIMS (2025-2026)
    {
        "id": "TRUE-01",
        "category": "Space Exploration Fact",
        "text": "ISRO successfully completed the SPADEX space docking experiment in January 2025, making India the fourth nation to demonstrate autonomous spacecraft docking in orbit.",
        "expected_verdict": ["true", "supports"],
    },
    {
        "id": "TRUE-02",
        "category": "Human Spaceflight Fact",
        "text": "Group Captain Shubhanshu Shukla became the first Indian astronaut to board the International Space Station on the Axiom-4 mission.",
        "expected_verdict": ["true", "supports"],
    },
    {
        "id": "TRUE-03",
        "category": "Satellite Technology Fact",
        "text": "The joint ISRO-NASA Earth observation satellite mission named NISAR utilizes dual-frequency synthetic aperture radar to monitor Earth surface changes.",
        "expected_verdict": ["true", "supports"],
    },

    # 🔴 DEBUNKED FALSE VIRAL CLAIMS (2025-2026)
    {
        "id": "FALSE-01",
        "category": "Fake Government Allowance",
        "text": "Union Budget 2026 announced that central government will transfer Rs 15,000 monthly cash allowance to every unemployed youth who registers on telegram channel.",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
    {
        "id": "FALSE-02",
        "category": "Health 5G Radiation Hoax",
        "text": "5G mobile tower signals in India are causing mass bird deaths and respiratory failure in domestic animals according to ICMR research.",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
    {
        "id": "FALSE-03",
        "category": "Viksit Bharat Card Phishing",
        "text": "Government of India launched Viksit Bharat Digital Card giving free unlimited train travel to all citizens who verify OTP at http://viksit-bharat-card.site",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize("item", REALWORLD_2026_BENCHMARK, ids=[i["id"] for i in REALWORLD_2026_BENCHMARK])
async def test_realworld_2026_query(item: dict):
    run_id = f"test_{item['id'].lower()}"
    raw_text = item["text"]

    bb = Blackboard(run_id=run_id, raw_input=raw_text)
    deps = AgentDeps(blackboard=bb, config={})
    state = ScrutinGraphState(run_id=run_id, raw_input=raw_text)

    events = []
    async def dummy_emit(event_type: str, data: dict):
        events.append((event_type, data))

    report = await run_graph_engine(state, deps, dummy_emit)
    assert report is not None
    assert report.run_id == run_id
    assert report.overall_verdict.lower() in [v.lower() for v in item["expected_verdict"]]
    
    # Specific assertions for True vs False separation
    if item["id"].startswith("TRUE"):
        assert report.overall_verdict.lower() in ("true", "supports")
    elif item["id"].startswith("FALSE"):
        assert report.overall_verdict.lower() in ("false", "misleading", "unverifiable")
        assert report.overall_verdict.lower() != "true"
