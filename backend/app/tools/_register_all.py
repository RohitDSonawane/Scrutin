"""
Registers all tools into the capability registry.
Import this module once at startup — e.g. in app/__init__.py or app/cli.py.
"""
from __future__ import annotations
from app.tools.registry import register

# ── Import tool functions ──────────────────────────────────────────────────────
from app.tools.search_tools import web_search, fetch_article
from app.tools.reference_tools import query_factcheck_db
from app.tools.provenance_tools import verify_domain
from app.tools.forensic_tools import transcribe_media, analyze_image


# ── Register each with its capability tag ─────────────────────────────────────

@register("web_search", description="Web search via Serper or DuckDuckGo fallback")
def _web_search(request, config):
    return web_search(request, config)


@register("fetch_article", description="Fetch article as Markdown via Jina Reader", requires_config=False)
def _fetch_article(request, config=None):
    return fetch_article(request)


@register("fact_check", description="Google Fact Check Tools API — ClaimReview verdicts")
def _fact_check(request, config):
    return query_factcheck_db(request, config)


@register("whois", description="WHOIS domain registration lookup", requires_config=False)
def _whois(request, config=None):
    return verify_domain(request)


@register("transcribe_media", description="Whisper media transcription via Groq/OpenAI")
def _transcribe_media(request, config):
    return transcribe_media(request, config)


@register("analyze_image", description="Image forensics via TruFor/pHash", requires_config=False)
def _analyze_image(request, config=None):
    return analyze_image(request)
