# Scrutin — Detailed Architecture Reference

This is the deep technical documentation for the Scrutin platform: how the Blackboard, agents, orchestration loop, scoring, memory tiers, and tool layer fit together. For a project overview start with [`README.md`](./README.md); for getting it running, see [`SETUP.md`](./SETUP.md).

---

## 1. Design Philosophy

Scrutin treats claim verification as a variable-depth reasoning task rather than a fixed retrieval pipeline. The system is built around four non-negotiable rules (full list in [`AGENTS.md`](./AGENTS.md)):

1. **Hub-and-spoke only.** Sub-agents never call each other. Every cross-agent request is a typed `AgentRequest` placed on the Blackboard; the Orchestrator processes it on its next loop iteration.
2. **Structured output everywhere.** Every agent output is a validated Pydantic `BaseModel`. No raw dicts, no regex-parsed LLM text.
3. **Deterministic-picker scoring.** The LLM never emits a raw confidence float as a judgment. It commits to independent boolean features; Python composes the final numeric score. This avoids the "flat-band" pathology where raw LLM confidence scores cluster meaninglessly around ~0.7.
4. **Context externalization.** Heavy content (scraped HTML, transcripts) lives on the Blackboard keyed by short IDs (`WB1`, `TR3`, `FC1`...). Agents pass IDs in their messages, never raw content.

---

## 2. The Blackboard

The Blackboard is a single, run-scoped Pydantic model, passed to every agent via dependency injection. It is the *only* channel of communication between agents.

```python
class Blackboard(BaseModel):
    run_id: str
    raw_input: str
    input_type: Literal["text", "url", "image", "video"] = "text"

    atomic_claims: dict[str, str] = Field(default_factory=dict)       # claim_id -> claim_text
    evidence_store: dict[str, Any] = Field(default_factory=dict)      # "WB1" -> {url, title, snippet, ...}
    findings: list[dict] = Field(default_factory=list)                # append-only, never overwritten

    plan: Plan = Field(default_factory=Plan)
    iterations: int = 0
    budget_limit: int = 20
    provisional_verdict: Optional[str] = None
    final_report: Optional[dict] = None
```

Key invariants:
- **No agent overwrites another agent's findings.** `findings` is append-only (`list.append()` semantics — mirrors `Annotated[list, operator.add]` in the reference Blackboard implementation).
- **Evidence is stored by pointer.** `blackboard.store_evidence(prefix, data)` auto-increments an ID (`WB1`, `WB2`, ...) and returns just the pointer; agents carry the pointer, not the payload, in their `Finding.evidence_ids`.
- **The Blackboard is flushed to SQLite at run completion — even on error.** This is the non-negotiable audit trail (`flush_to_sqlite`).

### Evidence ID prefix convention

| Prefix | Source |
|--------|--------|
| `WB` | Web search (Serper/DDG) |
| `FC` | Google Fact Check API match |
| `RD` | Reddit thread |
| `WK` | Wikipedia article |
| `YT` | YouTube transcript chunk |
| `TR` | Media file transcript (Whisper) |
| `NW` | News API article |

---

## 3. Message Types

### `Finding` — every sub-agent's output

```python
class Finding(BaseModel):
    agent: str
    claim_id: str
    stance: Literal["supports", "contradicts", "mixed", "insufficient_evidence"]
    evidence_ids: list[str] = Field(default_factory=list)   # Blackboard keys only
    confidence: float = Field(ge=0.0, le=1.0)                # derived, not freeform LLM float
    rationale: str
    requests: list[AgentRequest] = Field(default_factory=list)
```

Note the Credibility agent's `stance` is *always* `"mixed"` — source credibility is deliberately never modeled as binary.

### `AgentRequest` — the only inter-agent channel

```python
class AgentRequest(BaseModel):
    from_agent: str
    to_agent: str
    claim_id: str
    reason: str
    payload: dict = Field(default_factory=dict)
```

These never trigger a direct call — they're queued on the Blackboard and the Orchestrator turns them into new `Task`s on its next replan.

### `Plan` / `Task` — the Orchestrator's dynamic execution plan

```python
class Task(BaseModel):
    task_id: str
    agent: str
    claim_id: str
    params: dict = Field(default_factory=dict)
    completed: bool = False
    retry_count: int = 0
    retry_reason: Optional[str] = None

class Plan(BaseModel):
    tasks: list[Task] = Field(default_factory=list)
    # next_task(), mark_done(task_id), requeue(task_id, reason)
```

The plan is **replanned on every REFLECT step** — it is not a static DAG. `requeue()` bumps `retry_count` and stamps a `retry_reason` so the agent knows *why* it's being asked to redo work.

Full schema source: [`blackboard-schemas.md`](./blackboard-schemas.md).

---

## 4. Deterministic-Picker Scoring

The Orchestrator's built-in self-critique step never lets an LLM directly emit the number that decides whether the run stops. Instead the LLM commits to independent boolean judgments, and Python composes the score.

```python
class EvidenceEvaluation(BaseModel):
    sources_are_independent: bool
    adversarial_critique_addressed: bool
    confidence_matches_evidence: bool
    claim_fully_decomposed: bool
    quality_note: str   # ONE specific observation about the weakest remaining gap

def compute_stopping_score(ev: EvidenceEvaluation) -> float:
    score = 0.0
    if ev.sources_are_independent:        score += 0.30
    if ev.adversarial_critique_addressed:  score += 0.30
    if ev.confidence_matches_evidence:     score += 0.25
    if ev.claim_fully_decomposed:          score += 0.15
    return round(score, 2)   # >= 0.85 → stop; < 0.85 → replan
```

This is the same pattern used across the codebase for any scoring surface: **never ask an LLM for a raw confidence number as a final judgment** — ask for categorical/boolean sub-judgments and let deterministic code combine them.

---

## 5. Reflexion Self-Critique Loop

When a run ends in `insufficient_evidence`, or a task is retried, the system writes a structured verbal reflection to episodic memory so future runs on structurally similar claims don't repeat the same retrieval mistake.

```python
class AgentReflection(BaseModel):
    root_cause: str    # ONE SENTENCE — precisely why evidence is insufficient
    correction: str    # ONE SENTENCE imperative — the concrete next search step
    lesson: str        # 2-4 sentences, second person, stored verbatim for future similar claims
```

Example `root_cause`: *"All 3 sources are AP republications, not independent reporting."* Example `correction`: *"Search specifically for local reporting from the region mentioned in the claim."*

---

## 6. Adversarial Verification (Debate Pattern)

The Adversarial Verifier's isolation is a hard architectural constraint, not a style choice:

- It receives **only**: (a) raw compiled evidence items (IDs + snippets) from the Blackboard, and (b) the Orchestrator's provisional verdict string.
- It does **not** receive the Evidence Agent's reasoning trace, planning notes, or intermediate thoughts.
- It runs on a **different model provider** (Groq/Llama) than the Evidence Agent (Gemini), specifically to avoid shared training biases between the two roles.

```python
class AdversarialCritique(BaseModel):
    verdict_stands: bool           # False → Orchestrator must lower confidence or reopen evidence
    strongest_counter: str         # best good-faith counter-argument (or weakest point, if verdict stands)
    unexamined_angle: str | None   # a specific named source/angle that was missed, if any
```

Specifically, the Adversarial agent looks for:
1. **Cherry-picking** — contradicting evidence that was available but ignored.
2. **Single-source over-reliance** — verdict resting on one outlet.
3. **Unexamined assumptions.**
4. **Alternative explanations** for the same evidence.
5. **Echo-chamber detection** — do all sources trace back to the same original claim (the "RAMA pattern")?

It may request **one** targeted follow-up search if it names a specific missed source or angle — it may not run a full second evidence pass; that stays the Evidence agent's job.

---

## 7. The Six Agents — Prompt Contracts

Full system prompts: [`agent-system-prompts.md`](./agent-system-prompts.md). Summary of each agent's hard prohibitions (these are enforced at the prompt level, not just convention):

- **Orchestrator** — never fabricates evidence (only reweighs what sub-agents produced), never skips the Adversarial step, never calls sub-agents directly.
- **Decomposition** — makes no truth judgment, uses no external tools, never invents a claim not actually present in the input (self-checks for this explicitly).
- **Evidence** — never sets the final credibility score, never judges source trustworthiness (delegates via `AgentRequest` instead), never does forensic media analysis. Checks the fact-check DB *before* any web search (fast path). Treats N outlets republishing one wire story as one piece of evidence, not N.
- **Credibility** — never judges claim content truth, never runs new web searches, never writes reputation updates directly (proposes them; Orchestrator commits). `"unknown"` is a valid, honest output for obscure sources — it must not fabricate a score.
- **Forensics** — never judges whether the caption/claim about the media is true (that's Evidence's job — it delegates via `AgentRequest`), never forces a binary call when signals conflict. Distinguishes three failure modes explicitly: technically manipulated, authentic-but-false-context, and authentic-but-misleading-framing.
- **Adversarial** — never runs general new searches, never inherits Evidence's reasoning framing, never sets the final verdict (can only force a re-open via `verdict_stands=False`).

---

## 8. Memory Tiers

| Tier | Store | Rule |
|---|---|---|
| **Working** | In-process Python dict | Never auto-promoted; Orchestrator explicitly calls `episodic.record_run()` at completion |
| **Episodic** | SQLite (`aiosqlite`, WAL mode) | Append-only; used for recall ("have we seen this claim before?"), never as ground truth |
| **Semantic** | Pinecone (free tier, single index) | Claim embeddings (`gemini-embedding-001`, dim 768) + perceptual hashes (`imagehash`), separate namespaces; never a verdict substitute |
| **Long-term / reputation** | SQLite | Extract-Deduplicate-Commit (EDC) pipeline: read existing profile → compute delta → write only if score changes by > 2 points |

### SQLite tables (`scrutin.db`)

- `episodic_runs` — full run history, verdict, score, confidence, complete Blackboard JSON dump.
- `source_reputation` — domain → credibility score, WHOIS registrar/registered date, `is_recent_domain` flag (< 180 days).
- `calibration_log` — per-run, per-agent stated confidence vs. actual outcome, feeding the ECE calculation.
- `claim_similarity_cache` — metadata store paired with Pinecone vector IDs for fast duplicate-claim lookup.

Every connection **must** set `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON` — this is mandatory to avoid `database is locked` errors under async access. Full DDL: [`database-schema.md`](./database-schema.md).

### Pinecone index

- Index `scrutin-claims`, `dimension=768`, `metric="cosine"`, namespace `claims`.
- Media perceptual hashing (`imagehash.phash`) is **not yet promoted to Pinecone** — free tier allows only one index, and the `claims` namespace already uses it at `dimension=768`. Media hashes are stored as raw hex in SQLite for now; the intended future migration (once a second index is available) is `dimension=64, metric="hamming"` in its own `media` namespace.
- Embedding model is explicitly `gemini-embedding-001` — not an OpenAI embedding model (different provider, different dimensionality).

### Extract-Deduplicate-Commit (EDC) pipeline (source reputation)

```python
# 1. EXTRACT — read existing profile (score, total_runs, failed_runs)
# 2. DEDUPLICATE — compute new score = 100 * (1 - failed/total); delta = |new - old|
# 3. COMMIT — only write if delta >= 2.0 (avoids noisy commits); always commit brand-new domains
```

---

## 9. Tool Layer

Tools are **stateless pure functions**: typed Pydantic request in, typed Pydantic response out. A tool never makes a judgment call — if a function needs an LLM to interpret its own output, that logic belongs in an agent's reasoning step, not in `tools/`.

| Module | Wraps |
|---|---|
| `search_tools.py` | Serper web search + Jina Reader scraping + Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) re-ranking → top 5 snippets |
| `forensic_tools.py` | Whisper transcription (Groq/OpenAI) + local TruFor (manipulation scoring) + StreetCLIP (location prediction) + EXIF/pHash |
| `provenance_tools.py` | X GraphQL (cookie-based, `bird_x.py`) + Reddit (PRAW) + free WHOIS domain lookups |
| `reference_tools.py` | News API + Wikipedia API + Google Fact Check Tools API + Wayback Machine |

Agents declare *capabilities*, not specific tool names — `registry.py` resolves capability tags to the current implementation, so tools can be swapped without touching agent code.

**Deliberately excluded** (see [`tool-integration-spec.md`](./tool-integration-spec.md) for full reasoning):
- Paid X/Grok API scrapers (`xai_x.py`, `xquik.py`, `xurl_x.py`) — no Enterprise X API keys; `bird_x.py` is the sole X capability.
- Instagram/LinkedIn/TikTok scrapers — trigger CAPTCHAs immediately, too unstable for a short build cycle.
- Local Wikipedia FAISS index (`wiki_dump.py`) — the hosted API is lightweight enough; avoids hosting a heavy vector index.
- Legacy duplicate Reddit client (`reddit.py`) — replaced by the PRAW-based implementation.

---

## 10. Calibration

Scrutin tracks whether its *stated* confidence matches its *empirical* accuracy over time using Expected Calibration Error (ECE):

```python
@dataclass
class CalibrationBucket:
    confidence_range: tuple[float, float]
    count: int
    correct: int
    # accuracy = correct / count
    # expected_confidence = midpoint of confidence_range
    # calibration_error = |accuracy - expected_confidence|
```

10 buckets of width 0.1 across `[0, 1]`. `compute_ece()` weights each bucket's calibration error by its share of total runs. **A well-calibrated system has ECE < 0.05** — i.e., it's right ~80% of the time when it says 80%. Run `python -m app.cli stats` for a formatted report.

---

## 11. Testing with PydanticAI Test Doubles

`TestModel` and `FunctionModel` let the full orchestration loop be unit-tested without live LLM calls — a complete multi-iteration run executes in under 2 seconds.

```python
def test_loop_stops_within_budget():
    bb = Blackboard(run_id="test-001", raw_input="...", plan=Plan(tasks=[...]), budget_limit=10)
    with TestModel.patch_all():
        report = asyncio.run(run_orchestrator(bb, agent_registry={}))
    assert bb.iterations <= bb.budget_limit
    assert report is not None
```

Ground-truth regression fixtures (`tests/fixtures/ground_truth.py`) pair known claims with expected verdicts/stances — e.g. a well-sourced true historical fact, a debunked health-misinformation claim, and a "misleading" case built from real-but-non-causal observational data. These runs use live LLM calls and cost real API quota (`python -m app.cli test --fixtures ...`).

---

## Terminal trace example

```
12:04:33 | INFO     | orchestrator       | Run started: run_a1b2c3 | claim: "vaccines caused deaths"
12:04:33 | INFO     | decomposition      | Decomposed → 2 atomic claims: C1 (statistical), C2 (causal)
12:04:34 | INFO     | orchestrator       | Iteration 1: Launching evidence_agent on C1
12:04:34 | INFO     | evidence_agent     | Fast-path: Google Fact Check → 1 match (Snopes: False)
12:04:34 | INFO     | evidence_agent     | Searching: 'COVID vaccine deaths US statistics' → 8 results via serper
12:04:35 | INFO     | evidence_agent     | Stored WB1 (cdc.gov), WB2 (reuters.com), WB3 (apnews.com)
12:04:35 | INFO     | evidence_agent     | Finding: stance=contradicts, confidence=0.88
12:04:35 | INFO     | orchestrator       | Iteration 2: Launching credibility_agent on WB2 domain reuters.com
12:04:36 | INFO     | credibility_agent  | reuters.com → score=94.0, domain_age=30y, track_record=excellent
12:04:36 | INFO     | orchestrator       | Iteration 3: Launching adversarial_agent
12:04:38 | WARNING  | adversarial        | verdict_stands=False → 'All 3 sources cite CDC data; no independent replication'
12:04:38 | INFO     | orchestrator       | Adversarial critique noted. Replanning: adding evidence retry for C1
12:04:39 | INFO     | evidence_agent     | Retry: query='vaccine mortality peer reviewed studies' → 5 results
12:04:40 | INFO     | evidence_agent     | Added WB4 (nejm.org) — independent of CDC data
12:04:40 | INFO     | orchestrator       | Iteration 5: Re-running adversarial_agent
12:04:42 | INFO     | adversarial        | verdict_stands=True
12:04:42 | INFO     | orchestrator       | Stopping: score=0.90 ≥ 0.85 threshold

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT:      FALSE
SCORE:        12.0 / 100
CONFIDENCE:   0.90
ITERATIONS:   5 / 20
TIME:         8.4s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADVERSARIAL:  No material counter-argument survived after adding peer-reviewed source WB4.
SOURCES USED: CDC (WB1), Reuters (WB2), AP News (WB3), NEJM (WB4)
FACT-CHECK:   Snopes → "False" (FC1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

This trace shows the full loop in miniature: fast-path fact-check hit, independent-sourcing check, credibility scoring, an Adversarial rejection that forces a real replan (not just a re-ask), and a final stop once the deterministic-picker score clears 0.85.

---

## Reference documents

- [`README.md`](./README.md) — project overview and roadmap
- [`SETUP.md`](./SETUP.md) — local setup instructions
- [`AGENTS.md`](./AGENTS.md) — workspace rules and code standards
- [`agent-system-prompts.md`](./agent-system-prompts.md) — full system prompts for all 6 agents
- [`blackboard-schemas.md`](./blackboard-schemas.md) — all Pydantic message/state schemas
- [`database-schema.md`](./database-schema.md) — SQLite + Pinecone persistence definitions
- [`tool-integration-spec.md`](./tool-integration-spec.md) — tool wrappers, schemas, and exclusions
- [`evaluation-and-calibration-plan.md`](./evaluation-and-calibration-plan.md) — CLI, test doubles, ground truth, ECE
