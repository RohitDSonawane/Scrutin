import pytest
import asyncio
from fastapi.testclient import TestClient
from app.api import app

def test_api_stream_endpoint():
    """Verify that /api/verify/stream initializes asyncio Queue and streams SSE events without import error."""
    client = TestClient(app)
    # Perform a GET request on stream endpoint
    response = client.get("/api/verify/stream?claim=Test+claim")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
