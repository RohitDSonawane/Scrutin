"""
Indian Misinformation WhatsApp Test Benchmark Suite
===================================================
Executes all 6 real-world Indian WhatsApp misinformation test queries
through Scrutin's state graph verification engine.
"""

from __future__ import annotations
import pytest
from app.graph.state import ScrutinGraphState
from app.graph.engine import run_graph_engine
from app.protocols.blackboard import Blackboard
from app.agents.base import AgentDeps

BENCHMARK_QUERIES = [
    {
        "id": "WA-01",
        "category": "Welfare Scheme Phishing",
        "text": "Government of India giving free Rs. 5000 recharge under PM Free Recharge Scheme at http://pm-free-yojana-2026.online",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
    {
        "id": "WA-02",
        "category": "Medical Cure Hoax",
        "text": "Boiled guava leaves and lemon juice cure Dengue in 24 hours according to WHO and AIIMS doctors.",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
    {
        "id": "WA-03",
        "category": "Digital Arrest Panic",
        "text": "RBI blocking all bank accounts by midnight unless PAN is linked at http://sbi-aadhaar-update.site due to CBI digital arrest alert.",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
    {
        "id": "WA-04",
        "category": "Currency Nano-Chip Hoax",
        "text": "New Rs 2000 currency note contains an embedded Nano GPS Chip that tracks cash hidden 120 meters underground.",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
    {
        "id": "WA-05",
        "category": "Child Lifter Mob Panic",
        "text": "Gang of 50 child lifters disguised as beggars kidnapped 4 children from school yesterday.",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
    {
        "id": "WA-06",
        "category": "UNESCO Award Myth",
        "text": "UNESCO officially declared Narendra Modi as the Best Prime Minister in the World and Jana Gana Mana as Best National Anthem.",
        "expected_verdict": ["false", "misleading", "unverifiable"],
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize("query_item", BENCHMARK_QUERIES, ids=[q["id"] for q in BENCHMARK_QUERIES])
async def test_indian_misinformation_query(query_item: dict):
    run_id = f"test_{query_item['id'].lower()}"
    raw_text = query_item["text"]

    bb = Blackboard(run_id=run_id, raw_input=raw_text)
    deps = AgentDeps(blackboard=bb, config={})
    state = ScrutinGraphState(run_id=run_id, raw_input=raw_text)

    events = []
    async def dummy_emit(event_type: str, data: dict):
        events.append((event_type, data))

    report = await run_graph_engine(state, deps, dummy_emit)
    assert report is not None
    assert report.run_id == run_id
    assert report.overall_verdict.lower() in [v.lower() for v in query_item["expected_verdict"]]
    # Ensure system never returns false "true" verdict on unverified or failed claims
    assert report.overall_verdict.lower() != "true"
