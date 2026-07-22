import requests

def get(url: str, params: dict = None) -> dict:
    """Helper for JSON GET requests."""
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()
