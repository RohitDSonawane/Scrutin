# tests/conftest.py
from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "mock_groq_api_key"
if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = "mock_google_api_key"

import pytest
from app.memory.migrations import run_migrations


@pytest.fixture
def db_path(tmp_path):
    """Shared fixture: creates a fresh migrations-applied DB for every test."""
    path = str(tmp_path / "test_scrutin.db")
    run_migrations(path)
    return path
