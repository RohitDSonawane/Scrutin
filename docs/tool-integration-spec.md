# Tool Integration Specification — Claim Verification Platform

This document details the exact tooling structure for the Claim Verification Platform MVP. It defines which files are copied from the source folder [toolcall/](file:///d:/ENGR/Scrutin/Refrences/toolcall/toolcall), what clutter is removed, and the exact Pydantic schemas for the tool wrappers.

---

## 1. Directory Structure & File Mapping

We copy only the essential files from the `toolcall/` subdirectories into our platform's `app/tools/lib/` folder. All paid X API modules, redundant scrapers, and local vector indexes are removed.

```
app/
└── tools/
    ├── registry.py             # PydanticAI tool registry and capability tags
    ├── search_tools.py         # Google Serper + Jina Reader + CrossEncoder re-ranker
    ├── forensic_tools.py       # Whisper media transcription + local TruFor & StreetCLIP
    ├── provenance_tools.py     # X (GraphQL) + Reddit (PRAW) + Free WHOIS
    ├── reference_tools.py      # News API + Wikipedia API + FactCheck + Wayback Machine
    │
    └── lib/                    # Copied from Refrences/toolcall/toolcall/ (Cleaned & Read-only)
        ├── http.py             # Core HTTP client with retries/exponential backoff
        ├── subproc.py          # Safe subprocess runner with group kill signals
        ├── health.py           # Dependency probe for ffmpeg/yt-dlp binaries
        ├── log.py              # Stderr log formatter
        │
        ├── grounding.py        # Web search dispatcher
        ├── web_search_keyless.py # DuckDuckGo free scraper fallback
        ├── web_fetch_keyless.py  # Jina Reader markdown scraper
        ├── backends.py         # Active key/capability backend resolution
        │
        ├── transcribe.py       # Whisper API (Groq/OpenAI) media transcriber
        ├── cookie_extract.py   # Browser cookies extractor
        ├── chrome_cookies.py   # Chrome cookie decryptor
        ├── safari_cookies.py   # Safari cookie binary parser
        │
        ├── bird_x.py           # X GraphQL scrape worker (uses cookies)
        ├── reddit_keyless.py   # Keyless Reddit search API (RSS, Shreddit)
        ├── reddit_enrich.py    # Reddit comment extractor
        ├── youtube_yt.py       # YouTube transcript & metadata crawler
        ├── bluesky.py          # Bluesky public AT Protocol client
        └── arxiv.py            # Academic papers index scraper
```

### ❌ Clutter Removed (Deliberately Excluded)
1. **Paid X Scrapers:** [xai_x.py](file:///d:/ENGR/Scrutin/Refrences/toolcall/toolcall/30dayss______/source_lib/xai_x.py), [xquik.py](file:///d:/ENGR/Scrutin/Refrences/toolcall/toolcall/30dayss______/source_lib/xquik.py), and [xurl_x.py](file:///d:/ENGR/Scrutin/Refrences/toolcall/toolcall/30dayss______/source_lib/xurl_x.py) (we don't have Grok or Enterprise X API keys; `bird_x.py` is our sole X capability).
2. **Flaky Social Scrapers:** `instagram.py`, `linkedin.py`, and `tiktok.py` (highly unstable for a short hackathon; they trigger captchas immediately).
3. **Local Wikipedia Vector Index:** `wiki_dump.py` (requires hosting a heavy FAISS index; online Wikipedia API is lightweight and up-to-date).
4. **Duplicate Reddit APIs:** [reddit.py](file:///d:/ENGR/Scrutin/Refrences/toolcall/toolcall/30dayss______/source_lib/reddit.py) (replaced entirely by `reddit_service.py` PRAW implementation from TruthLens).

---

## 2. Tool Wrappers & Pydantic Schemas

Every tool exposed to our PydanticAI agents must accept a Pydantic `BaseModel` query request and return a structured Pydantic response.

---

### 2.1 Search & Re-Ranking: `search_tools.py`
This tool combines Serper.dev web search with the Cross-Encoder re-ranking logic from [base.py (LibrAI)](file:///d:/ENGR/Scrutin/Refrences/toolcall/toolcall/libr_ai____/retriever/base.py) to return only the most relevant page chunks.

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class SearchRequest(BaseModel):
    query: str = Field(description="The factual search query to verify.")
    date_from: Optional[str] = Field(None, description="Start date filter in YYYY-MM-DD format.")
    date_to: Optional[str] = Field(None, description="End date filter in YYYY-MM-DD format.")

class SearchSnippet(BaseModel):
    title: str
    url: str
    snippet: str = Field(description="Relevance-ranked text passage from the web page.")
    relevance_score: float = Field(description="Cross-Encoder score (0.0 to 1.0).")

class SearchResponse(BaseModel):
    success: bool
    results: List[SearchSnippet]
    source_backend: str  # "serper" | "duckduckgo"
```

* **Execution Logic:**
  1. Call `grounding.web_search(query, date_range=(date_from, date_to))` using the Serper key.
  2. Scrape the body content of the top 3 URLs using `web_fetch_keyless.fetch_markdown()`.
  3. Chunk the markdown content using a sliding window.
  4. Rank all chunks against the query using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
  5. Return the top 5 highest-scoring snippets.

---

### 2.2 Audio/Video Transcription: `forensic_tools.py`
Exposes the Whisper media transcriber for audio files and video links (YouTube, TikTok).

```python
class TranscribeRequest(BaseModel):
    media_url_or_path: str = Field(description="Direct URL to YouTube/TikTok or local media path.")

class TranscribeResponse(BaseModel):
    success: bool
    transcript: str
    provider: str  # "groq" | "openai"
    error_message: Optional[str] = None
```

* **Execution Logic:** Calls `transcribe.transcribe_media()` using Groq Whisper (or OpenAI Whisper as fallback).

---

### 2.3 Image Tampering & Metadata: `forensic_tools.py`
Integrates local image forensics and spatial metadata.

```python
class ImageAnalysisRequest(BaseModel):
    image_path: str = Field(description="Local file path to the claim image.")

class ImageAnalysisResponse(BaseModel):
    is_manipulated: bool
    manipulation_score: float = Field(description="TruFor forgery score (0.0 to 1.0).")
    predicted_country: Optional[str] = Field(None, description="StreetCLIP country location prediction.")
    gps_coordinates: Optional[str] = Field(None, description="EXIF metadata coordinates.")
    perceptual_hash: Optional[str] = Field(None, description="Image perceptual hash (pHash) for fast-path duplicate verification.")
```

---

### 2.4 Social Media & Domain Provenance: `provenance_tools.py`
Extracts credentials to search X (Twitter), Reddit, and checks domain registration details.

```python
class DomainVerifyRequest(BaseModel):
    domain: str = Field(description="The domain name to verify (e.g. bbc-news-update.com).")

class DomainVerifyResponse(BaseModel):
    domain: str
    registered_at: str
    registrar: str
    is_recent: bool = Field(description="True if domain was registered within the last 180 days.")
    domain_age_days: int = Field(description="Number of days since domain registration.")
```

* **Execution Logic:** Uses the Python library `python-whois` to perform free domain lookups.

---

### 2.5 Verification & Reference Databases: `reference_tools.py`
Queries historical archives, news search engines, and pre-existing fact-check indexes.

```python
class FactCheckDbRequest(BaseModel):
    query: str = Field(description="Claim keywords to look up in the fact-check index.")

class FactCheckItem(BaseModel):
    claim: str
    verdict: str  # "True" | "False" | "Misleading"
    review_publisher: str  # e.g., "Snopes"
    review_url: str

class FactCheckDbResponse(BaseModel):
    matches_found: int
    verdicts: List[FactCheckItem]
```

* **Execution Logic:** Calls the Google Fact Check Tools API (`https://factchecktools.googleapis.com/v1alpha1/claims:search`) with a developer key to retrieve Snopes/PolitiFact matches.

---

## 3. Central Tool Registry Configuration (`registry.py` + `_register_all.py`)

Tools are **registered by capability tag** in `tools/_register_all.py` and dispatched by `registry.call()`. Agents invoke tools via `asyncio.to_thread(registry_call, capability, request, config)` inside their `@agent.tool` decorated methods:

```python
# tools/_register_all.py — imported ONCE at startup (app lifespan)
from app.tools.registry import register
from app.tools.search_tools import web_search, fetch_article
from app.tools.reference_tools import query_factcheck_db
from app.tools.provenance_tools import verify_domain
from app.tools.forensic_tools import transcribe_media, analyze_image

@register("web_search", description="Serper.dev or DuckDuckGo fallback")
def _web_search(request, config): return web_search(request, config)

@register("fact_check", description="Google Fact Check Tools API")
def _fact_check(request, config): return query_factcheck_db(request, config)

@register("whois", description="WHOIS domain lookup", requires_config=False)
def _whois(request, config=None): return verify_domain(request)

@register("transcribe_media", description="Groq Whisper transcription")
def _transcribe(request, config): return transcribe_media(request, config)

@register("analyze_image", description="pHash/ELA image forensics", requires_config=False)
def _analyze(request, config=None): return analyze_image(request)
```

Inside agents, tools are registered with the `@agent.tool` decorator:

```python
# agents/evidence_agent.py
@evidence_agent.tool
async def web_search_tool(ctx, query: str, date_from: str = "", date_to: str = "") -> dict:
    from app.tools.search_tools import SearchRequest
    from app.tools.registry import call as registry_call
    req = SearchRequest(query=query, date_from=date_from or None, date_to=date_to or None)
    resp = await asyncio.to_thread(registry_call, "web_search", req, ctx.deps.config)
    # Store each result on the Blackboard by ID — never pass raw content to LLM
    for item in resp.results:
        eid = ctx.deps.blackboard.store_evidence("WB", item.model_dump())
    return {"results": [...], "backend": resp.backend_used, "count": len(resp.results)}
```

---

## 4. Environment Variables Reference (`.env`)

Add the following configuration lines to the project's root `.env` file:

```env
# Model configuration (PydanticAI model strings)
DEFAULT_MODEL=groq:llama-3.3-70b-versatile      # Fallback for all agents
ORCHESTRATOR_MODEL=groq:llama-3.3-70b-versatile  # Override per-agent
DECOMPOSITION_MODEL=groq:llama-3.3-70b-versatile
EVIDENCE_MODEL=groq:llama-3.3-70b-versatile
CREDIBILITY_MODEL=groq:llama-3.3-70b-versatile
FORENSICS_MODEL=groq:llama-3.3-70b-versatile
ADVERSARIAL_MODEL=groq:llama-3.3-70b-versatile
EMBEDDING_MODEL=gemini-embedding-001             # 768-dim, Google genai SDK

# LLM Provider API Keys
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...                           # Gemini + embedding access
OPENROUTER_API_KEY=sk-or-...                     # Optional: for OpenRouter-hosted models

# Google Serper API Keys (Web Search — up to 4 keys, round-robin rotation)
SERPER_API_KEY=your_primary_key_here
SERPER_API_KEY_2=key_2
SERPER_API_KEY_3=key_3
SERPER_API_KEY_4=key_4

# Google Fact Check Tools API Key
GOOGLE_FACT_CHECK_API_KEY=your_google_dev_key

# Vector Store (optional — falls back to local cosine if not set)
PINECONE_API_KEY=pc-...

# Database
SCRUTIN_DB_PATH=scrutin.db                       # Default: current directory

# API Server
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
PORT=8000
```
