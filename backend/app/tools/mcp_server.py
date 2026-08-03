"""
Model Context Protocol (MCP) Tool Server Specifications
======================================================
Standardizes Scrutin tools using the Linux Foundation Model Context Protocol (MCP) specification.
Exposes JSON-RPC tool schemas, dynamic tool discovery, and schema-validated invocation handlers.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# ── MCP Tool Manifest Schemas ──────────────────────────────────────────────────

class MCPToolSchema(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(..., alias="inputSchema")

    model_config = {"populate_by_name": True}


class MCPToolResponse(BaseModel):
    content: list[dict[str, Any]]
    is_error: bool = False


# ── MCP Tool Definitions ────────────────────────────────────────────────────────

MCP_TOOLS: list[MCPToolSchema] = [
    MCPToolSchema(
        name="web_search",
        description="Search the web for grounding evidence about a factual claim using Google Serper or keyless DuckDuckGo fallback.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query string to execute"},
                "date_from": {"type": "string", "description": "Optional start date filter (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "Optional end date filter (YYYY-MM-DD)"},
                "count": {"type": "integer", "description": "Number of search results to return", "default": 10},
            },
            "required": ["query"],
        },
    ),
    MCPToolSchema(
        name="verify_domain",
        description="Lookup WHOIS registration date and domain age for a publisher domain to assess recency red flags.",
        input_schema={
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain name to inspect (e.g. bbc-news-update.com)"},
            },
            "required": ["domain"],
        },
    ),
    MCPToolSchema(
        name="query_factcheck_db",
        description="Query the Google Fact Check Tools API for existing ClaimReview verdicts from Snopes, PolitiFact, etc.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Claim text keywords to look up in the fact-check index"},
                "language_code": {"type": "string", "description": "Language ISO code (default: en)", "default": "en"},
            },
            "required": ["query"],
        },
    ),
    MCPToolSchema(
        name="fetch_article",
        description="Fetch a news article URL and render clean Markdown text via Jina Reader.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Direct HTTP/HTTPS article URL to fetch"},
            },
            "required": ["url"],
        },
    ),
    MCPToolSchema(
        name="pubmed_search",
        description="Search PubMed NCBI database for biomedical, clinical trial, and health literature.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Medical or health claim keywords"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    ),
    MCPToolSchema(
        name="arxiv_search",
        description="Search ArXiv API for physics, computer science, mathematics, and climate preprints.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Scientific or technical keywords"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    ),
    MCPToolSchema(
        name="semantic_scholar_search",
        description="Search Semantic Scholar graph API for academic paper citations, abstracts, and authors.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Academic search query"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    ),
    MCPToolSchema(
        name="image_forensics",
        description="Inspect an image file for perceptual hash (pHash), Error Level Analysis (ELA) manipulation score, and EXIF metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to local image file"},
            },
            "required": ["image_path"],
        },
    ),
]


# ── MCP Tool Execution Dispatcher ──────────────────────────────────────────────

def list_mcp_tools() -> list[dict[str, Any]]:
    """Return list of standard MCP Tool schemas for tool discovery."""
    return [t.model_dump(by_alias=True) for t in MCP_TOOLS]


def execute_mcp_tool(name: str, arguments: dict[str, Any], config: dict | None = None) -> MCPToolResponse:
    """
    Execute an MCP tool by name with arguments.
    Enforces non-raising error boundary — returns structured error MCP response on exception.
    """
    config = config or {}
    try:
        if name == "web_search":
            from app.tools.search_tools import web_search, SearchRequest
            req = SearchRequest(
                query=arguments.get("query", ""),
                date_from=arguments.get("date_from"),
                date_to=arguments.get("date_to"),
                count=arguments.get("count", 10),
            )
            res = web_search(req, config)
            return MCPToolResponse(content=[{"type": "text", "text": res.model_dump_json()}])

        elif name == "verify_domain":
            from app.tools.provenance_tools import verify_domain, DomainVerifyRequest
            req = DomainVerifyRequest(domain=arguments.get("domain", ""))
            res = verify_domain(req)
            return MCPToolResponse(content=[{"type": "text", "text": res.model_dump_json()}])

        elif name == "query_factcheck_db":
            from app.tools.reference_tools import query_factcheck_db, FactCheckRequest
            req = FactCheckRequest(
                query=arguments.get("query", ""),
                language_code=arguments.get("language_code", "en"),
            )
            res = query_factcheck_db(req, config)
            return MCPToolResponse(content=[{"type": "text", "text": res.model_dump_json()}])

        elif name == "fetch_article":
            from app.tools.search_tools import fetch_article, ArticleFetchRequest
            req = ArticleFetchRequest(url=arguments.get("url", ""))
            res = fetch_article(req)
            return MCPToolResponse(content=[{"type": "text", "text": res.model_dump_json()}])

        elif name == "pubmed_search":
            from app.tools.reference_tools import search_pubmed, AcademicSearchRequest
            req = AcademicSearchRequest(query=arguments.get("query", ""), max_results=arguments.get("max_results", 5))
            res = search_pubmed(req)
            return MCPToolResponse(content=[{"type": "text", "text": res.model_dump_json()}])

        elif name == "arxiv_search":
            from app.tools.reference_tools import search_arxiv, AcademicSearchRequest
            req = AcademicSearchRequest(query=arguments.get("query", ""), max_results=arguments.get("max_results", 5))
            res = search_arxiv(req)
            return MCPToolResponse(content=[{"type": "text", "text": res.model_dump_json()}])

        elif name == "semantic_scholar_search":
            from app.tools.reference_tools import search_semantic_scholar, AcademicSearchRequest
            req = AcademicSearchRequest(query=arguments.get("query", ""), max_results=arguments.get("max_results", 5))
            res = search_semantic_scholar(req)
            return MCPToolResponse(content=[{"type": "text", "text": res.model_dump_json()}])

        elif name == "image_forensics":
            from app.tools.forensic_tools import analyze_image, ImageAnalysisRequest
            req = ImageAnalysisRequest(image_path=arguments.get("image_path", ""))
            res = analyze_image(req)
            return MCPToolResponse(content=[{"type": "text", "text": res.model_dump_json()}])

        else:
            return MCPToolResponse(
                content=[{"type": "text", "text": f"Unknown MCP tool capability: '{name}'"}],
                is_error=True,
            )

    except Exception as e:
        return MCPToolResponse(
            content=[{"type": "text", "text": f"MCP Tool '{name}' execution error: {str(e)[:200]}"}],
            is_error=True,
        )
