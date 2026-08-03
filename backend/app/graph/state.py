"""
LangGraph State Schema Definition for Scrutin
=============================================
Defines the typed graph state passed between state graph nodes.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from app.protocols.messages import Task, Plan, VerificationReport


class ScrutinGraphState(BaseModel):
    run_id: str
    raw_input: str
    input_type: str = "text"
    atomic_claims: dict[str, str] = Field(default_factory=dict)
    evidence_store: dict[str, Any] = Field(default_factory=dict)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    plan: Plan = Field(default_factory=Plan)
    iterations: int = 0
    budget_limit: int = 20
    provisional_verdict: str | None = None
    final_report: VerificationReport | None = None
    is_complete: bool = False
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}
