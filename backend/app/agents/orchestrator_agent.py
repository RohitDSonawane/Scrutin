from __future__ import annotations
import os
from pydantic_ai import Agent
from app.agents.base import AgentDeps, get_agent_model
from app.agents.prompts import get_prompt
from app.protocols.messages import OrchestratorDecision

orchestrator_agent = Agent(
    get_agent_model("ORCHESTRATOR_MODEL"),
    deps_type=AgentDeps,
    output_type=OrchestratorDecision,
    system_prompt=get_prompt("orchestrator"),
    retries=3,
)
# Called once per orchestration iteration. Decides to delegate (emit Tasks) or finalize
# (emit VerificationReport). Never calls sub-agents directly — Python executes its decision.
