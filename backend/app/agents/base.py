from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from loguru import logger

if TYPE_CHECKING:
    from app.protocols.blackboard import Blackboard


@dataclass
class AgentDeps:
    """
    Injected into every agent via PydanticAI dependency injection.
    Holds the shared Blackboard reference and the config dict with all API keys.
    """
    blackboard: Blackboard
    config: dict[str, Any] = field(default_factory=dict)
    agent_budget: int = 5        # Max tool calls this agent may make this invocation


def get_agent_logger(agent_name: str):
    """Returns a loguru logger bound to the agent name for colored terminal trace."""
    return logger.bind(agent=agent_name)


def get_agent_model(env_var_name: str) -> Any:
    """
    Factory that returns an OpenRouterModel or string model target based on configuration.
    All model names are resolved exclusively from environment variables.
    Cascade: env_var_name -> DEFAULT_MODEL -> ORCHESTRATOR_MODEL.
    """
    from pydantic_ai.models.openrouter import OpenRouterModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    raw = (
        os.getenv(env_var_name)
        or os.getenv("DEFAULT_MODEL")
        or os.getenv("ORCHESTRATOR_MODEL")
    )
    if not raw:
        raise RuntimeError(
            f"No model configured: set {env_var_name}, DEFAULT_MODEL, or ORCHESTRATOR_MODEL in .env"
        )

    key = os.getenv("OPENROUTER_API_KEY", "")

    if key and (raw.startswith("google/") or raw.startswith("openrouter/") or "gemma" in raw):
        clean_name = raw.replace("openrouter:", "").replace("openrouter/", "")
        return OpenRouterModel(clean_name, provider=OpenRouterProvider(api_key=key))
    return raw
