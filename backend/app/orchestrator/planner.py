from __future__ import annotations
import uuid
from app.protocols.blackboard import Blackboard
from app.protocols.messages import Plan, Task


def bootstrap_plan(blackboard: Blackboard, initial_tasks: list[Task] | None = None) -> Plan:
    """
    Build the initial plan for Blackboard.
    If initial_tasks is provided, uses them; otherwise starts with decomposition task T1.
    """
    if initial_tasks is not None:
        return Plan(tasks=initial_tasks)
    return Plan(tasks=[
        Task(
            task_id="T1",
            agent="decomposition",
            claim_id="C0",
            params={"raw_input": blackboard.raw_input},
            parallel_group=None,
        )
    ])


# Alias for backward compatibility during migration
initial_plan = bootstrap_plan
