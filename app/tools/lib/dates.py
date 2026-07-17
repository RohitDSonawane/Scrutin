from __future__ import annotations
from datetime import datetime

def parse_date(value: str) -> datetime | None:
    """Parse a date string robustly and return a datetime object."""
    cleaned = value.strip()
    # Handle ISO formats
    if "T" in cleaned:
        cleaned = cleaned.split("T")[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None
