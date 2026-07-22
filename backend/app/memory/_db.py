# app/memory/_db.py
from __future__ import annotations
import os
import aiosqlite

DB_PATH_DEFAULT = os.getenv("SCRUTIN_DB_PATH", "scrutin.db")

async def get_db(db_path: str = DB_PATH_DEFAULT) -> aiosqlite.Connection:
    """Open a WAL-mode async SQLite connection. Use as async context manager."""
    db = await aiosqlite.connect(db_path)
    await db.execute("PRAGMA journal_mode=WAL")   # MANDATORY — prevents 'database is locked'
    await db.execute("PRAGMA foreign_keys=ON")
    return db
