from __future__ import annotations
from typing import Callable, Any
from dataclasses import dataclass, field


@dataclass
class ToolRegistration:
    name: str
    capability: str           # e.g. "web_search", "fact_check", "whois"
    fn: Callable              # The actual stateless function to call
    description: str = ""
    requires_config: bool = True  # Does this tool need the config dict?


_REGISTRY: dict[str, ToolRegistration] = {}


def register(capability: str, description: str = "", requires_config: bool = True):
    """Decorator to register a tool function by its capability tag."""
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[capability] = ToolRegistration(
            name=fn.__name__,
            capability=capability,
            fn=fn,
            description=description,
            requires_config=requires_config,
        )
        return fn
    return decorator


def get(capability: str) -> ToolRegistration:
    """Resolve a capability tag to its current implementation."""
    if capability not in _REGISTRY:
        raise KeyError(
            f"No tool registered for capability '{capability}'. "
            f"Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[capability]


def call(capability: str, request: Any, config: dict | None = None) -> Any:
    """Call a tool by capability tag. Passes config only if tool requires it."""
    reg = get(capability)
    if reg.requires_config:
        return reg.fn(request, config or {})
    else:
        return reg.fn(request)


def list_capabilities() -> list[str]:
    return list(_REGISTRY.keys())


def get_all_registrations() -> dict[str, ToolRegistration]:
    return dict(_REGISTRY)
