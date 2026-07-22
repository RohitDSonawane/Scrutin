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
    registered_at: str
    registrar: str
    is_recent: bool = Field(description="True if domain was registered within the last 180 days.")
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

## 3. Central Tool Registry Configuration (`registry.py`)

Using **PydanticAI**, tools are decorated and registered inside `app/tools/registry.py`. Each agent declares which tools it can access:

```python
from pydantic_ai import Agent
from app.tools.search_tools import search_web_tool
from app.tools.forensic_tools import transcribe_media_tool, analyze_image_tool
from app.tools.provenance_tools import verify_domain_tool
from app.tools.reference_tools import query_factcheck_db_tool

# Setup orchestrator agent (delegates queries)
orchestrator = Agent('google-gla:gemini-2.5-flash')

# Setup Evidence Agent
evidence_agent = Agent('google-gla:gemini-2.5-flash')
evidence_agent.tool(search_web_tool)
evidence_agent.tool(query_factcheck_db_tool)

# Setup Forensics Agent
forensics_agent = Agent('google-gla:gemini-2.5-flash')
forensics_agent.tool(transcribe_media_tool)
forensics_agent.tool(analyze_image_tool)
```

---

## 4. Environment Variables Reference (`.env`)

Add the following configuration lines to the project's root `.env` file to support the integrated stack:

```env
# Google Serper API Keys (For Web Search & RIS)
SERPER_API_KEY=your_primary_key_here
SERPER_API_KEY_2=key_2
SERPER_API_KEY_3=key_3
SERPER_API_KEY_4=key_4

# Google Fact Check Tools API Key
GOOGLE_FACT_CHECK_API_KEY=your_google_dev_key

# Transcription APIs
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...

# News Database Keys
NEWSAPI_KEY=news_key
NEWS_DATA_API_KEY=newsdata_key

# Reddit API Creds (PRAW Wrapper)
REDDIT_CLIENT_ID=client_id
REDDIT_CLIENT_SECRET=client_secret
REDDIT_USERNAME=username
REDDIT_USER_AGENT=hackathon_verifier_v1
```
