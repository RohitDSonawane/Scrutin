# Scrutin — Backend

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: PydanticAI](https://img.shields.io/badge/Framework-PydanticAI-red.svg)](https://ai.pydantic.dev/)

**Scrutin** is a production-grade multi-agent misinformation verification engine. It coordinates six independent cognitive agents through a hub-and-spoke Blackboard architecture, coordinated by an LLM-Authoritative orchestration loop backed by FastAPI + SSE streaming.

---

## System Architecture

```
Raw Input (claim / URL)
        │
        ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                    orchestrator/loop.py                      │
 │  ┌──────────────────────────────────────────────────────┐   │
 │  │                   Blackboard (shared state)          │   │
 │  │  atomic_claims{}  evidence_store{}  findings[]       │   │
 │  │  plan.tasks[]     provisional_verdict  final_report  │   │
 │  └──────────────────────────────────────────────────────┘   │
 │       ▲                                                       │
 │  ┌────┴──────────────────────────────────────────────────┐   │
 │  │  Orchestrator LLM (Groq llama-3.3-70b-versatile)     │   │
 │  │  Per-iteration: DELEGATE tasks | FINALIZE report      │   │
 │  └───────────┬───────────────────────────────────────────┘   │
 │              │                                                │
 │    ┌─────────▼──────────────────────────────────────────┐    │
 │    │        Sub-Agent Execution (asyncio.gather)        │    │
 │    │                                                    │    │
 │    │  Decomposition  →  Evidence  →  Credibility        │    │
 │    │  Forensics      →  Adversarial                     │    │
 │    └────────────────────────────────────────────────────┘    │
 └─────────────────────────────────────────────────────────────┘
        │
        ▼
 VerificationReport (JSON) + SSE event stream
```

---

## Agents

| Agent | Model | Role | Tools |
|---|---|---|---|
| **Orchestrator** | `groq:llama-3.3-70b-versatile` | Decides tasks per iteration (DELEGATE / FINALIZE) | None |
| **Decomposition** | `groq:llama-3.3-70b-versatile` | Parses raw input into atomic, typed, checkable claims | None (text only) |
| **Evidence** | `groq:llama-3.3-70b-versatile` | Iterative web search & Fact Check API retrieval | `web_search_tool`, `factcheck_lookup_tool` |
| **Credibility** | `groq:llama-3.3-70b-versatile` | WHOIS domain age & reputation scoring (5-dim rubric) | `whois_lookup_tool`, `get_existing_reputation_tool` |
| **Forensics** | `groq:llama-3.3-70b-versatile` | Deepfake/pHash/transcript analysis for media claims | `transcribe_media_tool`, `analyze_image_tool` |
| **Adversarial** | `groq:llama-3.3-70b-versatile` | Red-team attack on provisional verdict (no tools by design) | None |

All models are resolved from `.env` via the `get_agent_model()` factory. Any agent can be independently pointed at a different provider by setting its `*_MODEL` env var.

---

## Orchestration Flow

1. **`run_orchestrator()`** in `orchestrator/loop.py` is the single entry point for both CLI and API.
2. A **Blackboard** is created to hold shared mutable state (claims, evidence, findings, plan).
3. The **planner** bootstraps an initial `Plan` with a `decomposition` task.
4. **Fast-path cache** — before any LLM calls, `search_similar_claims()` queries Pinecone (or local SQLite cosine search) for semantically similar past claims. Exact match (≥ 0.95 cosine) → return cached report immediately.
5. **Main loop** — while `budget_remaining()`:
   - **Step A:** Execute any pending `Plan.tasks` using `asyncio.gather()` for parallel groups.
   - **Step B:** When the plan is empty, call the Orchestrator LLM for the next decision:
     - `delegate` → add new tasks to the plan (e.g. add adversarial task, re-run evidence with tighter query)
     - `finalize` → accept `VerificationReport` from LLM, break loop
6. **Adversarial guard** — if the Orchestrator tries to finalize before an adversarial task ran, the loop forces one.
7. **Fallback report** — if the Orchestrator LLM fails or the budget exhausts, `_build_final_report()` assembles a heuristic report from Blackboard state.
8. **Persistence** — reputation updates (EDC pipeline), semantic embeddings (Pinecone + SQLite), and episodic run records are committed in `finally`.

---

## SSE Event Stream

`GET /api/verify/stream?claim=<claim_text>` opens a Server-Sent Events connection.

Each SSE message is `data: <json>\n\n` where the JSON has `{"type": <event_type>, "data": {...}}`.

| Event | When | Key Payload Fields |
|---|---|---|
| `start` | Run begins | `run_id`, `raw_input`, `input_type` |
| `plan` | After bootstrap or Orchestrator delegate | `iteration`, `tasks[]` |
| `agent_start` | Before each agent runs | `agent`, `claim_id`, `task_id`, `iteration` |
| `decomposition` | After Decomposition agent | `claims: [{claim_id, claim_text}]` |
| `finding` | After Evidence/Credibility/Forensics/Adversarial | `agent`, `claim_id`, `stance`, `confidence`, `rationale` |
| `provisional_verdict` | After each finding | `verdict` |
| `orchestrator_decision` | After Orchestrator LLM responds | `action`, `reasoning`, `tasks?` |
| `log` | Every loguru `INFO`+ log line | `timestamp`, `level`, `agent`, `message` |
| `final_report` | At run completion | `report: VerificationReport` |
| `complete` | Last event | `run_id`, `processing_time_seconds` |
| `error` | On exception | `detail` |

---

## API Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/healthz` | Health check → `{"status": "ok"}` |
| `POST` | `/api/verify` | Synchronous verification (waits for full result) |
| `GET` | `/api/verify/stream` | SSE streaming verification (`?claim=` or `?url=`) |
| `POST` | `/api/verify/stream` | SSE streaming via request body |
| `GET` | `/api/recent` | Last 5 distinct verified claims from episodic memory |
| `GET` | `/api/docs` | Swagger UI |
| `GET` | `/api/openapi.json` | OpenAPI schema |

**CORS:** `localhost:5173`, `localhost:3000`, `127.0.0.1:5173` by default. Override via `CORS_ORIGINS` env var.

---

## VerificationReport Schema

```python
class VerificationReport(BaseModel):
    run_id: str
    raw_input: str
    overall_verdict: Literal["true", "false", "misleading", "unverifiable", "inconclusive"]
    credibility_score: float          # 0–100
    confidence: float                 # 0.0–1.0
    claim_findings: list[dict]        # all agent Finding objects
    adversarial_summary: str
    evidence_used: list[EvidenceItem] # url, snippet, source_domain, relevance_score
    source_credibility_notes: str
    processing_time_seconds: float
    iterations_used: int
    budget_exhausted: bool
    ai_opinion: str | None            # synthesized AI narrative verdict explanation
```

---

## Database Schema (SQLite — `scrutin.db`)

| Table | Purpose |
|---|---|
| `episodic_runs` | Full audit trail — every run's raw Blackboard JSON + structured verdict |
| `source_reputation` | Per-domain credibility score (EDC pipeline, updated by Credibility agent) |
| `calibration_log` | Agent stated confidence vs. actual outcome (for ECE computation) |
| `claim_similarity_cache` | Claim text + embedding vector + verdict for local cosine search |

All tables use `PRAGMA journal_mode=WAL` for concurrent async safety. All async writes use `aiosqlite`. Schema is applied idempotently by `app/memory/migrations.py` at startup.

---

## Tool Registry

Tools are registered via `@register(capability)` in `tools/_register_all.py` and resolved by agents via `registry.call(capability, request, config)`.

| Capability | Function | Provider |
|---|---|---|
| `web_search` | `search_tools.web_search()` | Serper.dev (4-key pool) → DuckDuckGo keyless fallback |
| `fetch_article` | `search_tools.fetch_article()` | Jina Reader (keyless, returns Markdown) |
| `fact_check` | `reference_tools.query_factcheck_db()` | Google Fact Check Tools API |
| `whois` | `provenance_tools.verify_domain()` | `python-whois` library |
| `transcribe_media` | `forensic_tools.transcribe_media()` | Groq Whisper API |
| `analyze_image` | `forensic_tools.analyze_image()` | `imagehash` (pHash) + ELA |

**Serper key pool** (`utils/serper_pool.py`): round-robin across `SERPER_API_KEY`, `SERPER_API_KEY_2/3/4`. Exhausted keys (429 response) are marked and skipped for the session.

**Rate limiters** (`utils/rate_limiter.py`):
- Groq: 2.4s between calls (~25 RPM headroom)
- Gemini: 5.0s between calls (~12 RPM headroom)

---

## Memory Layers

| Layer | Module | Technology | Description |
|---|---|---|---|
| **Episodic** | `memory/episodic.py` | SQLite WAL | Full audit trail per run + find_similar_run() text search |
| **Semantic** | `memory/semantic.py` | Pinecone + SQLite cosine | Claim embeddings via `gemini-embedding-001` (768-dim). Fallback to local cosine if Pinecone unavailable |
| **Long-term** | `memory/longterm.py` | SQLite WAL | Domain reputation — EDC pipeline (Δ > 2 points to commit) |
| **Calibration** | `evaluation/calibration.py` | SQLite | Expected Calibration Error (ECE) computation from `calibration_log` |

---

## Installation & Running

### Prerequisites
- Python 3.11+ (tested on 3.11, 3.12, 3.14)
- `ffmpeg` (optional — for media transcription only)

### 1. Virtual environment
```powershell
cd d:\ENGR\Scrutin\backend
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure `.env`
Copy `.env.example` → `.env`. Minimum required keys:
```
GROQ_API_KEY=...
GOOGLE_API_KEY=...
GOOGLE_FACT_CHECK_API_KEY=...
SERPER_API_KEY=...
DEFAULT_MODEL=groq:llama-3.3-70b-versatile
EMBEDDING_MODEL=gemini-embedding-001
```

### 4. Run DB migrations (once)
```powershell
python -m app.memory.migrations
```

### 5. Start the API server
```powershell
python -m app.server      # → http://localhost:8000
```

### CLI usage
```powershell
# Verify a claim (full agent trace)
python -m app.cli verify --claim "Pune has the highest rate of blockchain startups in India" --trace

# Verify via article URL
python -m app.cli verify --url "https://example.com/news"

# View calibration + run stats
python -m app.cli stats
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_MODEL` | — | Fallback model for all agents |
| `ORCHESTRATOR_MODEL` | — | Orchestrator LLM |
| `DECOMPOSITION_MODEL` | — | Decomposition agent |
| `EVIDENCE_MODEL` | — | Evidence agent |
| `CREDIBILITY_MODEL` | — | Credibility agent |
| `FORENSICS_MODEL` | — | Forensics agent |
| `ADVERSARIAL_MODEL` | — | Adversarial agent |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Claim embedding model |
| `OPENROUTER_API_KEY` | — | Required for OpenRouter-hosted models (google/, gemma) |
| `GOOGLE_API_KEY` | — | Gemini + embedding access |
| `GROQ_API_KEY` | — | Groq Llama access |
| `SERPER_API_KEY[_2/_3/_4]` | — | Web search (up to 4 keys, round-robin) |
| `GOOGLE_FACT_CHECK_API_KEY` | — | Google Fact Check Tools API |
| `PINECONE_API_KEY` | — | Semantic vector store (optional) |
| `SCRUTIN_DB_PATH` | `scrutin.db` | SQLite database path |
| `CORS_ORIGINS` | `localhost:5173,...` | Comma-separated allowed origins |

---

## License

MIT — see [LICENSE](../LICENSE).
