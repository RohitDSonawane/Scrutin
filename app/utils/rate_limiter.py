from __future__ import annotations
import asyncio
from aiolimiter import AsyncLimiter

# Groq free tier limit is 30 RPM. We use 25 for safe headroom.
GROQ_RPM_LIMIT = 25.0

# Gemini free tier limit is 15 RPM. We use 12 for safe headroom.
GEMINI_RPM_LIMIT = 12.0

_groq_limiter: AsyncLimiter | None = None
_groq_limiter_loop: asyncio.AbstractEventLoop | None = None

_gemini_limiter: AsyncLimiter | None = None
_gemini_limiter_loop: asyncio.AbstractEventLoop | None = None


async def groq_acquire() -> None:
    """
    Acquire a Groq RPM token before every Groq agent call.
    Blocks until a token is available.
    Safe against cross-loop/closed-loop warnings in pytest runs.
    """
    import os
    if "PYTEST_CURRENT_TEST" in os.environ:
        return

    global _groq_limiter, _groq_limiter_loop
    current_loop = asyncio.get_running_loop()
    if _groq_limiter is None or _groq_limiter_loop is not current_loop:
        _groq_limiter = AsyncLimiter(1, time_period=2.4)
        _groq_limiter_loop = current_loop
    await _groq_limiter.acquire()


async def gemini_acquire() -> None:
    """
    Acquire a Gemini RPM token before every Gemini agent call.
    Blocks until a token is available.
    Safe against cross-loop/closed-loop warnings in pytest runs.
    """
    import os
    if "PYTEST_CURRENT_TEST" in os.environ:
        return

    global _gemini_limiter, _gemini_limiter_loop
    current_loop = asyncio.get_running_loop()
    if _gemini_limiter is None or _gemini_limiter_loop is not current_loop:
        _gemini_limiter = AsyncLimiter(1, time_period=5.0)
        _gemini_limiter_loop = current_loop
    await _gemini_limiter.acquire()
