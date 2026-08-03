from __future__ import annotations
import os
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from app.agents.base import AgentDeps, get_agent_model
from app.agents.prompts import get_prompt


class AtomicClaim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: str
    is_load_bearing: bool


class DecompositionOutput(BaseModel):
    claims: list[AtomicClaim] = Field(
        description="List of structured atomic claims"
    )
    opinion_flags: list[str] = Field(default_factory=list)
    decomposition_note: str = ""

decomposition_agent = Agent(
    get_agent_model("DECOMPOSITION_MODEL"),
    deps_type=AgentDeps,
    output_type=DecompositionOutput,
    system_prompt=get_prompt("decomposition"),
)
