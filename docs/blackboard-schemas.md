# Blackboard Schemas — Scrutin Platform

All inter-agent message types, the shared Blackboard state model, and the final report schema.
Every object here is a validated Pydantic `BaseModel`. No raw dicts cross agent boundaries.

---

## 1. Primitive Building Blocks

```python
# app/protocols/messages.py
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """A single piece of evidence stored on the Blackboard by ID."""
    source_id: str          # "WB1", "RED1", "FC1", etc.
    url: str
    title: str = ""
    snippet: str            # Max 500 chars — relevance-ranked passage
    source_domain: str      # e.g. "reuters.com"
    published_date: Optional[str] = None   # YYYY-MM-DD or None
    relevance_score: float  # 0.0 – 1.0 (from Cross-Encoder or API)
    retrieval_backend: str  # "serper" | "duckduckgo" | "factcheck_api" | "reddit" | "wikipedia"


class AgentRequest(BaseModel):
    """A sub-agent's request for another agent's help, routed through the Orchestrator."""
    from_agent: str         # e.g. "evidence_agent"
    to_agent: str           # e.g. "credibility_agent"
    claim_id: str
    reason: str             # Why this delegation is needed
    payload: dict = Field(default_factory=dict)  # Agent-specific params (e.g. {"domain": "bbc-mirror.net"})
```

---

## 2. Agent Output: Finding

This is what every sub-agent writes to the Blackboard when it completes a task.

```python
class Finding(BaseModel):
    """The structured output of any sub-agent. Append-only to Blackboard.findings."""
    agent: str              # "decomposition" | "evidence" | "credibility" | "forensics" | "adversarial"
    claim_id: str           # Which atomic claim this finding addresses
    stance: Literal["supports", "contradicts", "mixed", "insufficient_evidence"]
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Blackboard store keys only — never raw content. e.g. ['WB1', 'WB2']"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Calibrated float. Derived from deterministic-picker booleans, not LLM freeform."
    )
    rationale: str          # Agent's reasoning in plain English — shown in terminal trace
    requests: list[AgentRequest] = Field(
        default_factory=list,
        description="Outbound delegation requests back to Orchestrator. Never direct agent calls."
    )
```

---

## 3. Orchestration: Plan & Task

```python
class Task(BaseModel):
    """A single unit of work in the Orchestrator's dynamic plan."""
    task_id: str            # "T1", "T2", etc.
    agent: str              # Which agent to invoke
    claim_id: str
    params: dict = Field(default_factory=dict)   # e.g. {"query": "...", "domain": "..."}
    completed: bool = False
    retry_count: int = 0
    retry_reason: Optional[str] = None          # Set by evaluator on retry


class Plan(BaseModel):
    """The mutable dynamic plan. Replanned on every REFLECT step."""
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
```

---

## 4. Evaluator Output: Deterministic-Picker Schema

The Orchestrator's built-in self-critique step. LLM commits to booleans; Python computes the `stop` signal.

```python
class EvidenceEvaluation(BaseModel):
    """
    Deterministic-picker evaluation schema.
    Python computes pass/fail from independent boolean features — never a raw LLM float.
    Source: FareedKhan-dev/all-agentic-architectures — reflexion.py _ReflexionEvaluation
    """
    sources_are_independent: bool = Field(
        description="True iff the supporting sources do NOT all trace back to a single wire story or press release."
    )
    adversarial_critique_addressed: bool = Field(
        description="True iff the provisional verdict explicitly addresses the Adversarial agent's strongest counter-argument."
    )
    confidence_matches_evidence: bool = Field(
        description="True iff the stated confidence is consistent with the number and quality of independent sources found."
    )
    claim_fully_decomposed: bool = Field(
        description="True iff all load-bearing sub-claims in the input have been assigned a Finding on the Blackboard."
    )
    quality_note: str = Field(
        description="ONE specific observation about the weakest remaining gap in the evidence set."
    )

def compute_stopping_score(ev: EvidenceEvaluation) -> float:
    """Python signal composer — not the LLM."""
    score = 0.0
    if ev.sources_are_independent:       score += 0.30
    if ev.adversarial_critique_addressed: score += 0.30
    if ev.confidence_matches_evidence:    score += 0.25
    if ev.claim_fully_decomposed:         score += 0.15
    return round(score, 2)  # >= 0.85 → stop; < 0.85 → replan
```

---

## 5. Reflexion: Self-Critique Memory Entry

Written to episodic memory when a run ends in insufficient_evidence or is retried.

```python
class AgentReflection(BaseModel):
    """
    Verbal reflection stored in SQLite episodic memory.
    Source: FareedKhan-dev/all-agentic-architectures — reflexion.py _SelfReflection
    """
    root_cause: str = Field(
        description="ONE SENTENCE: precisely why the current evidence set is insufficient. "
                    "Reference the specific gap (e.g., 'All 3 sources are AP republications')."
    )
    correction: str = Field(
        description="ONE SENTENCE imperative: the concrete next search step."
    )
    lesson: str = Field(
        description="2-4 sentences in second person stored verbatim for future similar claims."
    )
```

---

## 6. The Blackboard

The single run-scoped shared state object passed to all agents via dependency injection.

```python
# app/protocols/blackboard.py
from __future__ import annotations
import sqlite3
from typing import Any, Optional
from pydantic import BaseModel, Field


class Blackboard(BaseModel):
    """
    Run-scoped shared state. Serializable — flushed to SQLite episodic log at completion.
    No agent may overwrite another agent's findings section.
    Context externalization: heavy data stored by ID, agents pass IDs not raw content.
    """
    run_id: str
    raw_input: str
    input_type: Literal["text", "url", "image", "video"] = "text"

    # --- Decomposition outputs ---
    atomic_claims: dict[str, str] = Field(
        default_factory=dict,
        description="claim_id -> claim_text. e.g. {'C1': 'The vaccine causes autism.'}"
    )

    # --- Evidence store: heavy content stored by pointer ID ---
    evidence_store: dict[str, Any] = Field(
        default_factory=dict,
        description="'WB1' -> {url, title, snippet, content_markdown}. Agents receive IDs, not content."
    )

    # --- Agent findings: APPEND-ONLY, never overwrite ---
    findings: list[dict] = Field(default_factory=list)

    # --- Orchestration ---
    plan: Plan = Field(default_factory=Plan)
    iterations: int = 0
    budget_limit: int = 20
    provisional_verdict: Optional[str] = None
    final_report: Optional[dict] = None

    # --- Model Config ---
    model_config = {"arbitrary_types_allowed": True}

    def next_evidence_id(self, prefix: str) -> str:
        count = sum(1 for k in self.evidence_store if k.startswith(prefix))
        return f"{prefix}{count + 1}"

    def store_evidence(self, prefix: str, data: dict) -> str:
        eid = self.next_evidence_id(prefix)
        self.evidence_store[eid] = data
        return eid  # Return pointer — agents store this, not the raw data

    def append_finding(self, finding: Finding) -> None:
        self.findings.append(finding.model_dump())

    def get_findings_for_claim(self, claim_id: str) -> list[dict]:
        return [f for f in self.findings if f["claim_id"] == claim_id]

    def flush_to_sqlite(self, conn: sqlite3.Connection) -> None:
        """Must be called at run completion — even on error. Non-negotiable audit trail."""
        conn.execute(
            """INSERT OR REPLACE INTO episodic_runs (run_id, raw_input, data_json, created_at)
               VALUES (?, ?, ?, datetime('now'))""",
            (self.run_id, self.raw_input, self.model_dump_json())
        )
        conn.commit()
```

---

## 7. Final Report Schema

```python
class VerificationReport(BaseModel):
    """The final structured output written to blackboard.final_report."""
    run_id: str
    raw_input: str
    overall_verdict: Literal["true", "false", "misleading", "unverifiable", "inconclusive"]
    credibility_score: float = Field(ge=0.0, le=100.0, description="0=False, 100=True")
    confidence: float = Field(ge=0.0, le=1.0)
    claim_findings: list[dict]      # One Finding dict per atomic claim
    adversarial_summary: str        # Adversarial agent's critique summary
    evidence_used: list[EvidenceItem]  # All evidence items referenced
    source_credibility_notes: str   # Credibility agent's structured notes
    processing_time_seconds: float
    iterations_used: int
    budget_exhausted: bool          # True if stopped due to budget, not confidence
```

---

## Evidence ID Prefix Convention

| Prefix | Source |
|--------|--------|
| `WB`   | Web search (Serper/DDG) |
| `FC`   | Google Fact Check API match |
| `RD`   | Reddit thread |
| `WK`   | Wikipedia article |
| `YT`   | YouTube transcript chunk |
| `TR`   | Media file transcript (Whisper) |
| `NW`   | News API article |
