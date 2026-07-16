---
name: scrutin-patterns
description: Production code patterns for the Scrutin multi-agent fact-checking platform. Covers PydanticAI agent wiring, the Reflexion self-critique loop, the Debate/Adversarial pattern, Blackboard state management, and the deterministic-picker scoring discipline. Trigger this skill when writing any agent, orchestrator, tool, or memory module for the Scrutin project.
---

# Scrutin Platform — Implementation Patterns

Derived from real source code in the following repos studied for this project:
- `FareedKhan-dev/all-agentic-architectures` — Blackboard, Debate, Reflexion implementations
- `KLOSYX/FCAgent` — Web search result structuring pattern
- `pydantic/pydantic-ai` — Agent, tool, dependency injection patterns
- `mem0ai/mem0` — Extract-Deduplicate-Commit memory pipeline

---

## Pattern 1: PydanticAI Agent with Typed Deps & Structured Output

This is the canonical agent setup for every agent in the system. Use dependency injection for the Blackboard and API config — never global variables.

```python
# app/agents/base.py
from __future__ import annotations
from dataclasses import dataclass
from pydantic import BaseModel
from pydantic_ai import Agent

@dataclass
class AgentDeps:
    """Passed to every agent via dependency injection."""
    blackboard: "Blackboard"  # The shared run-scoped state object
    config: dict              # API keys and config values
    run_budget: int = 10      # Max tool calls remaining for this agent

# Every agent output is a validated Pydantic model — never a raw string
class Finding(BaseModel):
    agent: str
    claim_id: str
    stance: str           # "supports" | "contradicts" | "mixed" | "insufficient_evidence"
    evidence_ids: list[str]   # Blackboard keys (e.g. ["WB1", "WB2"]) NOT raw text
    confidence: float         # 0.0 to 1.0 — must be calibrated, not vibes
    rationale: str
    requests: list["AgentRequest"] = []

class AgentRequest(BaseModel):
    from_agent: str
    to_agent: str
    reason: str
    payload: dict

# Agent instantiation pattern — model string is the ONLY coupling to a provider
evidence_agent = Agent(
    "google-gla:gemini-2.5-flash",
    deps_type=AgentDeps,
    output_type=Finding,
    system_prompt=(
        "You are the Evidence & Corroboration Agent. "
        "Your job is to gather and evaluate independent evidence for and against a given claim. "
        "You NEVER set the final credibility score. You hand a stance WITH evidence to the Orchestrator. "
        "You NEVER cite three outlets that all republished the same wire story as 'three sources'."
    ),
)
```

---

## Pattern 2: Deterministic-Picker Scoring (from all-agentic-architectures)

**Source:** `reflexion.py` `_ReflexionEvaluation` schema + `blackboard.py` `_AgentBid` schema.

The LLM commits to multiple independent boolean features. Python composes the deciding signal. This prevents the flat-band pathology where a raw LLM confidence score clusters around 0.7 for everything.

```python
# app/orchestrator/evaluator.py
from __future__ import annotations
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class EvidenceEvaluation(BaseModel):
    """Deterministic-picker schema: LLM commits to booleans, Python computes verdict."""
    sources_are_independent: bool = Field(
        description="True iff the supporting sources do NOT all trace back to a single wire story or press release."
    )
    adversarial_critique_addressed: bool = Field(
        description="True iff the Orchestrator's provisional verdict explicitly addresses the Adversarial agent's strongest counter-argument."
    )
    confidence_matches_evidence: bool = Field(
        description="True iff the stated confidence is consistent with the number and quality of independent sources found."
    )
    quality_note: str = Field(
        description="ONE specific observation about the weakest point in the current evidence set."
    )

def compute_stopping_score(ev: EvidenceEvaluation) -> float:
    """Python composes the signal — not the LLM."""
    score = 0.0
    if ev.sources_are_independent:
        score += 0.4
    if ev.adversarial_critique_addressed:
        score += 0.4
    if ev.confidence_matches_evidence:
        score += 0.2
    return score  # >= 0.8 means stopping criteria met

evaluator_agent = Agent(
    "google-gla:gemini-2.5-flash",
    output_type=EvidenceEvaluation,
    system_prompt="You are a rigorous evidence evaluator. Commit to specific boolean judgments — do not hedge.",
)
```

---

## Pattern 3: Reflexion Self-Critique Loop (from `reflexion.py`)

**Source:** `FareedKhan-dev/all-agentic-architectures/src/.../reflexion.py`

The `_SelfReflection` schema drives the verbal-reflection step that writes actionable corrections into Episodic memory so future runs on similar claims avoid the same retrieval mistake.

```python
# app/orchestrator/reflection.py
from __future__ import annotations
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class AgentReflection(BaseModel):
    """Actionable verbal reflection — stored in episodic memory for future similar claims."""
    root_cause: str = Field(
        description="ONE SENTENCE: precisely WHY the current evidence set is insufficient. "
                    "Reference the specific gap (e.g., 'All 3 sources are AP republications, "
                    "not independent reporting')."
    )
    correction: str = Field(
        description="ONE SENTENCE imperative: the concrete next search step to take "
                    "(e.g., 'Search specifically for local reporting from the region mentioned in the claim')."
    )
    lesson: str = Field(
        description="2-4 sentences in second person. Combine root_cause + correction + "
                    "a generalizable lesson for structurally similar claims. "
                    "This text is stored verbatim in episodic memory."
    )

reflection_agent = Agent(
    "google-gla:gemini-2.5-flash",
    output_type=AgentReflection,
    system_prompt=(
        "You are a self-critique agent reviewing an insufficient fact-checking run. "
        "Be specific and actionable. Vague reflections (e.g., 'search more') are useless."
    ),
)
```

---

## Pattern 4: Debate / Adversarial Verification (from `debate.py`)

**Source:** `FareedKhan-dev/all-agentic-architectures/src/.../debate.py`  
**Paper:** Du et al., *Improving Factuality and Reasoning through Multiagent Debate* (2023)

The Adversarial Verifier uses an independent critique schema. It NEVER gets the Evidence agent's reasoning trace — only the raw evidence IDs and the provisional verdict.

```python
# app/agents/adversarial_agent.py
from __future__ import annotations
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class AdversarialCritique(BaseModel):
    """The Adversarial Verifier's structured output — one critique per invocation."""
    verdict_stands: bool = Field(
        description="True iff you cannot construct a plausible counter-argument that materially "
                    "undermines the provisional verdict using ONLY the evidence provided. "
                    "False means the Orchestrator must lower confidence or reopen evidence gathering."
    )
    strongest_counter: str = Field(
        description="The single strongest good-faith alternative explanation or counter-argument. "
                    "If verdict_stands=True, write the weakest point in the existing verdict instead."
    )
    unexamined_angle: str | None = Field(
        None,
        description="A specific, named source or search angle that was NOT checked and could "
                    "change the verdict. Only populate if you have a concrete suggestion, not a vague 'look harder'."
    )

adversarial_agent = Agent(
    # MUST be on a different provider than the Evidence agent — no shared training biases
    "groq:llama-3.3-70b-versatile",
    output_type=AdversarialCritique,
    system_prompt=(
        "You are the Adversarial Verifier. Your ONLY job is to steelman the opposition. "
        "You are given raw evidence and a provisional verdict. Construct the strongest possible "
        "counter-argument using ONLY that evidence. Do NOT do new research unless you identify "
        "a specific named source that was missed."
    ),
)
```

---

## Pattern 5: Blackboard State (from `blackboard.py`)

**Source:** `FareedKhan-dev/all-agentic-architectures/src/.../blackboard.py`

The Blackboard uses append-only semantics for findings. Agents write to their own namespaced section and never edit other agents' sections.

```python
# app/protocols/blackboard.py
from __future__ import annotations
from typing import Any
import sqlite3
import json
from pydantic import BaseModel, Field

class Blackboard(BaseModel):
    """Run-scoped shared state. Serializable for SQLite episodic log persistence."""
    run_id: str
    raw_input: str
    input_type: str = "text"  # "text" | "url" | "image" | "video"

    # Decomposition outputs
    atomic_claims: dict[str, str] = Field(default_factory=dict)  # claim_id -> claim_text

    # Evidence store — all scraped content stored by ID to keep agent contexts lean
    evidence_store: dict[str, Any] = Field(default_factory=dict)  # "WB1" -> {url, content, ...}

    # Agent findings — append-only, never overwrite
    findings: list[dict] = Field(default_factory=list)

    # Orchestration metadata
    plan_tasks: list[dict] = Field(default_factory=list)
    iterations: int = 0
    budget_limit: int = 20
    provisional_verdict: str | None = None
    final_report: dict | None = None

    def store_evidence(self, prefix: str, data: dict) -> str:
        """Store evidence by auto-incremented ID and return the ID pointer."""
        idx = sum(1 for k in self.evidence_store if k.startswith(prefix))
        evidence_id = f"{prefix}{idx + 1}"
        self.evidence_store[evidence_id] = data
        return evidence_id

    def append_finding(self, finding: dict) -> None:
        """Append-only — never overwrites existing findings."""
        self.findings.append(finding)

    def flush_to_sqlite(self, conn: sqlite3.Connection) -> None:
        """Persist to episodic log at run completion. Must be called even on crashes."""
        conn.execute(
            "INSERT OR REPLACE INTO episodic_runs (run_id, data, created_at) VALUES (?, ?, datetime('now'))",
            (self.run_id, self.model_dump_json())
        )
        conn.commit()
```

---

## Pattern 6: FCAgent Web Search Result Structuring

**Source:** `KLOSYX/FCAgent/retriever/web_search.py`

The FCAgent pattern of wrapping LLM-post-processed search results in a typed schema with `key_info` + `url` per item is the canonical approach for our Evidence tool wrappers.

```python
# app/tools/search_tools.py
from __future__ import annotations
from typing import TypedDict
from pydantic import BaseModel, Field

class SearchItem(TypedDict):
    key_info: str   # LLM-extracted relevant fact from this source
    url: str        # provenance link

class WebSearchResult(BaseModel):
    """Typed, validated output from the web search tool — never a raw dict."""
    results: list[SearchItem] = Field(description="Ranked search results with extracted key facts.")
    backend_used: str         # "serper" | "duckduckgo"
    query_used: str           # The actual query string sent to the search engine
    total_found: int

# Tool registration in PydanticAI
from pydantic_ai import Agent
evidence_agent = Agent("google-gla:gemini-2.5-flash")

@evidence_agent.tool
async def web_search(ctx, query: str, date_from: str | None = None, date_to: str | None = None) -> WebSearchResult:
    """Search the web for evidence about a factual claim using Google Serper API."""
    from app.tools.lib.grounding import web_search as _search
    items, artifact = _search(
        query=query,
        date_range=(date_from, date_to) if date_from else None,
        config=ctx.deps.config,
        backend="auto",
    )
    # Store full content on Blackboard by ID pointer — not in the return value
    for item in items:
        ctx.deps.blackboard.store_evidence("WB", item)
    return WebSearchResult(
        results=[{"key_info": i["snippet"], "url": i["url"]} for i in items[:5]],
        backend_used=artifact.get("label", "unknown"),
        query_used=query,
        total_found=artifact.get("resultCount", len(items)),
    )
```

---

## Pattern 7: Memory EDC Pipeline (from `mem0`)

**Source:** `mem0ai/mem0` — extract-dedupe-commit pattern for source reputation.

```python
# app/memory/longterm.py
from __future__ import annotations
import aiosqlite

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS source_reputation (
    domain TEXT PRIMARY KEY,
    credibility_score REAL NOT NULL DEFAULT 50.0,
    total_runs INTEGER NOT NULL DEFAULT 0,
    failed_runs INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

async def update_source_reputation(db_path: str, domain: str, check_failed: bool) -> None:
    """
    EDC Pipeline:
    1. EXTRACT — Read existing profile.
    2. DEDUPLICATE — Compute new score delta.
    3. COMMIT — Write only if delta > 2.0 (avoid noise commits).
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")

        # 1. EXTRACT
        async with db.execute(
            "SELECT credibility_score, total_runs, failed_runs FROM source_reputation WHERE domain = ?",
            (domain,)
        ) as cursor:
            row = await cursor.fetchone()

        # 2. DEDUPLICATE — compute new values
        if row:
            score, total, failed = row
            total += 1
            if check_failed:
                failed += 1
            new_score = max(0.0, min(100.0, 100.0 * (1.0 - failed / total)))
            delta = abs(new_score - score)
        else:
            total, failed = 1, (1 if check_failed else 0)
            new_score = 0.0 if check_failed else 100.0
            delta = 100.0  # Always commit new domains

        # 3. COMMIT — only if meaningful change
        if delta >= 2.0:
            await db.execute(
                """INSERT INTO source_reputation (domain, credibility_score, total_runs, failed_runs, last_updated)
                   VALUES (?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(domain) DO UPDATE SET
                       credibility_score = excluded.credibility_score,
                       total_runs = excluded.total_runs,
                       failed_runs = excluded.failed_runs,
                       last_updated = excluded.last_updated""",
                (domain, new_score, total, failed)
            )
            await db.commit()
```
