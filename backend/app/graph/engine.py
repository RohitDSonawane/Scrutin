"""
LangGraph State Machine Engine for Scrutin
=========================================
Builds and runs the state graph engine for multi-agent claim verification.
"""

from __future__ import annotations
import time
from typing import Callable, Any
from loguru import logger

from app.graph.state import ScrutinGraphState
from app.graph.nodes import (
    decomposition_node,
    evidence_node,
    credibility_node,
    forensics_node,
    adversarial_node,
    finalizer_node,
)
from app.agents.base import AgentDeps
from app.protocols.messages import VerificationReport


async def run_graph_engine(
    state: ScrutinGraphState,
    deps: AgentDeps,
    emit: Callable[[str, dict], Any],
) -> VerificationReport:
    """
    Stateful execution graph engine for Scrutin multi-agent verification.
    Traverses graph nodes statefully until stopping criteria or budget exhaustion.
    """
    start_time = time.time()
    budget_exhausted = False

    # Node 1: Claim Decomposition
    state = await decomposition_node(state, deps, emit)

    # Iterative execution loop over pending sub-agent tasks
    while state.iterations < state.budget_limit:
        state.iterations += 1
        pending_tasks = [t for t in state.plan.tasks if not t.completed]
        if not pending_tasks:
            break

        next_task = pending_tasks[0]
        agent_name = (next_task.agent or "").lower().strip()

        if agent_name == "evidence":
            state = await evidence_node(state, next_task, deps, emit)
        elif agent_name == "credibility":
            state = await credibility_node(state, next_task, deps, emit)
        elif agent_name == "forensics":
            state = await forensics_node(state, next_task, deps, emit)
        else:
            state.plan.mark_done(next_task.task_id)

    else:
        budget_exhausted = True
        logger.warning(f"Run {state.run_id}: Graph execution budget limit reached ({state.budget_limit} iterations)")

    # Node 2: Mandatory Adversarial Red-Team Node
    state = await adversarial_node(state, deps, emit)

    # Node 3: Report Assembly Finalizer Node
    elapsed = time.time() - start_time
    state = await finalizer_node(state, elapsed, budget_exhausted)

    return state.final_report
