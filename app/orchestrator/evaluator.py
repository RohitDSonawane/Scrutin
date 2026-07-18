from __future__ import annotations
import os
from pydantic_ai import Agent
from app.protocols.messages import EvidenceEvaluation, AgentReflection, compute_stopping_score
from app.agents.prompts import get_prompt

STOPPING_THRESHOLD = 0.85   # Minimum score to stop the loop (architecture §6)


# Evaluator agent — uses Gemini Flash for deterministic-picker judgment
_evaluator_agent = Agent(
    os.getenv("ORCHESTRATOR_MODEL", "google:gemini-2.5-flash"),
    output_type=EvidenceEvaluation,
    system_prompt="""
You are the self-critique evaluator for the Scrutin fact-checking orchestrator.
Given the current Blackboard state (findings, evidence, provisional verdict), 
commit to these boolean judgments:
- sources_are_independent: True iff supporting sources don't all trace to one wire story/press release
- adversarial_critique_addressed: True iff provisional verdict addresses adversarial's strongest counter
- confidence_matches_evidence: True iff stated confidence is consistent with source quality and count
- claim_fully_decomposed: True iff all load-bearing sub-claims have a Finding on the Blackboard
Also provide a quality_note: ONE specific observation about the weakest remaining gap.
""".strip()
)

_reflection_agent = Agent(
    os.getenv("ORCHESTRATOR_MODEL", "google:gemini-2.5-flash"),
    output_type=AgentReflection,
    system_prompt="""
You are the reflection agent. Given why a fact-checking run is insufficient,
produce a structured lesson with: root_cause (1 sentence), correction (1 imperative sentence),
lesson (2-4 sentences in second person, stored in episodic memory for future similar claims).
""".strip()
)


async def evaluate(blackboard_summary: str) -> tuple[EvidenceEvaluation, float]:
    """
    Run the deterministic-picker evaluator against the current Blackboard state.
    Returns (evaluation, stopping_score).
    stopping_score >= STOPPING_THRESHOLD → stop the loop.
    """
    from app.utils.rate_limiter import gemini_acquire
    await gemini_acquire()
    result = await _evaluator_agent.run(blackboard_summary)
    ev = result.output
    score = compute_stopping_score(ev)
    return ev, score


async def reflect(blackboard_summary: str, evaluation: EvidenceEvaluation) -> AgentReflection:
    """
    Run the verbal reflection step when evaluation score is below threshold.
    Stored in episodic memory so future similar claims benefit from this lesson.
    """
    prompt = (
        f"Root cause of insufficient evidence:\n{evaluation.quality_note}\n\n"
        f"Evaluation flags:\n"
        f"- sources_independent: {evaluation.sources_are_independent}\n"
        f"- adversarial_addressed: {evaluation.adversarial_critique_addressed}\n"
        f"- confidence_matches: {evaluation.confidence_matches_evidence}\n\n"
        f"Blackboard state:\n{blackboard_summary[:1000]}"
    )
    from app.utils.rate_limiter import gemini_acquire
    await gemini_acquire()
    result = await _reflection_agent.run(prompt)
    return result.output
