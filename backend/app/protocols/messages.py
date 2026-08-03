from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field


# ── 1. Primitive evidence item ─────────────────────────────────────────────────
class EvidenceItem(BaseModel):
    source_id: str
    url: str
    title: str = ""
    snippet: str
    source_domain: str
    published_date: str | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    retrieval_backend: str


# ── 2. Inter-agent request (routed through Orchestrator only) ──────────────────
class AgentRequest(BaseModel):
    from_agent: str
    to_agent: str
    claim_id: str
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)


# ── 3. Task in the dynamic plan ───────────────────────────────────────────────
class Task(BaseModel):
    task_id: str
    agent: str
    claim_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    completed: bool = False
    retry_count: int = 0
    retry_reason: str | None = None
    parallel_group: int | None = None  # Tasks with same group int are asyncio.gather()'d


# ── 4. Mutable plan ───────────────────────────────────────────────────────────
class Plan(BaseModel):
    tasks: list[Task] = Field(default_factory=list)

    def next_task(self) -> Task | None:
        return next((t for t in self.tasks if not t.completed), None)

    def mark_done(self, task_id: str) -> None:
        for t in self.tasks:
            if t.task_id == task_id:
                t.completed = True

    def requeue(self, task_id: str, reason: str) -> None:
        for t in self.tasks:
            if t.task_id == task_id:
                t.completed = False
                t.retry_count += 1
                t.retry_reason = reason

    def all_done(self) -> bool:
        return all(t.completed for t in self.tasks)


# ── 5. Agent finding (append-only to Blackboard) ──────────────────────────────
class Finding(BaseModel):
    agent: str
    claim_id: str
    stance: Literal["supports", "contradicts", "mixed", "insufficient_evidence"]
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    requests: list[AgentRequest] = Field(default_factory=list)


# ── 6. Evaluator LLM schema ──────────────────────────────────────────────────
class EvidenceEvaluation(BaseModel):
    sources_are_independent: bool
    adversarial_critique_addressed: bool
    confidence_matches_evidence: bool
    claim_fully_decomposed: bool
    readiness_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Evaluator LLM qualitative readiness score")
    epistemic_reasoning: str = Field(default="", description="Epistemic rationale for readiness score")
    quality_note: str


def compute_stopping_score(ev: EvidenceEvaluation) -> float:
    """Returns LLM qualitative readiness score if set, else calculates weighted score."""
    if ev.readiness_score > 0.0:
        return round(ev.readiness_score, 2)
    score = 0.0
    if ev.sources_are_independent:         score += 0.30
    if ev.adversarial_critique_addressed:  score += 0.30
    if ev.confidence_matches_evidence:     score += 0.25
    if ev.claim_fully_decomposed:          score += 0.15
    return round(score, 2)


# ── 7. Reflexion memory entry ─────────────────────────────────────────────────
class AgentReflection(BaseModel):
    root_cause: str
    correction: str
    lesson: str


# ── 8. Adversarial critique ───────────────────────────────────────────────────
class AdversarialCritique(BaseModel):
    verdict_stands: bool
    strongest_counter: str
    unexamined_angle: str | None = None


# ── 9. Final report ───────────────────────────────────────────────────────────
class VerificationReport(BaseModel):
    run_id: str
    raw_input: str
    overall_verdict: Literal["true", "false", "misleading", "unverifiable", "inconclusive"]
    credibility_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    claim_findings: list[dict[str, Any]]
    adversarial_summary: str
    evidence_used: list[EvidenceItem]
    source_credibility_notes: str
    processing_time_seconds: float
    iterations_used: int
    budget_exhausted: bool
    ai_opinion: str | None = Field(default=None, description="AI narrative opinion explaining the final verdict rationale, key evidence highlights, and credibility analysis.")


# ── 10. LLM-Authoritative Orchestrator Decisions ──────────────────────────────
class DelegateAction(BaseModel):
    """Orchestrator wants to run one or more sub-agent tasks next."""
    tasks: list[Task] = Field(description="Sub-agent tasks to run in this round")
    reasoning: str = Field(description="One sentence: why these agents were selected")

class FinalizeAction(BaseModel):
    """Orchestrator decides sufficiency criteria are met and finalizes the run."""
    report: VerificationReport = Field(description="Complete structured verification report")
    reasoning: str = Field(description="One sentence: why sufficiency criteria are met")

class OrchestratorDecision(BaseModel):
    """Tagged union for iteration-by-iteration Orchestrator LLM decision."""
    action: Literal["delegate", "finalize"] = Field(description="Action type: delegate or finalize")
    delegate: DelegateAction | None = None
    finalize: FinalizeAction | None = None
