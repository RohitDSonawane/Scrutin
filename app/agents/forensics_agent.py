from __future__ import annotations
import os
from pydantic_ai import Agent
from app.agents.base import AgentDeps
from app.agents.prompts import get_prompt
from app.protocols.messages import Finding

forensics_agent = Agent(
    os.getenv("FORENSICS_MODEL", "google:gemini-2.5-flash"),
    deps_type=AgentDeps,
    output_type=Finding,
    system_prompt=get_prompt("forensics"),
)

@forensics_agent.tool
async def transcribe_media_tool(ctx, media_url: str) -> dict:
    """Transcribe audio or video to text using Groq Whisper (fast, free tier)."""
    from app.tools.registry import call as registry_call
    from pydantic import BaseModel
    class Req(BaseModel):
        media_url_or_path: str
    resp = registry_call("transcribe_media", Req(media_url_or_path=media_url), ctx.deps.config)
    return resp.model_dump()


@forensics_agent.tool
async def analyze_image_tool(ctx, image_path: str) -> dict:
    """Analyze an image for manipulation signs using pHash and forensic tools."""
    from pydantic import BaseModel
    class Req(BaseModel):
        image_path: str
    from app.tools.registry import call as registry_call
    resp = registry_call("analyze_image", Req(image_path=image_path))
    return resp.model_dump()
