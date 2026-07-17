from __future__ import annotations
from pydantic_ai import Agent
from app.agents.base import AgentDeps
from app.agents.prompts import get_prompt
from app.protocols.messages import Finding

credibility_agent = Agent(
    "groq:llama-3.3-70b-versatile",
    deps_type=AgentDeps,
    output_type=Finding,
    system_prompt=get_prompt("credibility"),
)

@credibility_agent.tool
async def whois_lookup_tool(ctx, domain: str) -> dict:
    """Look up WHOIS registration data for a domain to check age and registrar."""
    from app.tools.provenance_tools import DomainVerifyRequest
    from app.tools.registry import call as registry_call
    req = DomainVerifyRequest(domain=domain)
    resp = registry_call("whois", req)
    return resp.model_dump()


@credibility_agent.tool
async def get_existing_reputation_tool(ctx, domain: str) -> dict:
    """Check long-term reputation memory for this domain (fast path)."""
    from app.memory.longterm import get_reputation
    rep = await get_reputation(domain)
    return rep or {"domain": domain, "status": "unknown"}
