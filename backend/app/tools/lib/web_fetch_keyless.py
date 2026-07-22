import requests
from dataclasses import dataclass

@dataclass
class FetchResult:
    ok: bool
    markdown: str = ""
    cached_snapshot: bool = False
    reason: str = ""

def fetch_markdown(url: str) -> FetchResult:
    """Fetch a URL and return clean Markdown via Jina Reader."""
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, timeout=10)
        if response.status_code == 200:
            return FetchResult(ok=True, markdown=response.text)
        else:
            return FetchResult(ok=False, reason=f"HTTP {response.status_code}")
    except Exception as e:
        return FetchResult(ok=False, reason=str(e))
