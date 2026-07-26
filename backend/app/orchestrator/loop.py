from __future__ import annotations
import asyncio
import json
import sqlite3
import time
import uuid
from typing import Any, Callable, Optional

from loguru import logger
from app.protocols.blackboard import Blackboard
from app.protocols.messages import (
    Plan, Finding, Task, VerificationReport, EvidenceItem, AdversarialCritique
)
from app.orchestrator import planner
from app.agents.decomposition_agent import decomposition_agent
from app.agents.evidence_agent import evidence_agent
from app.agents.credibility_agent import credibility_agent
from app.agents.forensics_agent import forensics_agent
from app.agents.adversarial_agent import adversarial_agent
from app.agents.orchestrator_agent import orchestrator_agent
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
    on_event: Optional[Callable[[str, dict], Any]] = None,
) -> VerificationReport:
    """
    LLM-Authoritative orchestration loop for Scrutin.
    Orchestrator LLM decides dynamic task delegation and final sufficiency.
    """
    from app.memory.episodic import record_run

    config = config or {}
    run_id = run_id or str(uuid.uuid4())[:8]
    start_time = time.time()

    async def emit(event_type: str, data: dict):
        if on_event:
            try:
                res = on_event(event_type, data)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

    log = logger.bind(agent="orchestrator")
    log.info(f"Run started: {run_id} | input_type={input_type}")
    await emit("start", {"run_id": run_id, "raw_input": raw_input, "input_type": input_type})

    bb = Blackboard(run_id=run_id, raw_input=raw_input, input_type=input_type)
    bb.plan = planner.bootstrap_plan(bb)
    await emit("plan", {"iteration": 0, "tasks": [t.model_dump() for t in bb.plan.tasks]})

    deps = AgentDeps(blackboard=bb, config=config)
    budget_exhausted = False

    # ── Fast-path episodic cache lookup ────────────────────────────────────────
    cached_report = await _check_episodic_cache(raw_input, input_type, run_id, db_path, config, start_time, bb, emit, log)
    if cached_report:
        return cached_report

    final_report: Optional[VerificationReport] = None

    try:
        while bb.budget_remaining():
            bb.iterations += 1

            # Step A: Run any pending tasks on Blackboard plan
            pending_tasks = [t for t in bb.plan.tasks if not t.completed]
            if pending_tasks:
                next_t = pending_tasks[0]
                tasks_to_run = (
                    [t for t in pending_tasks if t.parallel_group == next_t.parallel_group]
                    if next_t.parallel_group is not None else [next_t]
                )
                await asyncio.gather(*(
                    _execute_single_task(t, bb, deps, emit, log) for t in tasks_to_run
                ))
                continue

            # Step B: All tasks complete — query Orchestrator LLM for next decision
            bb_summary = _summarize_blackboard(bb)
            prompt = f"Iteration {bb.iterations}/{bb.budget_limit}.\n\n{bb_summary}"

            from app.utils.rate_limiter import groq_acquire
            await groq_acquire()

            try:
                res = await orchestrator_agent.run(prompt, deps=deps)
                decision = res.output
            except Exception as orch_err:
                log.error(f"Orchestrator decision query failed: {orch_err}. Forcing fallback.")
                break

            if decision.action == "finalize" and decision.finalize and decision.finalize.report:
                # Python Safety Guardrail: Verify Adversarial pass executed
                has_adv = any(t.agent == "adversarial" and t.completed for t in bb.plan.tasks)
                if not has_adv:
                    log.warning("Orchestrator attempted finalize before Adversarial pass — forcing Adversarial task")
                    bb.plan.tasks.append(Task(
                        task_id=f"T_adv_{bb.iterations}",
                        agent="adversarial",
                        claim_id="C0",
                        parallel_group=None,
                    ))
                    await emit("orchestrator_decision", {
                        "action": "delegate",
                        "reasoning": "Python guardrail: Adversarial red-team pass required before finalize."
                    })
                    continue

                log.bind(agent="orchestrator").info(f"Finalizing run: {decision.finalize.reasoning}")
                await emit("orchestrator_decision", {
                    "action": "finalize",
                    "reasoning": decision.finalize.reasoning
                })
                final_report = decision.finalize.report
                break
            elif decision.action == "delegate" and decision.delegate and decision.delegate.tasks:
                log.bind(agent="orchestrator").info(f"Delegating next tasks: {decision.delegate.reasoning}")
                for new_task in decision.delegate.tasks:
                    bb.plan.tasks.append(new_task)
                await emit("orchestrator_decision", {
                    "action": "delegate",
                    "reasoning": decision.delegate.reasoning,
                    "tasks": [t.model_dump() for t in decision.delegate.tasks]
                })
                continue
            else:
                log.warning("Orchestrator returned empty decision — stopping loop")
                break
        else:
            budget_exhausted = True
            log.warning(f"Budget exhausted at {bb.iterations} iterations — forcing stop")

    finally:
        elapsed = time.time() - start_time
        is_fallback = False

        if final_report is not None:
            report = final_report
        else:
            log.info("No LLM finalize report produced — building fallback heuristic report")
            report = _build_final_report(bb, elapsed, budget_exhausted)
            is_fallback = True

        report.processing_time_seconds = round(elapsed, 2)
        report.iterations_used = bb.iterations
        report.budget_exhausted = budget_exhausted
        report.run_id = bb.run_id
        report.raw_input = bb.raw_input
        if not report.evidence_used:
            report.evidence_used = [EvidenceItem(
                source_id=k,
                url=str(v.get("url", "")),
                snippet=str(v.get("snippet", ""))[:300],
                source_domain=str(v.get("source_domain", "")),
                relevance_score=float(v.get("relevance", 0.0)),
                retrieval_backend=str(v.get("backend_used", "unknown")),
            ) for k, v in bb.evidence_store.items()]

        bb.final_report = report.model_dump()

        # Commit reputation updates and Pinecone embeddings
        await _commit_memory_and_reputation(bb, report, is_fallback, config, db_path, log)

        # Flush Blackboard audit trail & record run in SQLite
        await _flush_run_persistence(bb, report, elapsed, budget_exhausted, is_fallback, db_path, emit, log)

    return report


async def _execute_single_task(t: Task, bb: Blackboard, deps: AgentDeps, emit: Callable, log: Any) -> None:
    """Execute a single sub-agent task with rate-limiting and Blackboard update."""
    log.info(f"Iteration {bb.iterations}: Running {t.agent} on claim '{t.claim_id}'")
    await emit("agent_start", {"agent": t.agent, "claim_id": t.claim_id, "task_id": t.task_id, "iteration": bb.iterations})
    
    agent = AGENT_MAP.get(t.agent)
    if not agent:
        log.error(f"Unknown agent: {t.agent}")
        bb.plan.mark_done(t.task_id)
        return

    user_msg = _build_adversarial_prompt(bb) if t.agent == "adversarial" else _build_agent_prompt(t, bb)

    try:
        if t.agent in ("decomposition", "credibility", "adversarial"):
            from app.utils.rate_limiter import groq_acquire
            await groq_acquire()
        elif t.agent in ("evidence", "forensics"):
            from app.utils.rate_limiter import gemini_acquire
            await gemini_acquire()

        result = await agent.run(user_msg, deps=deps)
        finding = result.output

        if isinstance(finding, Finding):
            finding.agent = t.agent
            finding.claim_id = t.claim_id
            bb.append_finding(finding)
            log.bind(agent=t.agent).info(f"Finding: stance={finding.stance}, confidence={finding.confidence:.2f}")
            bb.provisional_verdict = _derive_provisional_verdict(bb)
            await emit("finding", {
                "agent": t.agent, "claim_id": t.claim_id, "stance": finding.stance,
                "confidence": finding.confidence, "rationale": finding.rationale,
            })
            await emit("provisional_verdict", {"verdict": bb.provisional_verdict})

        elif isinstance(finding, AdversarialCritique):
            adv_finding = Finding(
                agent=t.agent, claim_id=t.claim_id,
                stance="supports" if finding.verdict_stands else "contradicts",
                confidence=1.0, rationale=finding.strongest_counter, requests=[],
            )
            bb.append_finding(adv_finding)
            await emit("finding", {
                "agent": "adversarial", "claim_id": t.claim_id,
                "stance": adv_finding.stance, "confidence": 1.0, "rationale": finding.strongest_counter,
            })

        elif hasattr(finding, "claims"):
            for c in finding.claims:
                cid = str(c.claim_id if hasattr(c, "claim_id") else c.get("claim_id"))
                ctext = str(c.claim_text if hasattr(c, "claim_text") else c.get("claim_text"))
                bb.atomic_claims[cid] = ctext
            log.bind(agent="decomposition").info(f"Decomposed → {len(finding.claims)} claims")
            await emit("decomposition", {
                "claims": [{"claim_id": k, "claim_text": v} for k, v in bb.atomic_claims.items()]
            })
    except Exception as e:
        log.error(f"Agent {t.agent} failed: {e}")

    bb.plan.mark_done(t.task_id)


async def _check_episodic_cache(
    raw_input: str, input_type: str, run_id: str, db_path: str, config: dict,
    start_time: float, bb: Blackboard, emit: Callable, log: Any
) -> Optional[VerificationReport]:
    """Check fast-path cache for exact or high-similarity previously verified claims."""
    from app.memory.semantic import search_similar_claims
    from app.memory.episodic import find_similar_run, record_run

    similar = await search_similar_claims(raw_input, config)
    if not similar:
        sqlite_similar = await find_similar_run(raw_input, db_path=db_path)
        if sqlite_similar:
            is_exact = sqlite_similar[0]["raw_input"].lower().strip() == raw_input.lower().strip()
            similar = [{
                "claim_id": sqlite_similar[0]["run_id"],
                "run_id": sqlite_similar[0]["run_id"],
                "verdict": sqlite_similar[0]["overall_verdict"],
                "score": 1.0 if is_exact else 0.8,
                "text": sqlite_similar[0]["raw_input"],
            }]

    if similar:
        top = similar[0]
        if top["score"] >= 0.95 and (top.get("text") or "").lower().strip() == raw_input.lower().strip():
            log.info(f"Episodic fast-path hit: score={top['score']:.3f} → verdict={top['verdict']}")
            try:
                with sqlite3.connect(db_path, timeout=30.0) as conn:
                    row = conn.execute("SELECT data_json FROM episodic_runs WHERE run_id=?", (top["run_id"],)).fetchone()
                if row and row[0]:
                    cached_dict = json.loads(row[0]).get("final_report")
                    if cached_dict:
                        report = VerificationReport.model_validate(cached_dict)
                        report.run_id = run_id
                        report.processing_time_seconds = round(time.time() - start_time, 2)
                        bb.final_report = report.model_dump()
                        
                        await asyncio.to_thread(lambda: sqlite3.connect(db_path, timeout=30.0).execute("PRAGMA journal_mode=WAL"))
                        await record_run(
                            run_id=run_id, raw_input=raw_input, input_type=input_type,
                            overall_verdict=report.overall_verdict, credibility_score=report.credibility_score,
                            confidence=report.confidence, data_json=bb.model_dump_json(),
                            iterations_used=bb.iterations, budget_exhausted=False,
                            processing_time_seconds=report.processing_time_seconds, db_path=db_path,
                        )
                        return report
            except Exception as e:
                log.error(f"Cached run load failed: {e}. Running full pipeline.")
    return None


async def _commit_memory_and_reputation(bb: Blackboard, report: VerificationReport, is_fallback: bool, config: dict, db_path: str, log: Any) -> None:
    """Commit source reputation updates and Pinecone vector embeddings."""
    try:
        from app.memory.longterm import propose_reputation_update
        for finding in bb.findings:
            if finding.get("agent") == "credibility":
                for eid in finding.get("evidence_ids", []):
                    domain = bb.evidence_store.get(eid, {}).get("source_domain", "")
                    if domain:
                        check_failed = (report.overall_verdict in ("false", "misleading"))
                        res = await propose_reputation_update(domain, check_failed, db_path)
                        if res["committed"]:
                            log.bind(agent="orchestrator").info(f"Reputation updated: {domain} → {res['new_score']:.0f}")
    except Exception as e:
        log.error(f"Reputation commitment failed: {e}")

    if not is_fallback:
        try:
            from app.memory.semantic import upsert_claim
            for claim_id, claim_text in bb.atomic_claims.items():
                await upsert_claim(claim_id, claim_text, bb.run_id, report.overall_verdict, config, db_path)
        except Exception as sem_err:
            log.error(f"Claim semantic upsert failed: {sem_err}")


async def _flush_run_persistence(bb: Blackboard, report: VerificationReport, elapsed: float, budget_exhausted: bool, is_fallback: bool, db_path: str, emit: Callable, log: Any) -> None:
    """Flush Blackboard state to SQLite audit trail and record episodic run entry."""
    def _sync_write():
        with sqlite3.connect(db_path, timeout=30.0, isolation_level=None) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("BEGIN IMMEDIATE")
            bb.flush_to_sqlite(conn)
            conn.execute("COMMIT")

    await asyncio.to_thread(_sync_write)

    if not is_fallback:
        try:
            from app.memory.episodic import record_run
            await record_run(
                run_id=bb.run_id, raw_input=bb.raw_input, input_type=bb.input_type,
                overall_verdict=report.overall_verdict, credibility_score=report.credibility_score,
                confidence=report.confidence, data_json=bb.model_dump_json(),
                iterations_used=bb.iterations, budget_exhausted=budget_exhausted,
                processing_time_seconds=elapsed, db_path=db_path,
            )
        except Exception as db_err:
            log.error(f"Episodic record failed: {db_err}")

    log.info(f"Run complete: {bb.run_id} | verdict={report.overall_verdict} | time={elapsed:.1f}s")
    await emit("final_report", {"report": report.model_dump()})
    await emit("complete", {"run_id": bb.run_id, "processing_time_seconds": round(elapsed, 2)})


def _summarize_blackboard(bb: Blackboard) -> str:
    """Compact Blackboard summary for Orchestrator LLM context."""
    lines = [f"Claims: {bb.atomic_claims}", f"Findings ({len(bb.findings)}):"]
    for f in bb.findings[-5:]:
        lines.append(f"  [{f['agent']}] {f['claim_id']}: {f['stance']} ({f['confidence']:.2f})")
    lines.append(f"Provisional verdict: {bb.provisional_verdict}")
    lines.append(f"Evidence store keys: {list(bb.evidence_store.keys())}")
    return "\n".join(lines)


def _build_agent_prompt(task: Task, bb: Blackboard) -> str:
    claim_text = bb.atomic_claims.get(task.claim_id, bb.raw_input)
    return f"Claim to verify: {claim_text}\nParams: {task.params}"


def _build_adversarial_prompt(bb: Blackboard) -> str:
    """Adversarial agent receives ONLY raw evidence IDs/snippets + provisional verdict."""
    evidence_summary = [
        f"[{eid}] {data.get('url', '')}: {str(data.get('snippet', ''))[:200]}"
        for eid, data in list(bb.evidence_store.items())[:10]
    ]
    return f"Provisional verdict: {bb.provisional_verdict}\n\nRaw evidence:\n" + "\n".join(evidence_summary)


def _derive_provisional_verdict(bb: Blackboard) -> str:
    """Simple majority-stance heuristic for provisional verdict. Excludes credibility findings."""
    content_findings = [f for f in bb.findings if f.get("agent") != "credibility"]
    if not content_findings:
        return "inconclusive"
    stances = [f["stance"] for f in content_findings]
    if stances.count("contradicts") > stances.count("supports"):
        return "false"
    elif stances.count("supports") > stances.count("contradicts"):
        return "true"
    elif "mixed" in stances:
        return "misleading"
    return "inconclusive"


def _build_final_report(bb: Blackboard, elapsed: float, budget_exhausted: bool) -> VerificationReport:
    """Build fallback heuristic VerificationReport if Orchestrator LLM finalize fails."""
    adv_summary = next((f.get("rationale", "") for f in bb.findings if f.get("agent") == "adversarial"), "")
    avg_confidence = sum(f["confidence"] for f in bb.findings) / len(bb.findings) if bb.findings else 0.0
    verdict = "inconclusive"  # Fallback runs MUST default to inconclusive

    return VerificationReport(
        run_id=bb.run_id,
        raw_input=bb.raw_input,
        overall_verdict=verdict,
        credibility_score=50.0,
        confidence=round(avg_confidence, 2),
        claim_findings=bb.findings,
        adversarial_summary=adv_summary or "No adversarial critique produced.",
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
