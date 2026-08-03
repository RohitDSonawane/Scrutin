from __future__ import annotations
import asyncio
import os
from typing import Any
from loguru import logger
from pydantic_ai import Agent
from app.agents.base import AgentDeps, get_agent_model
from app.agents.prompts import get_prompt
from app.protocols.messages import Finding

evidence_agent = Agent(
    get_agent_model("EVIDENCE_MODEL"),
    deps_type=AgentDeps,
    output_type=Finding,
    system_prompt=get_prompt("evidence"),
)

@evidence_agent.tool
async def web_search_tool(ctx, query: str, date_from: str = "", date_to: str = "") -> dict[str, Any]:
    """Search the web for evidence about the claim using Serper (Google) or DuckDuckGo fallback."""
    from app.tools.search_tools import SearchRequest
    from app.tools.registry import call as registry_call
    try:
        req = SearchRequest(query=query, date_from=date_from or None, date_to=date_to or None)
        resp = await asyncio.to_thread(registry_call, "web_search", req, ctx.deps.config)
        
        results_summary = []
        for item in resp.results:
            eid = ctx.deps.blackboard.store_evidence("WB", item.model_dump())
            results_summary.append({
                "evidence_id": eid,
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
                "source_domain": item.source_domain,
            })
        return {"results": results_summary, "backend": resp.backend_used, "count": len(results_summary)}
    except Exception as e:
        logger.bind(agent="tool_error").error(f"Tool 'web_search_tool' failed: {e}")
        return {"results": [], "backend": "failed", "count": 0, "error": str(e)[:100]}


@evidence_agent.tool
async def factcheck_lookup_tool(ctx, query: str) -> dict[str, Any]:
    """Check Google Fact Check Tools API for existing verdicts on this claim (fast path)."""
    from app.tools.reference_tools import FactCheckRequest
    from app.tools.registry import call as registry_call
    try:
        req = FactCheckRequest(query=query)
        resp = await asyncio.to_thread(registry_call, "fact_check", req, ctx.deps.config)
        # Store FC results on Blackboard
        ids = []
        for item in resp.verdicts:
            eid = ctx.deps.blackboard.store_evidence("FC", item.model_dump())
            ids.append(eid)
        return {"fc_ids": ids, "matches_found": resp.matches_found}
    except Exception as e:
        logger.bind(agent="tool_error").error(f"Tool 'factcheck_lookup_tool' failed: {e}")
        return {"fc_ids": [], "matches_found": 0, "error": str(e)[:100]}
