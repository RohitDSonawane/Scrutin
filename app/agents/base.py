from __future__ import annotations
from dataclasses import dataclass, field
from loguru import logger
from aiolimiter import AsyncLimiter

# Global limiter reference, initialized lazily on the running loop to avoid warnings
_groq_limiter: AsyncLimiter | None = None

async def groq_acquire() -> None:
    """Acquire a slot on the Groq rate limiter before invocation to prevent 429s."""
    global _groq_limiter
    if _groq_limiter is None:
        _groq_limiter = AsyncLimiter(30, 60)
    await _groq_limiter.acquire()


@dataclass
class AgentDeps:
    """
    Injected into every agent via PydanticAI dependency injection.
    Holds the shared Blackboard reference and the config dict with all API keys.
    """
    blackboard: "Blackboard"     # type: app.protocols.blackboard.Blackboard
    config: dict = field(default_factory=dict)
    agent_budget: int = 5        # Max tool calls this agent may make this invocation


def get_agent_logger(agent_name: str):
    """Returns a loguru logger bound to the agent name for colored terminal trace."""
    return logger.bind(agent=agent_name)
