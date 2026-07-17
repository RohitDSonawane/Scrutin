from __future__ import annotations
import os
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from app.agents.base import AgentDeps
from app.agents.prompts import get_prompt


class DecompositionOutput(BaseModel):
    claims: list[dict] = Field(
        description="List of {claim_id, claim_text, claim_type, is_load_bearing}"
    )
    opinion_flags: list[str] = Field(default_factory=list)
    decomposition_note: str = ""


decomposition_agent = Agent(
    os.getenv("DECOMPOSITION_MODEL", "groq:llama-3.1-8b-instant"),
    deps_type=AgentDeps,
    output_type=DecompositionOutput,
    system_prompt=get_prompt("decomposition"),
)
