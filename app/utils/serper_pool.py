from __future__ import annotations
import itertools
import os
from typing import Iterator


def _load_serper_keys() -> list[str]:
    """Load all 4 Serper keys from environment. Returns non-empty keys only."""
    keys = []
    for suffix in ["", "_2", "_3", "_4"]:
        k = os.getenv(f"SERPER_API_KEY{suffix}", "").strip()
        if k:
            keys.append(k)
    return keys


class SerperKeyPool:
    """
    Round-robin key rotation across up to 4 Serper API keys.
    Falls back to keyless DuckDuckGo when all keys are exhausted.
    """
    def __init__(self):
        self._keys = _load_serper_keys()
        self._cycle: Iterator[str] = itertools.cycle(self._keys) if self._keys else iter([])
        self._exhausted_keys: set[str] = set()

    def next_key(self) -> str | None:
        """Get the next available key, or None if all keys are exhausted."""
        if not self._keys:
            return None
        for _ in range(len(self._keys)):
            key = next(self._cycle)
            if key not in self._exhausted_keys:
                return key
        return None  # All keys exhausted → fallback to keyless

    def mark_exhausted(self, key: str) -> None:
        """Mark a key as quota-exhausted for this session."""
        self._exhausted_keys.add(key)
        from loguru import logger
        logger.warning(f"Serper key ...{key[-6:] if len(key) >= 6 else key} marked exhausted. "
                       f"Remaining: {len(self._keys) - len(self._exhausted_keys)}")

    @property
    def has_keys(self) -> bool:
        return len(self._keys) > len(self._exhausted_keys)


# Singleton pool — shared across all tool calls in a process
_pool: SerperKeyPool | None = None

def get_pool() -> SerperKeyPool:
    global _pool
    if _pool is None:
        _pool = SerperKeyPool()
    return _pool
