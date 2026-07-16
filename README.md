# Scrutin — Multi-Agent Misinformation Verification

> A production-grade, hackathon-optimized fact-checking platform.  
> 6 independent cognitive agents. Hub-and-spoke orchestration. Terminal-first.

## Architecture

```
Input → Claim Decomposition → Evidence & Corroboration ↘
                           → Source Credibility        → Adversarial Verifier → Verdict
                           → Forensics (if media)     ↗
```

All agents coordinate through a shared Blackboard. The Orchestrator runs a plain `while` loop — no LangGraph, no graph DSL.

## Agents & Models

| Agent | Model | Role |
|---|---|---|
| Orchestrator | Gemini 2.5 Flash | Global plan + synthesis |
| Claim Decomposition | Groq Llama 3.1 8B | Atomic claim parsing |
| Evidence & Corroboration | Gemini 2.5 Flash | Iterative web retrieval |
| Source Credibility | Groq Llama 3.3 70B | Domain trust scoring |
| Multimodal Forensics | Gemini 2.5 Flash | Media authenticity |
| Adversarial Verifier | Groq Llama 3.3 70B | Red-team critique |

## Quick Start (5 Commands)

```bash
# 1. Clone and install
git clone https://github.com/your-org/scrutin
cd scrutin
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Edit .env — minimum: GROQ_API_KEY + GOOGLE_API_KEY + SERPER_API_KEY

# 3. Initialize database
python -m app.memory.migrations

# 4. Verify a claim
python -m app.cli verify --claim "The Eiffel Tower was built in 1889" --trace

# 5. Run regression tests
python -m app.cli test
```

## Tool Stack (Zero-Cost MVP)

| Tool | Provider | Cost |
|---|---|---|
| Web Search | Serper.dev (4 keys × 2500 queries) | Free tier |
| Fact Check DB | Google Fact Check Tools API | Free |
| Transcription | Groq Whisper large-v3 | Free tier |
| Domain Lookup | python-whois | Free |
| Vector Memory | Pinecone (1 free index) | Free tier |
| Embeddings | Google gemini-embedding-001 | Free tier |

## Known Limitations

**MVP scope decisions — not bugs:**

1. **Image/Video forensics are stubs in Phase 5** — `analyze_image_tool` returns placeholder data. Replace with a real TruFor or deepfake classifier service before demo. The Forensics agent's reasoning loop is fully wired; only the tool implementation needs upgrading.
2. **No Wayback Machine integration** — `provenance_tools.py` does WHOIS only. Archive.org snapshot retrieval was descoped for hackathon time constraints.
3. **Windows: Chrome/Edge cookie extraction is not supported** — `cookie_extract.py` uses DPAPI decryption for Windows Chrome cookies, which is not implemented. Only Firefox cookies work on Windows. This affects the X/Twitter scraper (`bird_x.py`). X scraping works if you manually set `AUTH_TOKEN` and `CT0` env vars.
4. **Single-process only** — No Celery/arq task queue. Running 10+ concurrent verifications will saturate Groq's free-tier RPM limit. Scale-out path: see `architecture.md §9`.
5. **Episodic fast-path uses text search, not vectors, in Phase 7–8** — Pinecone vector similarity search is wired in Phase 8 but requires `PINECONE_API_KEY`. Without it, similar-claim recall falls back to SQLite LIKE search (lower recall).
6. **No X/Twitter scraping by default** — `bird_x.py` requires X browser session cookies and Node.js on PATH. Set `AUTH_TOKEN`+`CT0` env vars to enable.
