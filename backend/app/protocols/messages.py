from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── 1. Primitive evidence item ─────────────────────────────────────────────────
class EvidenceItem(BaseModel):
    source_id: str
    url: str
    title: str = ""
    snippet: str
    source_domain: str
    published_date: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    retrieval_backend: str


# ── 2. Inter-agent request (routed through Orchestrator only) ──────────────────
class AgentRequest(BaseModel):
    from_agent: str
    to_agent: str
    claim_id: str
    reason: str
    payload: dict = Field(default_factory=dict)


# ── 3. Task in the dynamic plan ───────────────────────────────────────────────
class Task(BaseModel):
    task_id: str
    agent: str
    claim_id: str
    params: dict = Field(default_factory=dict)
    completed: bool = False
    retry_count: int = 0
    retry_reason: Optional[str] = None
    parallel_group: Optional[int] = None  # Tasks with same group int are asyncio.gather()'d


# ── 4. Mutable plan ───────────────────────────────────────────────────────────
class Plan(BaseModel):
    tasks: list[Task] = Field(default_factory=list)

    def next_task(self) -> Optional[Task]:
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


# ── 6. Evaluator deterministic-picker schema ──────────────────────────────────
class EvidenceEvaluation(BaseModel):
    sources_are_independent: bool
    adversarial_critique_addressed: bool
    confidence_matches_evidence: bool
    claim_fully_decomposed: bool
    quality_note: str


def compute_stopping_score(ev: EvidenceEvaluation) -> float:
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
    unexamined_angle: Optional[str] = None


# ── 9. Final report ───────────────────────────────────────────────────────────
class VerificationReport(BaseModel):
    run_id: str
    raw_input: str
    overall_verdict: Literal["true", "false", "misleading", "unverifiable", "inconclusive"]
    credibility_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    claim_findings: list[dict]
    adversarial_summary: str
    evidence_used: list[EvidenceItem]
    source_credibility_notes: str
    processing_time_seconds: float
    iterations_used: int
    budget_exhausted: bool
