from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


# ── Schemas ────────────────────────────────────────────────────────────────────

class DomainVerifyRequest(BaseModel):
    domain: str = Field(description="Domain name to look up (e.g. 'bbc-news-update.com')")


class DomainVerifyResponse(BaseModel):
    domain: str
    registered_at: Optional[str] = None    # YYYY-MM-DD
    registrar: Optional[str] = None
    is_recent: bool = False               # True if registered < 180 days ago
    domain_age_days: Optional[int] = None
    lookup_failed: bool = False
    failure_reason: str = ""


# ── Tool function ──────────────────────────────────────────────────────────────

RECENT_DOMAIN_THRESHOLD_DAYS = 180

def verify_domain(request: DomainVerifyRequest) -> DomainVerifyResponse:
    """
    WHOIS lookup for a domain. Returns registration age and recency flag.
    A domain registered < 180 days ago is flagged as 'recent' — a credibility red flag.
    Never raises. Returns lookup_failed=True on any error.
    """
    try:
        import whois
        w = whois.whois(request.domain)

        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if creation_date is None:
            return DomainVerifyResponse(
                domain=request.domain,
                registrar=str(w.registrar) if w.registrar else None,
                lookup_failed=False,
                failure_reason="no creation date in WHOIS record",
            )

        # Normalize to timezone-aware
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_days = (now - creation_date).days
        is_recent = age_days < RECENT_DOMAIN_THRESHOLD_DAYS

        return DomainVerifyResponse(
            domain=request.domain,
            registered_at=creation_date.strftime("%Y-%m-%d"),
            registrar=str(w.registrar) if w.registrar else None,
            is_recent=is_recent,
            domain_age_days=age_days,
        )

    except Exception as e:
        return DomainVerifyResponse(
            domain=request.domain,
            lookup_failed=True,
            failure_reason=str(e)[:200],
        )
