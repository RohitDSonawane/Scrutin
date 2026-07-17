from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from app.tools.search_tools import (
    web_search, fetch_article, rerank_snippets,
    SearchRequest, ArticleFetchRequest,
)
from app.tools.reference_tools import query_factcheck_db, FactCheckRequest


# ── web_search tests ──────────────────────────────────────────────────────────

def test_web_search_returns_structured_results():
    mock_items = [{
        "id": "WS1", "title": "Test Title", "url": "https://example.com",
        "source_domain": "example.com", "snippet": "test snippet",
        "date": "2024-01-01", "relevance": 0.8,
    }]
    mock_artifact = {"label": "serper", "resultCount": 1}

    with patch("app.tools.search_tools.grounding.web_search", return_value=(mock_items, mock_artifact)):
        response = web_search(SearchRequest(query="test claim"), config={"SERPER_API_KEY": "fake"})

    assert response.backend_used == "serper"
    assert len(response.results) == 1
    assert response.results[0].url == "https://example.com"
    assert response.results[0].relevance == 0.8


def test_web_search_never_raises_on_failure():
    with patch("app.tools.search_tools.grounding.web_search", side_effect=Exception("network error")):
        response = web_search(SearchRequest(query="test"), config={})
    assert response.results == []
    assert response.backend_used == "failed"


def test_web_search_respects_count_limit():
    mock_items = [{"id": f"WS{i}", "title": "t", "url": f"https://{i}.com",
                   "source_domain": f"{i}.com", "snippet": "s", "relevance": 0.5}
                  for i in range(20)]
    mock_artifact = {"label": "serper", "resultCount": 20}

    with patch("app.tools.search_tools.grounding.web_search", return_value=(mock_items, mock_artifact)):
        response = web_search(SearchRequest(query="test", count=5), config={})

    assert len(response.results) == 5


# ── fetch_article tests ───────────────────────────────────────────────────────

def test_fetch_article_success():
    mock_result = MagicMock()
    mock_result.ok = True
    mock_result.markdown = "# Article\n\nContent here."
    mock_result.cached_snapshot = False

    with patch("app.tools.search_tools.web_fetch_keyless.fetch_markdown", return_value=mock_result):
        response = fetch_article(ArticleFetchRequest(url="https://example.com"))

    assert response.ok is True
    assert "Content here" in response.markdown


def test_fetch_article_returns_empty_on_failure():
    mock_result = MagicMock()
    mock_result.ok = False
    mock_result.reason = "fetch-failed"

    with patch("app.tools.search_tools.web_fetch_keyless.fetch_markdown", return_value=mock_result):
        response = fetch_article(ArticleFetchRequest(url="https://bad-url.com"))

    assert response.ok is False
    assert response.markdown == ""


# ── query_factcheck_db tests ──────────────────────────────────────────────────

def test_factcheck_returns_empty_without_api_key():
    response = query_factcheck_db(FactCheckRequest(query="test"), config={})
    assert response.matches_found == 0
    assert response.verdicts == []


def test_factcheck_parses_api_response():
    mock_response = {
        "claims": [{
            "text": "The vaccine causes autism",
            "claimant": "unknown",
            "claimReview": [{
                "textualRating": "False",
                "publisher": {"name": "Snopes"},
                "url": "https://snopes.com/fact-check/vaccine-autism",
                "reviewDate": "2024-01-01T00:00:00Z",
            }]
        }]
    }

    with patch("app.tools.reference_tools.http.get", return_value=mock_response):
        response = query_factcheck_db(
            FactCheckRequest(query="vaccine autism"),
            config={"GOOGLE_FACT_CHECK_API_KEY": "fake_key"}
        )

    assert response.matches_found == 1
    assert response.verdicts[0].verdict == "False"
    assert response.verdicts[0].review_publisher == "Snopes"


def test_factcheck_never_raises_on_http_error():
    with patch("app.tools.reference_tools.http.get", side_effect=Exception("timeout")):
        response = query_factcheck_db(
            FactCheckRequest(query="test"),
            config={"GOOGLE_FACT_CHECK_API_KEY": "fake"}
        )
    assert response.matches_found == 0


# ── rerank_snippets tests (Gemini Embeddings cosine similarity) ───────────────

def test_rerank_snippets_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    
    mock_embedding0 = MagicMock()
    mock_embedding0.values = [1.0, 0.0, 0.0]
    mock_embedding1 = MagicMock()
    mock_embedding1.values = [0.9, 0.1, 0.0]
    mock_embedding2 = MagicMock()
    mock_embedding2.values = [0.1, 0.9, 0.0]
    
    mock_response.embeddings = [mock_embedding0, mock_embedding1, mock_embedding2]
    mock_client.models.embed_content.return_value = mock_response

    with patch("app.tools.search_tools.genai.Client", return_value=mock_client):
        ranked = rerank_snippets(
            query="test",
            snippets=["close snippet", "far snippet"],
            api_key="fake_key",
            top_k=2
        )
        assert len(ranked) == 2
        # Index 0 should rank higher than Index 1 (closer cosine similarity)
        assert ranked[0][0] == 0
        assert ranked[1][0] == 1


def test_rerank_snippets_fallback_without_key():
    ranked = rerank_snippets(query="test", snippets=["a", "b"], api_key="", top_k=2)
    assert len(ranked) == 2
    assert ranked[0][0] == 0
