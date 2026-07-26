from __future__ import annotations
import uuid
from app.protocols.blackboard import Blackboard
from app.protocols.messages import Plan, Task


def bootstrap_plan(blackboard: Blackboard) -> Plan:
    """
    Build the initial bootstrap plan.
    Starts with decomposition task T1. The Orchestrator LLM decides subsequent tasks.
    """
    tasks: list[Task] = [
        Task(
            task_id="T1",
            agent="decomposition",
            claim_id="C0",
            params={"raw_input": blackboard.raw_input},
            parallel_group=None,
        )
    ]
    return Plan(tasks=tasks)


# Alias for backward compatibility during migration
initial_plan = bootstrap_plan
