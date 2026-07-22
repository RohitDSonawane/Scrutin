from __future__ import annotations
import os
from pydantic_ai import Agent
from app.agents.base import AgentDeps
from app.agents.prompts import get_prompt
from app.protocols.messages import AdversarialCritique

adversarial_agent = Agent(
    # MUST be on Groq — different provider than Evidence/Orchestrator (Gemini)
    # This cross-provider independence is the architectural reason this agent exists
    os.getenv("ADVERSARIAL_MODEL", "groq:llama-3.3-70b-versatile"),
    deps_type=AgentDeps,
    output_type=AdversarialCritique,
    system_prompt=get_prompt("adversarial"),
)

# NOTE: The adversarial agent has NO tools by design (architecture §3.6).
# It receives only: (a) raw compiled evidence IDs + snippets, (b) provisional verdict string.
# It does NOT receive the Evidence agent's reasoning trace.
# It does NOT receive the Orchestrator's planning notes.
# Any targeted follow-up search request goes through the Orchestrator as an AgentRequest.
