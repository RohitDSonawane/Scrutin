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

    # ── Episodic fast-path: check for similar past claims ──────────────────────
    from app.memory.semantic import search_similar_claims
    from app.memory.episodic import find_similar_run

    similar = await search_similar_claims(raw_input, config)
    if not similar:
        sqlite_similar = await find_similar_run(raw_input, db_path=db_path)
        if sqlite_similar:
            similar = [{
                "claim_id": sqlite_similar[0]["run_id"],
                "run_id": sqlite_similar[0]["run_id"],
                "verdict": sqlite_similar[0]["overall_verdict"],
                "score": 0.97,
                "text": sqlite_similar[0]["raw_input"],
            }]

    if similar:
        top = similar[0]
        if top["score"] >= 0.95:
            log.info(f"Episodic fast-path hit: score={top['score']:.3f} → verdict={top['verdict']}")
            bb.provisional_verdict = top["verdict"]
            import sqlite3
            import json
            from app.protocols.messages import VerificationReport
            try:
                conn = sqlite3.connect(db_path, timeout=30.0)
                row = conn.execute(
                    "SELECT data_json FROM episodic_runs WHERE run_id=?",
                    (top["run_id"],)
                ).fetchone()
                conn.close()
                if row:
                    data = json.loads(row[0])
                    cached_report_dict = data.get("final_report")
                    if cached_report_dict:
                        report = VerificationReport.model_validate(cached_report_dict)
                        report.run_id = run_id
                        report.processing_time_seconds = round(time.time() - start_time, 2)
                        bb.final_report = report.model_dump()
                        
                        def _sync_write_fast():
                            conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
                            try:
                                conn.execute("BEGIN IMMEDIATE")
                                bb.flush_to_sqlite(conn)
                                conn.execute("COMMIT")
                            except Exception as write_err:
                                try:
                                    conn.execute("ROLLBACK")
                                except Exception:
                                    pass
                                raise write_err
                            finally:
                                conn.close()

                        await asyncio.to_thread(_sync_write_fast)

                        try:
                            from app.memory.episodic import record_run
                            await record_run(
                                run_id=run_id,
                                raw_input=raw_input,
                                input_type=input_type,
                                overall_verdict=report.overall_verdict,
                                credibility_score=report.credibility_score,
                                confidence=report.confidence,
                                data_json=bb.model_dump_json(),
                                iterations_used=bb.iterations,
                                budget_exhausted=False,
                                processing_time_seconds=report.processing_time_seconds,
                                db_path=db_path,
                            )
                        except Exception as rec_err:
                            log.error(f"Failed to record fast-path run: {rec_err}")

                        return report
            except Exception as e:
                log.error(f"Failed to load cached run report: {e}. Falling back to standard execution.")

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
                
                old_task_count = len(bb.plan.tasks)
                bb.plan = planner.replan(bb, ev, reflection)
                if len(bb.plan.tasks) == old_task_count:
                    log.warning("Replan did not add any new tasks — stopping to prevent infinite loop")
                    break
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
                    # Enforce rate limit throttling
                    if t.agent in ("decomposition", "credibility", "adversarial"):
                        from app.utils.rate_limiter import groq_acquire
                        await groq_acquire()
                    elif t.agent in ("evidence", "forensics"):
                        from app.utils.rate_limiter import gemini_acquire
                        await gemini_acquire()

                    result = await agent.run(user_msg, deps=deps)
                    finding = result.output

                    from app.protocols.messages import AdversarialCritique

                    if isinstance(finding, Finding):
                        finding.agent = t.agent
                        finding.claim_id = t.claim_id
                        bb.append_finding(finding)
                        log.bind(agent=t.agent).info(
                            f"Finding: stance={finding.stance}, confidence={finding.confidence:.2f}"
                        )
                        # Update provisional verdict
                        bb.provisional_verdict = _derive_provisional_verdict(bb)

                    elif isinstance(finding, AdversarialCritique):
                        # Convert to Finding so blackboard stores it
                        adv_finding = Finding(
                            agent=t.agent,
                            claim_id=t.claim_id,
                            stance="supports" if finding.verdict_stands else "contradicts",
                            confidence=1.0,
                            rationale=finding.strongest_counter,
                            requests=[],
                        )
                        bb.append_finding(adv_finding)
                        if finding.verdict_stands:
                            log.bind(agent="adversarial").info("verdict_stands=True ✓")
                        else:
                            log.bind(agent="adversarial").warning(
                                f"verdict_stands=False → '{finding.strongest_counter[:80]}...'"
                            )

                    elif hasattr(finding, "claims"):
                        # DecompositionOutput — populate atomic_claims
                        for c in finding.claims:
                            claim_id = str(c.claim_id if hasattr(c, "claim_id") else c.get("claim_id"))
                            claim_text = str(c.claim_text if hasattr(c, "claim_text") else c.get("claim_text"))
                            bb.atomic_claims[claim_id] = claim_text
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

        # Wire orchestrator_agent for final synthesis (LLM call, not heuristic)
        from app.agents.orchestrator_agent import orchestrator_agent
        try:
            bb_summary = _summarize_blackboard(bb)
            prompt = (
                f"Please synthesize the final verification report for the claim: '{bb.raw_input}'\n\n"
                f"Blackboard state summary:\n{bb_summary}\n\n"
                f"Provide the complete VerificationReport JSON matching the schema."
            )
            from app.utils.rate_limiter import gemini_acquire
            await gemini_acquire()
            res = await orchestrator_agent.run(prompt, deps=deps)
            report = res.output
            # Ensure Python-controlled metadata fields are set correctly
            report.processing_time_seconds = round(elapsed, 2)
            report.iterations_used = bb.iterations
            report.budget_exhausted = budget_exhausted
            report.run_id = bb.run_id
            report.raw_input = bb.raw_input
            if not report.evidence_used:
                from app.protocols.messages import EvidenceItem
                report.evidence_used = [EvidenceItem(
                    source_id=k,
                    url=str(v.get("url", "")),
                    snippet=str(v.get("snippet", ""))[:300],
                    source_domain=str(v.get("source_domain", "")),
                    relevance_score=float(v.get("relevance", 0.0)),
                    retrieval_backend=str(v.get("backend_used", "unknown")),
                ) for k, v in bb.evidence_store.items()]
        except Exception as synth_err:
            log.error(f"Failed orchestrator_agent final synthesis: {synth_err}. Falling back to heuristic.")
            report = _build_final_report(bb, elapsed, budget_exhausted)

        bb.final_report = report.model_dump()

        # ── Commit reputation updates proposed by credibility agent ────────────────
        try:
            from app.memory.longterm import propose_reputation_update
            for finding in bb.findings:
                if finding.get("agent") == "credibility":
                    for eid in finding.get("evidence_ids", []):
                        ev_data = bb.evidence_store.get(eid, {})
                        domain = ev_data.get("source_domain", "")
                        if domain:
                            check_failed = (report.overall_verdict in ("false", "misleading"))
                            result = await propose_reputation_update(domain, check_failed, db_path)
                            if result["committed"]:
                                log.bind(agent="orchestrator").info(
                                    f"Reputation updated: {domain} → {result['new_score']:.0f}"
                                )
        except Exception as rep_err:
            log.error(f"Reputation commitment failed: {rep_err}")

        # ── Upsert verified claims into Pinecone ───────────────────────────────────
        try:
            from app.memory.semantic import upsert_claim
            for claim_id, claim_text in bb.atomic_claims.items():
                await upsert_claim(claim_id, claim_text, bb.run_id, report.overall_verdict, config, db_path)
        except Exception as sem_err:
            log.error(f"Claim semantic upsert failed: {sem_err}")

        # Write #1: Raw Blackboard audit trail (synchronous connection offloaded to thread to prevent event-loop blocking)
        def _sync_write_final():
            conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("BEGIN IMMEDIATE")
                bb.flush_to_sqlite(conn)
                conn.execute("COMMIT")
            except Exception as write_err:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise write_err
            finally:
                conn.close()

        await asyncio.to_thread(_sync_write_final)

        # Write #2: Structured fields for analytics (asynchronous connection)
        try:
            await record_run(
                run_id=bb.run_id,
                raw_input=bb.raw_input,
                input_type=bb.input_type,
                overall_verdict=report.overall_verdict,
                credibility_score=report.credibility_score,
                confidence=report.confidence,
                data_json=bb.model_dump_json(),
                iterations_used=bb.iterations,
                budget_exhausted=budget_exhausted,
                processing_time_seconds=elapsed,
                db_path=db_path,
            )
        except Exception as db_err:
            log.error(f"Failed to record structured episodic run: {db_err}")

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
