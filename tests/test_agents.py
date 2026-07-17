from __future__ import annotations
import pytest
from pydantic_ai.models.test import TestModel
from app.protocols.blackboard import Blackboard
from app.protocols.messages import Finding, AdversarialCritique
from app.agents.base import AgentDeps
from app.agents.decomposition_agent import decomposition_agent, DecompositionOutput
from app.agents.adversarial_agent import adversarial_agent


@pytest.fixture
def deps():
    bb = Blackboard(run_id="test-agent-run", raw_input="test claim")
    return AgentDeps(blackboard=bb, config={"SERPER_API_KEY": "fake"})


def test_decomposition_agent_returns_correct_type(deps):
    with decomposition_agent.override(model=TestModel()):
        result = decomposition_agent.run_sync("Vaccines caused 50,000 deaths", deps=deps)
    # TestModel returns a valid DecompositionOutput shape
    assert isinstance(result.output, DecompositionOutput)


def test_adversarial_agent_returns_correct_type(deps):
    with adversarial_agent.override(model=TestModel()):
        result = adversarial_agent.run_sync(
            "Evidence: [WB1: CDC data]. Provisional verdict: FALSE",
            deps=deps
        )
    assert isinstance(result.output, AdversarialCritique)
    assert isinstance(result.output.verdict_stands, bool)


def test_agents_do_not_import_each_other():
    """No agent module may import another agent module."""
    import importlib
    agent_modules = [
        "app.agents.decomposition_agent",
        "app.agents.evidence_agent",
        "app.agents.credibility_agent",
        "app.agents.forensics_agent",
        "app.agents.adversarial_agent",
    ]
    for mod_name in agent_modules:
        mod = importlib.import_module(mod_name)
        source = open(mod.__file__).read()
        for other_mod in agent_modules:
            if other_mod == mod_name:
                continue
            short_name = other_mod.split(".")[-1]  # e.g. "evidence_agent"
            assert short_name not in source or f"from app.agents.{short_name}" not in source, \
                f"{mod_name} imports {other_mod} — agents must never import each other"


def test_no_agent_uses_groq_and_gemini_simultaneously():
    """Adversarial agent must be on Groq; Evidence and Orchestrator on Gemini."""
    from app.agents.adversarial_agent import adversarial_agent as adv
    from app.agents.evidence_agent import evidence_agent as ev
    assert "groq" in str(adv.model).lower() or "llama" in str(adv.model).lower()
    assert "gemini" in str(ev.model).lower() or "google" in str(ev.model).lower()
