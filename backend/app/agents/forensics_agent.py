from __future__ import annotations
import asyncio
import os
from typing import Any
from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent
from app.agents.base import AgentDeps, get_agent_model
from app.agents.prompts import get_prompt
from app.protocols.messages import Finding

forensics_agent = Agent(
    get_agent_model("FORENSICS_MODEL"),
    deps_type=AgentDeps,
    output_type=Finding,
    system_prompt=get_prompt("forensics"),
)

class TranscribeReq(BaseModel):
    media_url_or_path: str

class ImageReq(BaseModel):
    image_path: str

@forensics_agent.tool
async def transcribe_media_tool(ctx, media_url: str) -> dict[str, Any]:
    """Transcribe audio or video to text using Groq Whisper (fast, free tier)."""
    from app.tools.registry import call as registry_call
    try:
        resp = await asyncio.to_thread(registry_call, "transcribe_media", TranscribeReq(media_url_or_path=media_url), ctx.deps.config)
        return resp.model_dump()
    except Exception as e:
        logger.bind(agent="tool_error").error(f"Tool 'transcribe_media_tool' failed: {e}")
        return {"success": False, "transcript": "", "error_message": str(e)[:100], "provider": "failed"}


@forensics_agent.tool
async def analyze_image_tool(ctx, image_path: str) -> dict[str, Any]:
    """Analyze an image for manipulation signs using pHash and forensic tools."""
    from app.tools.registry import call as registry_call
    try:
        resp = await asyncio.to_thread(registry_call, "analyze_image", ImageReq(image_path=image_path))
        return resp.model_dump()
    except Exception as e:
        logger.bind(agent="tool_error").error(f"Tool 'analyze_image_tool' failed: {e}")
        return {
            "is_manipulated": False,
            "manipulation_score": 0.0,
            "predicted_country": None,
            "gps_coordinates": None,
            "perceptual_hash": None,
            "error": str(e)[:100]
        }
