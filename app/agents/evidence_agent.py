from __future__ import annotations
import os
from pydantic_ai import Agent
from app.agents.base import AgentDeps
from app.agents.prompts import get_prompt
from app.protocols.messages import Finding

evidence_agent = Agent(
    os.getenv("EVIDENCE_MODEL", "google:gemini-2.5-flash"),
    deps_type=AgentDeps,
    output_type=Finding,
    system_prompt=get_prompt("evidence"),
)

@evidence_agent.tool
async def web_search_tool(ctx, query: str, date_from: str = "", date_to: str = "") -> dict:
    """Search the web for evidence about the claim using Serper (Google) or DuckDuckGo fallback."""
    from app.tools.search_tools import SearchRequest
    from app.tools.registry import call as registry_call
    try:
        req = SearchRequest(query=query, date_from=date_from or None, date_to=date_to or None)
        resp = registry_call("web_search", req, ctx.deps.config)
        # Store results on Blackboard and return pointer IDs
        ids = []
        for item in resp.results:
            eid = ctx.deps.blackboard.store_evidence("WB", item.model_dump())
            ids.append(eid)
        return {"evidence_ids": ids, "backend": resp.backend_used, "count": len(ids)}
    except Exception as e:
        from loguru import logger
        logger.bind(agent="tool_error").error(f"Tool 'web_search_tool' failed: {e}")
        return {"evidence_ids": [], "backend": "failed", "count": 0, "error": str(e)[:100]}


@evidence_agent.tool
async def factcheck_lookup_tool(ctx, query: str) -> dict:
    """Check Google Fact Check Tools API for existing verdicts on this claim (fast path)."""
    from app.tools.reference_tools import FactCheckRequest
    from app.tools.registry import call as registry_call
    try:
        req = FactCheckRequest(query=query)
        resp = registry_call("fact_check", req, ctx.deps.config)
        # Store FC results on Blackboard
        ids = []
        for item in resp.verdicts:
            eid = ctx.deps.blackboard.store_evidence("FC", item.model_dump())
            ids.append(eid)
        return {"fc_ids": ids, "matches_found": resp.matches_found}
    except Exception as e:
        from loguru import logger
        logger.bind(agent="tool_error").error(f"Tool 'factcheck_lookup_tool' failed: {e}")
        return {"fc_ids": [], "matches_found": 0, "error": str(e)[:100]}
