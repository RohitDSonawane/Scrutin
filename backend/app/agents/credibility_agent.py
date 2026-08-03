from __future__ import annotations
import asyncio
import os
from typing import Any
from loguru import logger
from pydantic_ai import Agent
from app.agents.base import AgentDeps, get_agent_model
from app.agents.prompts import get_prompt
from app.protocols.messages import Finding

credibility_agent = Agent(
    get_agent_model("CREDIBILITY_MODEL"),
    deps_type=AgentDeps,
    output_type=Finding,
    system_prompt=get_prompt("credibility"),
)

@credibility_agent.tool
async def whois_lookup_tool(ctx, domain: str) -> dict[str, Any]:
    """Look up WHOIS registration data for a domain to check age and registrar."""
    from app.tools.provenance_tools import DomainVerifyRequest
    from app.tools.registry import call as registry_call
    try:
        req = DomainVerifyRequest(domain=domain)
        resp = await asyncio.to_thread(registry_call, "whois", req)
        return resp.model_dump()
    except Exception as e:
        logger.bind(agent="tool_error").error(f"Tool 'whois_lookup_tool' failed: {e}")
        return {
            "domain": domain,
            "registered_at": "",
            "registrar": "unknown",
            "is_recent": False,
            "error": str(e)[:100]
        }


@credibility_agent.tool
async def get_existing_reputation_tool(ctx, domain: str) -> dict[str, Any]:
    """Check long-term reputation memory for this domain (fast path)."""
    try:
        from app.memory.longterm import get_reputation
        rep = await get_reputation(domain)
        return rep or {"domain": domain, "status": "unknown"}
    except Exception as e:
        logger.bind(agent="tool_error").error(f"Tool 'get_existing_reputation_tool' failed: {e}")
        return {"domain": domain, "status": "unknown", "error": str(e)[:100]}
