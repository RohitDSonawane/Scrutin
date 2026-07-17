from __future__ import annotations
import os
from pydantic_ai import Agent
from app.agents.base import AgentDeps
from app.agents.prompts import get_prompt
from app.protocols.messages import Finding

credibility_agent = Agent(
    os.getenv("CREDIBILITY_MODEL", "groq:llama-3.3-70b-versatile"),
    deps_type=AgentDeps,
    output_type=Finding,
    system_prompt=get_prompt("credibility"),
)

@credibility_agent.tool
async def whois_lookup_tool(ctx, domain: str) -> dict:
    """Look up WHOIS registration data for a domain to check age and registrar."""
    from app.tools.provenance_tools import DomainVerifyRequest
    from app.tools.registry import call as registry_call
    try:
        req = DomainVerifyRequest(domain=domain)
        resp = registry_call("whois", req)
        return resp.model_dump()
    except Exception as e:
        from loguru import logger
        logger.bind(agent="tool_error").error(f"Tool 'whois_lookup_tool' failed: {e}")
        return {
            "domain": domain,
            "registered_at": "",
            "registrar": "unknown",
            "is_recent": False,
            "error": str(e)[:100]
        }


@credibility_agent.tool
async def get_existing_reputation_tool(ctx, domain: str) -> dict:
    """Check long-term reputation memory for this domain (fast path)."""
    try:
        from app.memory.longterm import get_reputation
        rep = await get_reputation(domain)
        return rep or {"domain": domain, "status": "unknown"}
    except Exception as e:
        from loguru import logger
        logger.bind(agent="tool_error").error(f"Tool 'get_existing_reputation_tool' failed: {e}")
        return {"domain": domain, "status": "unknown", "error": str(e)[:100]}
