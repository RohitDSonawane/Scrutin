import requests
import json
from urllib.parse import urlparse

def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""

def web_search(query: str, date_range: tuple | None, config: dict, backend: str):
    """Web search implementation using Serper.dev API."""
    api_key = config.get("SERPER_API_KEY")
    if not api_key or backend == "keyless":
        # DuckDuckGo fallback (simplified mock for now)
        return [], {"label": "keyless", "resultCount": 0}
        
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query, "num": 10})
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code != 200:
        raise Exception(f"Serper API error: {response.status_code}")
        
    data = response.json()
    organic = data.get("organic", [])
    
    items = []
    for res in organic:
        items.append({
            "title": res.get("title", ""),
            "url": res.get("link", ""),
            "source_domain": get_domain(res.get("link", "")),
            "snippet": res.get("snippet", ""),
            "date": res.get("date", ""),
            "relevance": 0.9 # Default relevance
        })
        
    return items, {"label": "serper", "resultCount": len(items)}
