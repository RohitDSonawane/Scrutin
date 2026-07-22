from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from app.tools.provenance_tools import verify_domain, DomainVerifyRequest


def test_verify_domain_detects_recent_domain():
    """A domain registered 30 days ago should be flagged as recent."""
    from datetime import datetime, timezone, timedelta
    mock_whois = MagicMock()
    mock_whois.creation_date = datetime.now(timezone.utc) - timedelta(days=30)
    mock_whois.registrar = "GoDaddy"

    with patch("whois.whois", return_value=mock_whois):
        result = verify_domain(DomainVerifyRequest(domain="new-domain.com"))

    assert result.is_recent is True
    assert result.domain_age_days < 180
    assert result.registrar == "GoDaddy"


def test_verify_domain_detects_old_domain():
    """A domain registered 5 years ago should NOT be flagged as recent."""
    from datetime import datetime, timezone, timedelta
    mock_whois = MagicMock()
    mock_whois.creation_date = datetime.now(timezone.utc) - timedelta(days=1825)
    mock_whois.registrar = "Namecheap"

    with patch("whois.whois", return_value=mock_whois):
        result = verify_domain(DomainVerifyRequest(domain="reuters.com"))

    assert result.is_recent is False
    assert result.domain_age_days > 180


def test_verify_domain_never_raises():
    """Even on WHOIS failure, should return gracefully."""
    with patch("whois.whois", side_effect=Exception("WHOIS lookup failed")):
        result = verify_domain(DomainVerifyRequest(domain="bad-domain.invalid"))

    assert result.lookup_failed is True
    assert len(result.failure_reason) > 0
