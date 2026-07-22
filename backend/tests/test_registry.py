from __future__ import annotations
import pytest

# Register all tools before testing
import app.tools._register_all  # noqa: F401 — side-effect import

from app.tools.registry import get, call, list_capabilities, ToolRegistration
from app.tools.search_tools import SearchRequest


def test_all_capabilities_registered():
    caps = list_capabilities()
    required = {"web_search", "fetch_article", "fact_check", "whois"}
    assert required.issubset(set(caps)), f"Missing: {required - set(caps)}"


def test_get_returns_tool_registration():
    reg = get("web_search")
    assert isinstance(reg, ToolRegistration)
    assert reg.capability == "web_search"
    assert callable(reg.fn)


def test_get_raises_on_unknown_capability():
    with pytest.raises(KeyError, match="No tool registered for capability"):
        get("does_not_exist")


def test_capability_resolution_is_implementation_agnostic():
    """Swapping the underlying function should not break callers using capability name."""
    from app.tools.registry import _REGISTRY
    original_fn = _REGISTRY["whois"].fn

    # Swap to a mock
    def mock_whois(request, config=None):
        from pydantic import BaseModel
        class R(BaseModel):
            domain: str = "mock"
            is_recent: bool = False
            lookup_failed: bool = False
            failure_reason: str = ""
        return R()

    _REGISTRY["whois"].fn = mock_whois

    from app.tools.provenance_tools import DomainVerifyRequest
    result = call("whois", DomainVerifyRequest(domain="test.com"))
    assert result.domain == "mock"

    # Restore original
    _REGISTRY["whois"].fn = original_fn


def test_stubs_are_registered_for_forensics():
    assert "transcribe_media" in list_capabilities()
    assert "analyze_image" in list_capabilities()
