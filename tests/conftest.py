# tests/conftest.py
from __future__ import annotations
import pytest
from app.memory.migrations import run_migrations


@pytest.fixture
def db_path(tmp_path):
    """Shared fixture: creates a fresh migrations-applied DB for every test."""
    path = str(tmp_path / "test_scrutin.db")
    run_migrations(path)
    return path
