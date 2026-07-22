from __future__ import annotations

def keyless_web_allowed(config: dict) -> bool:
    """Return whether keyless search is allowed when no keys are provided."""
    # Always allow keyless as a fallback to Serper/Brave
    return True
