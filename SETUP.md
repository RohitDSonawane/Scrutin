# Scrutin — Setup Guide

This guide gets Scrutin running locally, end to end: backend, frontend, database, and (optionally) the terminal CLI with no frontend at all. If you just want the project overview, see [`README.md`](./README.md); for how the pieces work, see [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## 1. Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11 or 3.12 | [python.org](https://www.python.org/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| pnpm | latest | `npm install -g pnpm` |

You'll also need API keys for the services Scrutin calls out to (see §4 below). At minimum for a first run you need **Google (Gemini)**, **Groq**, and **Serper**.

---

## 2. Clone the repo

```bash
git clone https://github.com/yourteam/scrutin.git
cd scrutin
```

---

## 3. Backend setup (Python / FastAPI)

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies (includes FastAPI + uvicorn)
pip install -r requirements.txt

# Configure secrets
cp .env.example .env
```

Open `.env` and fill in, at minimum:
```
GOOGLE_API_KEY=...
GROQ_API_KEY=...
SERPER_API_KEY=...
PINECONE_API_KEY=...
```
See §4 for the full environment variable reference.

### Run database migrations

Scrutin uses SQLite (WAL mode, mandatory) for episodic memory and source reputation, plus a single Pinecone index for claim-embedding similarity. Run migrations once before first use:

```bash
python -m app.memory.migrations
```

This is idempotent — safe to re-run any time. It creates:
- `episodic_runs` — full history of past verification runs
- `source_reputation` — long-term domain credibility scores
- `calibration_log` — stated confidence vs. actual outcome, for ECE tracking
- `claim_similarity_cache` — metadata store paired with the Pinecone vector index

Full schema detail: [`database-schema.md`](./database-schema.md).

### Start the API server

```bash
python -m app.server
```

The backend runs at **http://localhost:8000**
- Swagger UI: `http://localhost:8000/api/docs`
- Health check: `http://localhost:8000/api/healthz`

---

## 4. Frontend setup (React 19 + Vite)

```bash
cd frontend
pnpm install

cp artifacts/scrutin/.env.example artifacts/scrutin/.env.local
# .env.local already has: VITE_API_URL=http://localhost:8000

cd artifacts/scrutin
pnpm dev
```

The frontend runs at **http://localhost:5173** and talks to the backend at the URL configured in `.env.local`.

---

## 5. Environment variables reference

Add these to `backend/.env`:

```env
# Google Serper API Keys (web search & RIS) — support up to 4 keys for rotation
SERPER_API_KEY=your_primary_key_here
SERPER_API_KEY_2=key_2
SERPER_API_KEY_3=key_3
SERPER_API_KEY_4=key_4

# Google Fact Check Tools API key
GOOGLE_FACT_CHECK_API_KEY=your_google_dev_key

# Google Gemini (Orchestrator, Evidence, Forensics agents; gemini-embedding-001 for Pinecone)
GOOGLE_API_KEY=...

# Groq (Decomposition, Credibility, Adversarial agents + Whisper transcription fallback)
GROQ_API_KEY=gsk_...

# OpenAI (Whisper fallback only, if Groq Whisper is unavailable)
OPENAI_API_KEY=sk-...

# Pinecone (claim embedding similarity index)
PINECONE_API_KEY=...

# News database keys
NEWSAPI_KEY=news_key
NEWS_DATA_API_KEY=newsdata_key

# Reddit API creds (PRAW wrapper)
REDDIT_CLIENT_ID=client_id
REDDIT_CLIENT_SECRET=client_secret
REDDIT_USERNAME=username
REDDIT_USER_AGENT=hackathon_verifier_v1
```

> **Note:** `provenance_tools.py`'s X (Twitter) capability (`bird_x.py`) uses cookie-based GraphQL scraping, not a paid X API key — no `X_API_KEY` is needed for that path. See [`tool-integration-spec.md`](./tool-integration-spec.md) for what was deliberately excluded and why.

---

## 6. Running from the terminal (no frontend needed)

```bash
# Verify a text claim
python -m app.cli verify --claim "The COVID-19 vaccines caused 50,000 deaths in the US"

# Verify a URL
python -m app.cli verify --url "https://example.com/article"

# Verbose trace of every Blackboard write
python -m app.cli verify --claim "..." --trace

# Ground-truth regression suite (live LLM + ~10 Serper queries)
python -m app.cli test --fixtures tests/fixtures/ground_truth.py

# Calibration report (Expected Calibration Error)
python -m app.cli stats
```

---

## 7. Running tests

```bash
# Unit tests — no live LLM calls, uses PydanticAI's TestModel
pytest tests/ -v

# Ground-truth regression suite — live LLM calls, costs real API quota
python -m app.cli test --fixtures tests/fixtures/ground_truth.py
```

The unit test suite patches all PydanticAI agents with `TestModel.patch_all()`, so the full multi-iteration orchestration loop runs in under 2 seconds without hitting any real model provider. See [`ARCHITECTURE.md`](./ARCHITECTURE.md#testing-with-pydanticai-test-doubles) for how the test doubles are wired.

---

## 8. Quick end-to-end checklist

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure secrets
cp .env.example .env   # fill in SERPER_API_KEY, GROQ_API_KEY, GOOGLE_API_KEY, PINECONE_API_KEY

# 3. Run database migrations
python -m app.memory.migrations

# 4. Run a single live verification
python -m app.cli verify --claim "The Eiffel Tower was built in 1889" --trace

# 5. Run unit tests (no LLM calls)
pytest tests/ -v

# 6. Run the ground-truth regression suite
python -m app.cli test --fixtures tests/fixtures/ground_truth.py

# 7. Check calibration stats
python -m app.cli stats
```

If steps 1–4 succeed, the backend is fully functional even before the frontend is started — everything in §3 is independent of §4.

---

## 9. Troubleshooting

- **`database is locked` errors** — confirm `PRAGMA journal_mode=WAL` is being set on every connection (it's mandatory, see `app/memory/_db.py`); this is the #1 cause under concurrent async access.
- **Pinecone index creation fails** — free tier allows only one index. Don't try to create a second index for the `media` namespace; it's intentionally kept in SQLite for now (see [`database-schema.md`](./database-schema.md)).
- **Adversarial agent errors reference the wrong provider** — double-check `GROQ_API_KEY` is set; the Adversarial Verifier and Credibility agent are hard-pinned to Groq/Llama and will not silently fall back to Gemini.
- **Embedding dimension mismatch** — `gemini-embedding-001` outputs `dimension=768`; don't swap in an OpenAI embedding model (different dimensionality, different index).
