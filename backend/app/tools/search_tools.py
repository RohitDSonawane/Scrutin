from __future__ import annotations
import math
from typing import Optional
from pydantic import BaseModel, Field
import os
from google import genai
from app.tools.lib import grounding, web_fetch_keyless


# ── Request / Response schemas ─────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(description="The factual claim or search query to run")
    date_from: Optional[str] = None   # YYYY-MM-DD
    date_to: Optional[str] = None     # YYYY-MM-DD
    count: int = 10
    backend: str = "auto"             # "auto" | "serper" | "keyless"


class SearchResultItem(BaseModel):
    source_id: str          # e.g. "WB1" — set by caller after store_evidence()
    title: str
    url: str
    source_domain: str
    snippet: str
    date: Optional[str] = None
    relevance: float        # 0.0 – 1.0, from grounding.py


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    backend_used: str
    total_found: int
    query_used: str


class ArticleFetchRequest(BaseModel):
    url: str


class ArticleFetchResponse(BaseModel):
    ok: bool
    markdown: str = ""
    cached_snapshot: bool = False
    reason: str = ""        # failure reason if ok=False


# ── Tool functions ─────────────────────────────────────────────────────────────

def web_search(request: SearchRequest, config: dict) -> SearchResponse:
    """
    Web search dispatcher. Uses Serper (paid) first with key rotation, falls back to keyless DDG.
    NEVER raises — returns empty results with backend_used='failed' on total failure.
    """
    date_range = (request.date_from, request.date_to) if request.date_from else None

    from app.utils.serper_pool import get_pool
    pool = get_pool()
    key = pool.next_key()

    if key:
        config_with_key = {**config, "SERPER_API_KEY": key}
    else:
        # Force keyless DuckDuckGo
        config_with_key = {k: v for k, v in config.items() if "SERPER" not in k}

    try:
        items, artifact = grounding.web_search(
            query=request.query,
            date_range=date_range,
            config=config_with_key,
            backend=request.backend,
        )
    except Exception as e:
        err_str = str(e).lower()
        if key and ("429" in err_str or "quota" in err_str or "exhausted" in err_str or "limit" in err_str):
            pool.mark_exhausted(key)
            # Retry once with next key
            fallback_key = pool.next_key()
            if fallback_key:
                config_with_key["SERPER_API_KEY"] = fallback_key
                try:
                    items, artifact = grounding.web_search(
                        query=request.query,
                        date_range=date_range,
                        config=config_with_key,
                        backend=request.backend,
                    )
                except Exception:
                    items, artifact = [], {"label": "failed", "resultCount": 0}
            else:
                try:
                    config_keyless = {k: v for k, v in config.items() if "SERPER" not in k}
                    items, artifact = grounding.web_search(
                        query=request.query,
                        date_range=date_range,
                        config=config_keyless,
                        backend="keyless",
                    )
                except Exception:
                    items, artifact = [], {"label": "keyless_fallback", "resultCount": 0}
        else:
            items, artifact = [], {"label": "failed", "resultCount": 0}

    results = [
        SearchResultItem(
            source_id="",          # Caller assigns this after store_evidence()
            title=item.get("title", ""),
            url=item.get("url", ""),
            source_domain=item.get("source_domain", ""),
            snippet=item.get("snippet", ""),
            date=item.get("date"),
            relevance=float(item.get("relevance", 0.0)),
        )
        for item in items[: request.count]
    ]

    return SearchResponse(
        results=results,
        backend_used=artifact.get("label", "unknown"),
        total_found=artifact.get("resultCount", len(results)),
        query_used=request.query,
    )


def fetch_article(request: ArticleFetchRequest) -> ArticleFetchResponse:
    """
    Fetch a URL and return clean Markdown via Jina Reader.
    Free, no API key. Never raises.
    """
    result = web_fetch_keyless.fetch_markdown(request.url)
    return ArticleFetchResponse(
        ok=result.ok,
        markdown=result.markdown if result.ok else "",
        cached_snapshot=getattr(result, "cached_snapshot", False),
        reason=getattr(result, "reason", "") if not result.ok else "",
    )


# ── Online Embedding Re-Ranking (Gemini API) ──────────────────────────────────

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)


def rerank_snippets(query: str, snippets: list[str], api_key: str, top_k: int = 5) -> list[tuple[int, float]]:
    """
    Re-rank a list of text snippets against a query using Gemini online embeddings.
    Returns list of (original_index, score) tuples sorted by score descending.
    """
    if not api_key or not snippets:
        return [(i, 0.5) for i in range(len(snippets))][:top_k]

    try:
        client = genai.Client(api_key=api_key)
        # Batch embed the query + all snippets to minimize API roundtrips
        contents = [query] + snippets
        response = client.models.embed_content(
            model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
            contents=contents,
        )
        embeddings = [e.values for e in response.embeddings]
        query_emb = embeddings[0]
        snippet_embs = embeddings[1:]

        scored = []
        for idx, s_emb in enumerate(snippet_embs):
            score = cosine_similarity(query_emb, s_emb)
            scored.append((idx, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    except Exception:
        # Graceful fallback on any API errors
        return [(i, 0.5) for i in range(len(snippets))][:top_k]
