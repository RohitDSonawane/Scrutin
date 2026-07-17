from __future__ import annotations
import asyncio
import time
import uuid
from loguru import logger
from app.protocols.blackboard import Blackboard
from app.protocols.messages import Plan, Finding, VerificationReport
from app.orchestrator import planner, evaluator

# Import all agents
from app.agents.decomposition_agent import decomposition_agent
from app.agents.evidence_agent import evidence_agent
from app.agents.credibility_agent import credibility_agent
from app.agents.forensics_agent import forensics_agent
from app.agents.adversarial_agent import adversarial_agent
from app.agents.base import AgentDeps

AGENT_MAP = {
    "decomposition": decomposition_agent,
    "evidence": evidence_agent,
    "credibility": credibility_agent,
    "forensics": forensics_agent,
    "adversarial": adversarial_agent,
}


async def run_orchestrator(
    raw_input: str,
    input_type: str = "text",
    config: dict | None = None,
    db_path: str = "scrutin.db",
    run_id: str | None = None,
) -> VerificationReport:
    """
    The main orchestration loop. Plain while loop — no graph DSL.
    Plan → Act → Observe → Reflect → (Replan | Stop)
    """
    import sqlite3
    from app.memory.episodic import record_run

    config = config or {}
    run_id = run_id or str(uuid.uuid4())[:8]
    start_time = time.time()

    log = logger.bind(agent="orchestrator")
    log.info(f"Run started: {run_id} | input_type={input_type}")

    # Initialize Blackboard
    bb = Blackboard(run_id=run_id, raw_input=raw_input, input_type=input_type)
    bb.plan = planner.initial_plan(bb)

    deps = AgentDeps(blackboard=bb, config=config)
    budget_exhausted = False

    try:
        while bb.budget_remaining():
            bb.iterations += 1
            next_t = bb.plan.next_task()

            if next_t is None:
                log.info(f"Iteration {bb.iterations}: No more tasks — running evaluator")
                # Evaluate stopping criteria
                bb_summary = _summarize_blackboard(bb)
                ev, score = await evaluator.evaluate(bb_summary)
                log.info(f"Evaluator score: {score:.2f} (threshold: {evaluator.STOPPING_THRESHOLD})")

                if score >= evaluator.STOPPING_THRESHOLD:
                    log.info("Stopping criteria met ✓")
                    break

                # Not satisfied — reflect and replan
                log.info("Stopping criteria NOT met — reflecting and replanning")
                reflection = await evaluator.reflect(bb_summary, ev)
                log.bind(agent="reflection").info(f"Root cause: {reflection.root_cause}")
                bb.plan = planner.replan(bb, ev, reflection)
                continue

            # Gather all pending tasks in the same group (if group exists)
            if next_t.parallel_group is not None:
                tasks_to_run = [
                    t for t in bb.plan.tasks 
                    if not t.completed and t.parallel_group == next_t.parallel_group
                ]
            else:
                tasks_to_run = [next_t]

            # Define execution wrapper for each task
            async def run_single_task(t):
                log.info(f"Iteration {bb.iterations}: Running {t.agent} on claim '{t.claim_id}'")
                agent = AGENT_MAP.get(t.agent)
                if not agent:
                    log.error(f"Unknown agent: {t.agent}")
                    bb.plan.mark_done(t.task_id)
                    return

                if t.agent == "adversarial":
                    user_msg = _build_adversarial_prompt(bb)
                else:
                    user_msg = _build_agent_prompt(t, bb)

                try:
                    # Enforce Groq rate limit throttling
                    if t.agent in ("decomposition", "credibility", "adversarial"):
                        from app.agents.base import groq_acquire
                        await groq_acquire()

                    result = await agent.run(user_msg, deps=deps)
                    finding = result.output

                    if isinstance(finding, Finding):
                        bb.append_finding(finding)
                        log.bind(agent=t.agent).info(
                            f"Finding: stance={finding.stance}, confidence={finding.confidence:.2f}"
                        )
                        # Update provisional verdict
                        bb.provisional_verdict = _derive_provisional_verdict(bb)

                    elif hasattr(finding, "claims"):
                        # DecompositionOutput — populate atomic_claims
                        for c in finding.claims:
                            bb.atomic_claims[c["claim_id"]] = c["claim_text"]
                        log.bind(agent="decomposition").info(
                            f"Decomposed → {len(finding.claims)} claims"
                        )
                except Exception as e:
                    log.error(f"Agent {t.agent} failed: {e}")

                bb.plan.mark_done(t.task_id)

            # Gather and execute tasks concurrently
            await asyncio.gather(*(run_single_task(t) for t in tasks_to_run))

        else:
            budget_exhausted = True
            log.warning(f"Budget exhausted at {bb.iterations} iterations — forcing inconclusive")

    finally:
        # ALWAYS flush to SQLite — even on crash (architecture §5.3)
        elapsed = time.time() - start_time
        report = _build_final_report(bb, elapsed, budget_exhausted)
        bb.final_report = report.model_dump()

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        bb.flush_to_sqlite(conn)
        conn.close()

        log.info(f"Run complete: {run_id} | verdict={report.overall_verdict} | time={elapsed:.1f}s")

    return report


def _summarize_blackboard(bb: Blackboard) -> str:
    """Compact Blackboard summary for evaluator and reflection agents."""
    lines = [
        f"Claims: {bb.atomic_claims}",
        f"Findings ({len(bb.findings)}):",
    ]
    for f in bb.findings[-5:]:  # Last 5 findings only — context budget
        lines.append(f"  [{f['agent']}] {f['claim_id']}: {f['stance']} ({f['confidence']:.2f})")
    lines.append(f"Provisional verdict: {bb.provisional_verdict}")
    lines.append(f"Evidence store keys: {list(bb.evidence_store.keys())}")
    return "\n".join(lines)


def _build_agent_prompt(task, bb: Blackboard) -> str:
    claim_text = bb.atomic_claims.get(task.claim_id, bb.raw_input)
    return f"Claim to verify: {claim_text}\nParams: {task.params}"


def _build_adversarial_prompt(bb: Blackboard) -> str:
    """Adversarial agent gets ONLY raw evidence IDs + snippets + provisional verdict."""
    evidence_summary = []
    for eid, data in list(bb.evidence_store.items())[:10]:
        snippet = str(data.get("snippet", ""))[:200]
        url = data.get("url", "")
        evidence_summary.append(f"[{eid}] {url}: {snippet}")
    return (
        f"Provisional verdict: {bb.provisional_verdict}\n\n"
        f"Raw evidence:\n" + "\n".join(evidence_summary)
    )


def _derive_provisional_verdict(bb: Blackboard) -> str:
    """Simple majority-stance heuristic for provisional verdict."""
    if not bb.findings:
        return "inconclusive"
    stances = [f["stance"] for f in bb.findings]
    if stances.count("contradicts") > stances.count("supports"):
        return "false"
    elif stances.count("supports") > stances.count("contradicts"):
        return "true"
    elif "mixed" in stances:
        return "misleading"
    return "inconclusive"


def _build_final_report(bb: Blackboard, elapsed: float, budget_exhausted: bool) -> VerificationReport:
    from app.protocols.messages import EvidenceItem
    adversarial_summary = ""
    for f in bb.findings:
        if f["agent"] == "adversarial":
            adversarial_summary = f.get("rationale", "")

    avg_confidence = (
        sum(f["confidence"] for f in bb.findings) / len(bb.findings)
        if bb.findings else 0.0
    )
    verdict = bb.provisional_verdict or "inconclusive"
    score_map = {"true": 85.0, "false": 12.0, "misleading": 40.0,
                 "unverifiable": 50.0, "inconclusive": 50.0}

    return VerificationReport(
        run_id=bb.run_id,
        raw_input=bb.raw_input,
        overall_verdict=verdict,
        credibility_score=score_map.get(verdict, 50.0),
        confidence=round(avg_confidence, 2),
        claim_findings=bb.findings,
        adversarial_summary=adversarial_summary or "No adversarial critique produced.",
        evidence_used=[EvidenceItem(
            source_id=k,
            url=str(v.get("url", "")),
            snippet=str(v.get("snippet", ""))[:300],
            source_domain=str(v.get("source_domain", "")),
            relevance_score=float(v.get("relevance", 0.0)),
            retrieval_backend=str(v.get("backend_used", "unknown")),
        ) for k, v in bb.evidence_store.items()],
        source_credibility_notes="",
        processing_time_seconds=round(elapsed, 2),
        iterations_used=bb.iterations,
        budget_exhausted=budget_exhausted,
    )
