from __future__ import annotations
import os
from pydantic_ai import Agent
from app.agents.base import AgentDeps
from app.agents.prompts import get_prompt
from app.protocols.messages import VerificationReport

orchestrator_agent = Agent(
    os.getenv("ORCHESTRATOR_MODEL", "google:gemini-2.5-flash"),
    deps_type=AgentDeps,
    output_type=VerificationReport,
    system_prompt=get_prompt("orchestrator"),
)
# No tools — orchestrator synthesizes from Blackboard state passed in user message
# It NEVER calls sub-agents directly — it only writes the final report
