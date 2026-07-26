from __future__ import annotations
import os
from pydantic_ai import Agent
from app.agents.base import AgentDeps, get_agent_model
from app.agents.prompts import get_prompt
from app.protocols.messages import AdversarialCritique

adversarial_agent = Agent(
    get_agent_model("ADVERSARIAL_MODEL", "google/gemma-4-26b-a4b-it:free"),
    deps_type=AgentDeps,
    output_type=AdversarialCritique,
    system_prompt=get_prompt("adversarial"),
)

# NOTE: The adversarial agent has NO tools by design (architecture §3.6).
# It receives only: (a) raw compiled evidence IDs + snippets, (b) provisional verdict string.
# It does NOT receive the Evidence agent's reasoning trace.
# It does NOT receive the Orchestrator's planning notes.
# Any targeted follow-up search request goes through the Orchestrator as an AgentRequest.
