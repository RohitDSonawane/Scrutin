from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from app.tools.lib import http


# ── Schemas ────────────────────────────────────────────────────────────────────

class FactCheckRequest(BaseModel):
    query: str = Field(description="Claim keywords to look up in the Google Fact Check index")
    language_code: str = "en"
    max_results: int = 5


class FactCheckItem(BaseModel):
    claim_text: str
    claimant: Optional[str] = None
    verdict: str                    # "True" | "False" | "Misleading" | etc.
    review_publisher: str           # e.g. "Snopes", "PolitiFact"
    review_url: str
    review_date: Optional[str] = None


class FactCheckResponse(BaseModel):
    matches_found: int
    verdicts: list[FactCheckItem]
    query_used: str


# ── Tool function ──────────────────────────────────────────────────────────────

FACT_CHECK_API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

def query_factcheck_db(request: FactCheckRequest, config: dict) -> FactCheckResponse:
    """
    Query the Google Fact Check Tools API for existing ClaimReview verdicts.
    This is the Evidence agent's fast-path: if a matching verdict already exists,
    no web search is needed.
    Config keys: GOOGLE_FACT_CHECK_API_KEY
    Returns empty list on any failure — never raises.
    """
    api_key = config.get("GOOGLE_FACT_CHECK_API_KEY", "")
    if not api_key:
        return FactCheckResponse(matches_found=0, verdicts=[], query_used=request.query)

    try:
        data = http.get(FACT_CHECK_API_URL, params={
            "key": api_key,
            "query": request.query,
            "languageCode": request.language_code,
            "pageSize": request.max_results,
        })
    except Exception:
        return FactCheckResponse(matches_found=0, verdicts=[], query_used=request.query)

    claims = data.get("claims", [])
    verdicts = []
    for claim in claims:
        for review in claim.get("claimReview", []):
            verdicts.append(FactCheckItem(
                claim_text=claim.get("text", ""),
                claimant=claim.get("claimant"),
                verdict=review.get("textualRating", "unknown"),
                review_publisher=review.get("publisher", {}).get("name", "unknown"),
                review_url=review.get("url", ""),
                review_date=review.get("reviewDate"),
            ))

    return FactCheckResponse(
        matches_found=len(verdicts),
        verdicts=verdicts,
        query_used=request.query,
    )
