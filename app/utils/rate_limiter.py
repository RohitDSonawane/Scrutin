from __future__ import annotations
import asyncio
from aiolimiter import AsyncLimiter

# Groq free tier limit is 30 RPM. We use 25 for safe headroom.
GROQ_RPM_LIMIT = 25.0

_groq_limiter: AsyncLimiter | None = None
_groq_limiter_loop: asyncio.AbstractEventLoop | None = None


async def groq_acquire() -> None:
    """
    Acquire a Groq RPM token before every Groq agent call.
    Blocks until a token is available.
    Safe against cross-loop/closed-loop warnings in pytest runs.
    """
    global _groq_limiter, _groq_limiter_loop
    current_loop = asyncio.get_running_loop()
    if _groq_limiter is None or _groq_limiter_loop is not current_loop:
        _groq_limiter = AsyncLimiter(GROQ_RPM_LIMIT, time_period=60.0)
        _groq_limiter_loop = current_loop
    await _groq_limiter.acquire()
