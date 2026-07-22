from __future__ import annotations
import uuid
from app.protocols.blackboard import Blackboard
from app.protocols.messages import Plan, Task


def initial_plan(blackboard: Blackboard) -> Plan:
    """
    Build the initial task plan based on input type.
    Always starts with decomposition. Forensics only queued if input is not plain text.
    Evidence and Credibility are in the SAME parallel_group=1 — gathered concurrently.
    Adversarial is always a solo task (needs provisional verdict first).
    """
    tasks: list[Task] = []
    cid = "C0"  # Placeholder — real claim IDs assigned after decomposition

    # Step 1: Claim decomposition (always first, solo)
    tasks.append(Task(
        task_id="T1",
        agent="decomposition",
        claim_id=cid,
        params={"raw_input": blackboard.raw_input},
        parallel_group=None,
    ))

    # Step 2+3: Evidence + Credibility run in PARALLEL (no data dependency)
    tasks.append(Task(
        task_id="T2",
        agent="evidence",
        claim_id=cid,
        params={"mode": "factcheck_first"},
        parallel_group=1,    # gather group 1
    ))
    tasks.append(Task(
        task_id="T3",
        agent="credibility",
        claim_id=cid,
        parallel_group=1,    # gather group 1 — runs concurrently with evidence
    ))

    # Step 4: Forensics (only if media input, solo)
    if blackboard.input_type in ("image", "video"):
        tasks.append(Task(
            task_id="T4",
            agent="forensics",
            claim_id=cid,
            params={"input_type": blackboard.input_type},
            parallel_group=None,
        ))

    # Step 5: Adversarial (always last — needs provisional verdict)
    tasks.append(Task(
        task_id="T5",
        agent="adversarial",
        claim_id=cid,
        parallel_group=None,
    ))

    return Plan(tasks=tasks)


def replan(blackboard: Blackboard, critique: "EvidenceEvaluation", reflection: "AgentReflection") -> Plan:
    """
    Mutable replan step called when stopping criteria are NOT met.
    Adds targeted follow-up tasks based on what the evaluator flagged.
    Preserves completed tasks and only appends new ones.
    """
    plan = blackboard.plan
    new_task_idx = sum(1 for t in plan.tasks) + 1

    if not critique.sources_are_independent:
        # Evidence agent needs to find independent sources
        plan.tasks.append(Task(
            task_id=f"T{new_task_idx}",
            agent="evidence",
            claim_id="C_retry",
            params={
                "mode": "retry",
                "reason": reflection.correction,
                "query_modifier": "independent primary sources NOT wire service",
            },
            retry_reason=reflection.root_cause,
        ))
        new_task_idx += 1

    if not critique.adversarial_critique_addressed:
        # Re-run adversarial with explicit note to check the unexamined angle
        plan.tasks.append(Task(
            task_id=f"T{new_task_idx}",
            agent="adversarial",
            claim_id="C_retry",
            params={"mode": "retry", "reason": "previous critique not addressed"},
        ))
        new_task_idx += 1

    # Adversarial always goes last — reorder if needed
    _ensure_adversarial_is_last(plan)
    return plan


def _ensure_adversarial_is_last(plan: Plan) -> None:
    """Re-order so adversarial tasks are always the final pending task."""
    pending_adversarial = [t for t in plan.tasks if not t.completed and t.agent == "adversarial"]
    others = [t for t in plan.tasks if t not in pending_adversarial]
    plan.tasks = others + pending_adversarial
