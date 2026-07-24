from __future__ import annotations
import asyncio
import os
import time

class StandardRateLimiter:
    """Standard library rate limiter using asyncio.Lock & time.monotonic()."""

    def __init__(self, rate_period: float) -> None:
        self.rate_period = rate_period
        self.last_call = 0.0
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        if "PYTEST_CURRENT_TEST" in os.environ:
            return
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_call
            if elapsed < self.rate_period:
                await asyncio.sleep(self.rate_period - elapsed)
            self.last_call = time.monotonic()

_groq_limiter = StandardRateLimiter(2.4)    # Groq ~25 RPM headroom
_gemini_limiter = StandardRateLimiter(5.0)  # Gemini ~12 RPM headroom

async def groq_acquire() -> None:
    await _groq_limiter.acquire()

async def gemini_acquire() -> None:
    await _gemini_limiter.acquire()
