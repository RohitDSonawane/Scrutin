# Scrutin — Workspace Rules & Code Standards

> These rules apply to all files under `d:\ENGR\Scrutin\`.
> They are derived from studying the open-source reference repositories listed in [refrences.md](file:///d:/ENGR/Scrutin/Refrences/refrences.md).

---

## 1. Orchestration & Control Flow

- **No LangGraph or graph-DSL imports.** The orchestration loop lives in `orchestrator/loop.py` as a plain `while` loop. LangGraph patterns from `FareedKhan-dev/all-agentic-architectures` are studied for design guidance only — their runtime is never imported.
- **Self-critique is a required step before any final output.** Inspired by the Reflexion pattern (`arxiv:2303.11366`): every agent run must have an evaluate step. The evaluator commits to structured booleans (`addresses_constraints: bool`, `is_natural_language: bool`) — Python composes the pass/fail signal, NOT the LLM freeform score.
- **Deterministic-picker pattern is mandatory for any scoring surface.** The LLM commits to independent categorical features (booleans, enums). Python computes the deciding signal. Never ask the LLM to output a raw confidence float as a judgment — it produces a flat-band.

## 2. Agent Communication — Hub-and-Spoke Only

- Sub-agents NEVER call each other. All cross-agent requests are placed as typed `AgentRequest` objects on the `Blackboard`. The Orchestrator's next loop iteration processes them.
- The Blackboard accumulates findings with `list.append()` semantics (like `Annotated[list, operator.add]` from the real blackboard source). No finding is ever overwritten — only appended.
- Context externalization: heavy data (scraped HTML, transcripts) is stored on the Blackboard keyed by a short ID (e.g., `"WB1"`, `"TR3"`). Agents pass only IDs in their messages, never raw content.

## 3. Structured Output — No Raw Dicts

- All agent outputs are validated Pydantic `BaseModel` subclasses. A `Finding` with loose field types is a bug.
- Parsing LLM text with `regex` or `.split()` is banned. Use PydanticAI structured output or `model_validate_json()`.
- The FCAgent `web_search.py` pattern (parsing LLM search result summary into a `SearchResult(BaseModel)` with `list[Item]` typed fields) is the canonical approach for all tool post-processing.

## 4. Memory Tier Boundaries

- **Working memory:** in-process Python dict. Never promoted automatically — the Orchestrator explicitly calls `episodic.record_run()` at completion.
- **Episodic memory:** SQLite (`aiosqlite`). Append-only. Enable `PRAGMA journal_mode=WAL`. Used for recall ("have we seen this claim before?"), not as ground truth.
- **Semantic memory:** Pinecone (free tier). Stores claim embeddings (`gemini-embedding-001`) and perceptual hashes (`imagehash`) in separate namespaces. Never used as a verdict substitute.
- **Long-term / reputation:** SQLite. Source profiles use the Extract-Deduplicate-Commit (EDC) pipeline: read existing profile → compute delta → write only if score changes by >2 points.

## 5. Tool Contracts

- Tools are stateless pure functions. They receive typed Pydantic request objects and return typed Pydantic response objects.
- A tool NEVER makes a judgment call. If a function needs an LLM to interpret its own output, it belongs in an agent reasoning step, not in `tools/`.
- Tools declare their capability tag in `registry.py`. Agents declare needed capabilities — not specific tool names. The registry resolves to the current implementation.

## 6. Adversarial Agent Independence

- The Adversarial Verifier MUST NOT receive the Evidence Agent's reasoning traces, intermediate search thoughts, or planning notes in its context.
- It receives ONLY: (a) the raw compiled evidence items from the Blackboard, and (b) the Orchestrator's provisional verdict string.
- It runs on a DIFFERENT LLM provider than the Evidence Agent (Groq Llama vs. Gemini). This is a hard constraint to avoid shared training biases. Do not merge them onto the same provider to save keys.

## 7. Python Style

- Python 3.11+. Use `from __future__ import annotations` in every module.
- Use `asyncio.gather()` for independent parallel tool/agent calls. Never `await` them sequentially if they have no data dependency.
- All async database calls use `aiosqlite`. Do not use synchronous `sqlite3` in async code paths.
- `aiolimiter` is used for Groq RPM rate limiting. Import and wrap every Groq agent call.
