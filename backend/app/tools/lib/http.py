import requests
import asyncio

def get(url: str, params: dict = None) -> dict:
    """Helper for JSON GET requests (synchronous)."""
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

async def get_async(url: str, params: dict = None) -> dict:
    """Helper for JSON GET requests (non-blocking async)."""
    return await asyncio.to_thread(get, url, params)
