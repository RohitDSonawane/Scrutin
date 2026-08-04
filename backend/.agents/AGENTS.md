# Scrutin — Workspace Rules & Code Standards

> These rules apply to all files under `d:\ENGR\Scrutin\backend\`.
> Last updated: 2026-08-04 — reflects post-refactor architecture.

---

## 1. Orchestration & Control Flow

- **Primary orchestration loop lives in `orchestrator/loop.py`** as a plain Python `while` loop. `run_orchestrator()` is the single entry point used by both CLI (`app/cli.py`) and API (`app/api.py`). Never call agent nodes directly from outside this function.
- **`graph/engine.py` and `graph/nodes.py`** provide a secondary LangGraph-style state machine (`ScrutinGraphState`) for offline testing and graph-based execution. The primary SSE-backed API path always goes through `orchestrator/loop.py`.
- **The Orchestrator LLM decides, Python executes.** The Orchestrator LLM emits a typed `OrchestratorDecision` (structured output via PydanticAI). Python reads `decision.action` and routes accordingly — no freeform text parsing.
- **Self-critique is mandatory before any finalize.** The Orchestrator is prohibited from emitting `action="finalize"` before an Adversarial task has run. The loop enforces this with an explicit guard in `_execute_single_task`.
- **Deterministic-picker pattern for scoring.** The `EvidenceEvaluation` model uses boolean fields (`sources_are_independent`, `adversarial_critique_addressed`, etc.). `compute_stopping_score()` in `protocols/messages.py` calculates the deciding float from those booleans. Never ask the LLM for a raw score directly.

## 2. Agent Communication — Hub-and-Spoke Only

- **Sub-agents never call each other.** All cross-agent requests are placed as typed `AgentRequest` objects on the `Blackboard`. The Orchestrator processes them on the next iteration.
- **The Blackboard (`protocols/blackboard.py`) is the single shared mutable state.** Its `findings` list is append-only — `append_finding()` never overwrites. Its `evidence_store` is keyed by short IDs (`WB1`, `FC2`, etc.).
- **Context externalization is mandatory.** Heavy content (HTML, transcripts) is stored in `blackboard.evidence_store` keyed by ID. Agents pass IDs in `Finding.evidence_ids` — never raw content in messages.
- **Parallel execution** uses `asyncio.gather()` over tasks with the same `parallel_group` int. Tasks with no `parallel_group` run sequentially one at a time.

## 3. Structured Output — No Raw Dicts

- All agent outputs are validated Pydantic `BaseModel` subclasses:
  - `decomposition_agent` → `DecompositionOutput`
  - `evidence_agent`, `credibility_agent`, `forensics_agent` → `Finding`
  - `adversarial_agent` → `AdversarialCritique`
  - `orchestrator_agent` → `OrchestratorDecision`
- Parsing LLM text with `regex` or `.split()` is banned. Use PydanticAI structured output.
- Tool return types are Pydantic models. `registry.call()` invokes them — no raw dict returns from tools.

## 4. Memory Tier Boundaries

- **Working memory:** `Blackboard` (in-process). Never promoted automatically.
- **Episodic memory:** SQLite (`aiosqlite`). Append-only. `PRAGMA journal_mode=WAL`. Used for exact/similar claim recall and the run audit trail. `Blackboard.flush_to_sqlite()` writes raw JSON. `episodic.record_run()` writes structured fields — only called on clean completion.
- **Semantic memory:** Pinecone + local SQLite cosine fallback. Stores `gemini-embedding-001` (768-dim) embeddings via `memory/semantic.py`. Only upserted on non-fallback runs. Score ≥ 0.92 for fast-path cache hit.
- **Long-term / reputation:** SQLite `source_reputation` table. Uses Extract-Deduplicate-Commit (EDC) pipeline in `memory/longterm.py`. Only commits if domain score delta > 2 points.
- **Calibration:** `calibration_log` table. Expected Calibration Error (ECE) computed by `evaluation/calibration.py`. Populated by agent test harness runs.

## 5. Tool Contracts

- Tools are **stateless pure functions** registered in `tools/_register_all.py` via `@register(capability)`.
- Tools accept typed Pydantic request objects and return typed Pydantic response objects.
- A tool **never makes a judgment call**. If a function needs LLM interpretation, it belongs in an agent, not in `tools/`.
- Agents call tools by capability tag through `registry.call()` or inline via `asyncio.to_thread()`. They never import tool functions directly.
- Registered capabilities: `web_search`, `fetch_article`, `fact_check`, `whois`, `transcribe_media`, `analyze_image`.
- The `SerperKeyPool` (`utils/serper_pool.py`) manages up to 4 Serper API keys with round-robin rotation and quota exhaustion detection. Tools access it via `get_pool()`.

## 6. Adversarial Agent Independence

- The Adversarial Verifier receives **only**: (a) raw compiled evidence IDs + snippets from `bb.evidence_store`, (b) the `bb.provisional_verdict` string.
- It does **not** receive: the Evidence agent's reasoning trace, the Orchestrator's planning notes, or any intermediate thought.
- Its input is built exclusively by `_build_adversarial_prompt()` in `loop.py`.
- It has **no tools** by design (see `adversarial_agent.py` comment). Any targeted follow-up search goes through the Orchestrator as an `AgentRequest`.
- It outputs `AdversarialCritique` (not `Finding`). The loop converts it to a `Finding` with `stance="supports"` (verdict stands) or `stance="mixed"` (verdict challenged).

## 7. SSE Event Stream Protocol

- `_stream_verification()` in `api.py` manages a `asyncio.Queue` + loguru sink that receives events from `run_orchestrator()` via the `on_event` callback.
- Every event is `data: <json>\n\n` with `{"type": <event_type>, "data": {...}}`.
- Event types in emission order: `start` → `plan` → `agent_start` → `decomposition` / `finding` / `provisional_verdict` / `orchestrator_decision` → `log` (continuous) → `final_report` → `complete`.
- The `log` event sinks every `INFO`+ loguru message — it runs concurrently. Do not depend on `log` events for control flow.
- The queue sentinel is `None` (signals stream end to the async generator).

## 8. Python Style

- Python 3.11+. Use `from __future__ import annotations` in every module.
- Use `asyncio.gather()` for independent parallel agent/tool calls. Never `await` sequentially if there is no data dependency.
- All async database calls use `aiosqlite`. Do not use synchronous `sqlite3` in async code paths.
- Rate limiting is done via `utils/rate_limiter.py` (`groq_acquire()`, `gemini_acquire()`). Call the appropriate limiter before any LLM invocation. The limiter is a no-op in test environments (`PYTEST_CURRENT_TEST`).
- Model resolution: always via `get_agent_model(env_var_name)` in `agents/base.py`. Never hardcode model strings.
- `from __future__ import annotations` + `TYPE_CHECKING` guard for circular-import-prone imports (e.g., Blackboard in agent deps).

## 9. Ponytail Discipline & Code Minimization

- **The Ponytail Ladder (before adding code):**
  1. Does this feature need to exist at all? (YAGNI)
  2. Is it already in this codebase? Check `utils/`, `tools/`, `protocols/` first.
  3. Does the Python stdlib cover it? Prefer `itertools`, `asyncio`, `sqlite3` over new packages.
  4. Can it be written in fewer lines without sacrificing readability or safety?
- **Root-cause fixes only.** Fix bugs at their single origin. Never add duplicate guards across callers.
- **No unneeded abstractions.** Single-implementation interfaces and premature factories are banned.

## 10. Known Issues & Active Limitations (2026-08-04)

- `graph/engine.py` does not call `run_orchestrator()` — it runs a separate state machine. These two paths are not yet unified.
- The `migrations.py` schema for `claim_similarity_cache` references `episodic_runs(run_id)` as a FK but new runs are not always committed before semantic upserts — this can cause FK violations on first run. Mitigation: `INSERT OR REPLACE` with deferred FK enforcement.
- `VerificationReport.ai_opinion` is synthesized by `_synthesize_ai_opinion()` in `graph/nodes.py` (graph path) and by `_build_final_report()` in `orchestrator/loop.py` (fallback). The LLM-authoritative `OrchestratorDecision.finalize.report.ai_opinion` is trusted if present.
- Groq rate limits (429) on `llama-3.3-70b-versatile` at free tier will cause agent failures. The loop falls back to heuristic report assembly but does not retry with a different provider automatically.
