from __future__ import annotations
from dataclasses import dataclass, field
from loguru import logger
from aiolimiter import AsyncLimiter

import asyncio

from app.utils.rate_limiter import groq_acquire


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
