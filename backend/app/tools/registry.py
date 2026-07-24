from __future__ import annotations
from typing import Callable, Any
from dataclasses import dataclass

@dataclass(slots=True)
class ToolRegistration:
    name: str
    capability: str
    fn: Callable
    description: str = ""
    requires_config: bool = True

_REGISTRY: dict[str, ToolRegistration] = {}

def register(capability: str, description: str = "", requires_config: bool = True):
    """Decorator to register a tool function by its capability tag."""
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[capability] = ToolRegistration(
            name=fn.__name__, capability=capability, fn=fn, description=description, requires_config=requires_config
        )
        return fn
    return decorator

def get(capability: str) -> ToolRegistration:
    if capability not in _REGISTRY:
        raise KeyError(f"No tool registered for capability '{capability}'. Available: {list(_REGISTRY.keys())}")
    return _REGISTRY[capability]

def call(capability: str, request: Any, config: dict | None = None) -> Any:
    reg = get(capability)
    return reg.fn(request, config or {}) if reg.requires_config else reg.fn(request)

def list_capabilities() -> list[str]:
    return list(_REGISTRY.keys())

def get_all_registrations() -> dict[str, ToolRegistration]:
    return dict(_REGISTRY)
