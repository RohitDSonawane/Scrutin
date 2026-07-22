# Claim Verification Platform — Architecture from First Principles

## 0. How to read this document
This is a design, not a pitch. Every agent that appears below had to earn its place by passing a test: *does giving this responsibility its own reasoning loop and memory actually change the outcome, or am I just decorating a function call as an "agent"?* Anything that failed that test was demoted to a tool.

---

## 1. Does this problem actually need multi-agent architecture?

Work through the options honestly before reaching for the fashionable one.

**Single LLM call.** Fails immediately. The input space (text, URL, image, video, audio) requires different perception pipelines before any reasoning happens, and a single prompt cannot hold "decompose this claim," "judge this source," "detect this deepfake," and "weigh contradictory evidence" in one coherent context without one task's assumptions leaking into another (e.g., the model becoming anchored on the first evidence it retrieves and rationalizing around it).

**Fixed workflow (deterministic pipeline).** This is the honest baseline and it's tempting: fetch → extract claims → search → score → output. It's cheap, predictable, and easy to debug. It fails on this problem for a specific reason: **the number of retrieval and verification steps needed is not knowable in advance.** A single-sentence claim from a known-reliable outlet might need one search. A manipulated video with an out-of-context caption might need reverse image search, frame-level forensic analysis, a transcript check against the visual claim, and three rounds of follow-up search when the first evidence is ambiguous. A fixed pipeline either over-processes the easy case (cost, latency) or under-processes the hard case (wrong verdict). That variability in *path length and path shape* is the actual signature of a problem needing an agentic loop, not a workflow.

**Hybrid (deterministic scaffolding + agentic reasoning inside it).** This is closer, and large parts of the system genuinely are this: perception/extraction (OCR, ASR, reverse image search, metadata parsing) should be **deterministic tool calls**, not agents — there is no judgment involved in transcribing audio. But the verification core — deciding what to check, how much evidence is enough, whether a source is trustworthy, whether a counter-explanation is more plausible — is irreducibly a reasoning task with branching, retries, and disagreement.

**True multi-agent.** Justified here for one specific, defensible reason, not because "multi-agent is more impressive": **verification quality depends on cognitive separation, not just task separation.** If one context window both gathers evidence for a claim and judges that evidence, it is structurally prone to confirmation bias — the same reasoning trace that found the evidence tends to also validate it. The empirically effective fix (used in real fact-checking newsrooms and in adversarial-debate LLM research) is to force **independent, non-collaborating reasoning passes** that are only reconciled at the end by a separate synthesis step. That independence is the thing a single agent, however good, structurally cannot provide to itself. That is the actual first-principles justification for multi-agent here — not "images and text are different modalities" (that's a tool problem) and not "there's a lot to do" (that's a workflow problem).

**Verdict:** hybrid-leaning-multi-agent. Deterministic tools handle perception/extraction. A small set of genuinely independent cognitive agents handle judgment, coordinated by a dynamic (non-fixed) loop rather than a fixed graph.

---

## 2. Which things are real agents, and which are just APIs wearing a costume?

Rejected as "agents" on purpose, despite being common in tutorials:
- `NewsAPIAgent`, `GoogleSearchAgent`, `ReverseImageAgent`, `WhoisAgent`, `OCRAgent`, `ASRAgent`, `DeepfakeDetectorAgent` — these are **stateless function calls with no judgment**. Wrapping an API in a class named "Agent" doesn't make it one. They are tools, registered once, called by whichever cognitive agent needs them.
- A generic "ResearchAgent" that just calls search and summarizes — this is what the Evidence agent below actually is, so it isn't duplicated.

Kept as real cognitive agents, because each requires an independent judgment loop that cannot be collapsed into another without losing the reasoning quality the system needs:

| # | Agent | Why it's real (not a wrapper) |
|---|---|---|
| 1 | **Orchestrator (Planner + Synthesizer)** | Must hold global state, decide what's still unknown, and reconcile disagreement between other agents — this is inherently a single point of integrative judgment. |
| 2 | **Claim Decomposition & Framing Agent** | Turning a paragraph, article, or video transcript into a set of atomic, independently checkable claims is a linguistic/logical reasoning task with real ambiguity (what's the falsifiable core vs. opinion vs. framing), not a parsing task. |
| 3 | **Evidence & Corroboration Agent** | Must iteratively decide *what to search next* based on what's missing, judge relevance of noisy results, and know when evidence is sufficient — an open-ended retrieval-reasoning loop, not a single API call. |
| 4 | **Source & Provenance Credibility Agent** | Judging whether a publisher, account, or domain is trustworthy requires weighing track record, ownership, incentive, and manipulation signals together — a genuinely disputable judgment call, independent from whether the claim's content sounds right. |
| 5 | **Multimodal Forensics Agent** | Synthesizing multiple weak/noisy forensic signals (ELA artifacts, metadata inconsistency, deepfake-classifier scores, audio splice indicators) into one coherent authenticity judgment is inference under uncertainty, not tool execution. |
| 6 | **Adversarial Verifier ("Red Team") Agent** | Deliberately built to disagree: its entire job is to construct the strongest plausible counter-case and alternate explanation using only the same evidence pool. This is the agent that buys the "cognitive independence" argument from Section 1 — remove it and the system quietly becomes a confirmation machine. |

Six agents. Not eight, not twelve. If a future feature request ("add TikTok support," "add PDF forensics") shows up, the answer is a new **tool**, registered with the Forensics or Evidence agent — not a new agent, unless it requires genuinely new judgment the existing agents can't be prompted to do.

---

## 3. Agent specifications

### 3.1 Orchestrator Agent
- **Goal:** Produce a final, well-calibrated verdict (credibility score, evidence, reasoning, confidence, recommendation) for the submitted item, at minimum necessary cost.
- **Responsibilities:** parse intake → run decomposition → build and update a dynamic plan (which sub-agents to invoke, in what order, whether to re-invoke) → mediate conflicting sub-agent findings → decide when enough evidence exists → write the final structured report.
- **Reasoning process:** plan → delegate → observe → reflect → (retry/delegate again | stop) loop, described in full in Section 6. Uses explicit self-critique before finalizing: "does the evidence I have actually support this score, and did I get a genuine counter-argument, not just a token one?"
- **Tools:** none directly (delegates everything); has read access to the shared **blackboard** (Section 5.3).
- **Memory:** full working memory of the current run (Section 5.1); read access to episodic memory for similar-past-claims; read/write access to long-term source-reputation memory (it's the only agent allowed to write reputation updates, to keep that store consistent).
- **Decision authority:** highest in the system — can override a sub-agent's confidence if reflection or the Adversarial agent surfaces a strong contradiction; cannot fabricate evidence itself, only reweigh what sub-agents produced.
- **Delegation rules:** always delegates decomposition first; delegates Evidence and Forensics (if multimodal) in parallel when independent; always delegates Adversarial Verifier last, after a provisional verdict exists, specifically to attack that provisional verdict.
- **Communication:** hub-and-spoke — the Orchestrator is the only agent permitted to invoke other agents; sub-agents never call each other directly (see Section 5.4 for why mesh communication is explicitly rejected).
- **Stopping criteria:** confidence threshold reached AND Adversarial agent's strongest counter-case has been explicitly addressed in the report, OR iteration/cost budget exhausted (in which case it must report the verdict as low-confidence/inconclusive rather than force a number).

### 3.2 Claim Decomposition & Framing Agent
- **Goal:** Convert raw input (text, article, transcript, caption+image pairing) into a structured set of atomic, checkable claims with type labels.
- **Responsibilities:** separate factual assertions from opinion/framing/rhetoric; classify each claim (statistical, causal, quotation, event-occurrence, image/video-authenticity, identity/attribution); flag the load-bearing claim(s) that most affect overall credibility if any part of a long article can't be fully decomposed.
- **Reasoning process:** single structured-output pass with self-check ("did I invent a claim that wasn't actually asserted?"); no external tools needed for text; for video/audio, consumes the ASR/OCR transcript already produced by tools before the agent runs.
- **Tools:** none directly — operates on text already extracted by upstream deterministic tools (ASR, OCR, transcript fetch).
- **Memory:** working memory only (this run); no long-term memory needed — decomposition isn't a skill that benefits from cross-run recall the way credibility judgments do.
- **Decision authority:** authoritative on claim structure, not on truth value.
- **Delegation rules:** none — terminal, reports back to Orchestrator only.
- **Stopping criteria:** completes in one pass; Orchestrator may re-invoke once if downstream agents report a claim was mis-scoped.

### 3.3 Evidence & Corroboration Agent
- **Goal:** For a given atomic claim, gather and evaluate independent evidence for and against it.
- **Responsibilities:** run iterative search (not one-shot); triangulate across independent sources (explicitly avoid citing three outlets that all republished one wire story as "three sources"); track evidence provenance; produce a structured finding: supporting evidence, contradicting evidence, evidence gaps, and a preliminary stance with rationale.
- **Reasoning process:** ReAct-style loop — search, read, judge relevance/independence, decide what's still missing, search again — bounded by its own sub-budget set by the Orchestrator.
- **Tools:** web search, news/wire APIs, fact-check database lookup (specifically the Google Fact Check Tools API querying ClaimReview-indexed sources for free fast-path validation), academic/primary-source search, page fetch/reader.
- **Memory:** working memory for this claim's evidence trail; read access to semantic memory (previously verified similar claims, prior fact-checks) to avoid redundant search; does not write long-term memory itself.
- **Decision authority:** authoritative on "what evidence exists," not on final credibility scoring — it hands a stance *with* evidence to the Orchestrator, it doesn't set the score.
- **Delegation rules:** can request the Source Credibility agent evaluate a specific source it's unsure about mid-search (the one case of a sub-agent triggering another, routed through the Orchestrator as a request, not a direct call — see Section 5.4).
- **Stopping criteria:** stance confidence plateaus across two consecutive searches with no new corroborating or contradicting evidence, or sub-budget exhausted → reports evidence gap explicitly rather than guessing.

### 3.4 Source & Provenance Credibility Agent
- **Goal:** Judge the trustworthiness of the originating source(s) — publisher, account, domain, or uploader.
- **Responsibilities:** assess publisher track record, ownership/funding transparency, editorial standards, prior correction/retraction history, account behavior signals (for social posts: account age, posting pattern, network signals), domain forensics (registration age, TLS/hosting anomalies).
- **Reasoning process:** structured rubric-guided judgment (not a black-box score) — must produce reasons, not just a number, because "credibility score" without rationale is exactly the kind of unaccountable output this platform exists to avoid producing.
- **Tools:** WHOIS/domain lookup, publisher-database lookup (e.g., known media-bias/fact-check registries), social-platform metadata APIs, archive/wayback lookup for retraction history.
- **Memory:** read/write access to **long-term source-reputation memory** — this agent is the primary writer of durable, cross-run credibility profiles, subject to Orchestrator confirmation before persisting (to avoid one bad run poisoning future ones).
- **Decision authority:** authoritative on source-level trust; not authoritative on content-level truth (a credible source can still be wrong about one claim, and this agent must not conflate the two).
- **Delegation rules:** none outbound.
- **Stopping criteria:** completes when it has either found a reputation record in long-term memory (fast path) or completed a fresh assessment (slow path); always reports confidence in its own assessment, since new/unknown sources are common and "unknown" is a valid, honest answer.

### 3.5 Multimodal Forensics Agent
- **Goal:** Judge whether an image, video, or audio clip is authentic, manipulated, or used out of original context.
- **Responsibilities:** synthesize outputs from forensic tools into one coherent authenticity judgment; explicitly distinguish three different failure modes that get conflated in naive systems — (a) technically manipulated media, (b) authentic media with a false caption/context, (c) authentic and correctly captioned but misleading via selective framing.
- **Reasoning process:** gathers tool outputs, weighs them (a single deepfake-classifier score is not a verdict — it corroborates or contradicts other signals), reasons explicitly about which of the three failure modes above best fits the pattern.
- **Tools:** reverse image/video search, ELA/metadata extraction, deepfake/synthetic-media classifiers, audio spectrogram/splice-detection tools, frame-extraction, geolocation-from-image tools.
- **Memory:** working memory for this run; read access to semantic memory of previously verified/debunked media (many viral fakes recirculate — a perceptual-hash match against known-debunked media is a strong, fast signal).
- **Decision authority:** authoritative on authenticity/manipulation judgment; defers claim-truth judgment (is the *caption* true) to the Evidence agent.
- **Delegation rules:** requests Evidence agent's help (via Orchestrator) when it determines the media is authentic but the surrounding claim/caption needs separate fact-checking.
- **Stopping criteria:** forensic signals converge (multiple independent tools agree) or tool budget exhausted → reports "inconclusive, technically" honestly rather than forcing a binary real/fake call, since forensic tools have real false-positive/negative rates.

### 3.6 Adversarial Verifier ("Red Team") Agent
- **Goal:** Actively try to break the Orchestrator's provisional verdict.
- **Responsibilities:** given the provisional verdict and the evidence gathered so far, construct the strongest good-faith counter-argument or alternative explanation; identify unexamined assumptions, cherry-picked evidence, or single-source over-reliance; explicitly steelman the opposite conclusion.
- **Reasoning process:** critique-focused pass over the *same* evidence pool (deliberately does not run new searches by default, to isolate reasoning failures from evidence gaps — though it may request one targeted follow-up search if it identifies a specific unexamined angle).
- **Tools:** limited, targeted search access only (used sparingly, not as a full second Evidence pass — that would just duplicate Section 3.3's job).
- **Memory:** working memory only; this agent's value comes from a fresh, uncontaminated read of the evidence, so it deliberately does *not* inherit the Evidence agent's framing/notes, only the raw evidence artifacts.
- **Decision authority:** cannot set the final score; can force the Orchestrator to lower confidence or re-open evidence gathering if it identifies a material gap.
- **Delegation rules:** none outbound except the single targeted-search exception above.
- **Stopping criteria:** produces one structured critique per invocation; Orchestrator decides whether the critique is material enough to warrant another loop iteration.

---

## 4. Why not more agents?
Two credible candidates were deliberately cut:
- **A separate "Evaluator/Judge" agent scoring the whole system's own output.** Folded into the Orchestrator's own reflection step (Section 6) instead — an LLM-as-judge rubric applied by the same agent that already holds full context is cheaper and just as effective as spinning up a seventh agent that would need the same context copied into it anyway. It's a *step*, not a role that needs independent judgment separate from synthesis.
- **A dedicated "Bias/Framing Agent"** analyzing rhetorical framing separately from claim truth. Folded into Claim Decomposition (which already separates opinion/framing from factual assertions) and the final report template (which surfaces framing notes alongside the credibility score) rather than justifying a whole extra reasoning loop.

---

## 5. Runtime architecture

Single FastAPI process. No microservices, no LangGraph-style graph DSL. The orchestration "loop" is plain, inspectable Python control flow — this matters: a dynamic reasoning loop with retries and reflection is *easier* to reason about and debug as an explicit `while` loop with logged state transitions than as a graph of nodes/edges, given the loop shape here isn't actually a complex DAG — it's a bounded plan-act-observe-reflect cycle with one coordinator.

```
app/
  api/                # FastAPI routers — /verify, /status/{run_id}, /health
  orchestrator/
    loop.py           # the plan-act-observe-reflect-delegate-retry controller (Section 6)
    planner.py        # builds/updates the dynamic task plan
    evaluator.py       # reflection / self-critique / stopping-criteria logic
  agents/
    base.py           # shared agent interface (PydanticAI Agent wrapper + logging + budget)
    orchestrator_agent.py
    decomposition_agent.py
    evidence_agent.py
    credibility_agent.py
    forensics_agent.py
    adversarial_agent.py
  tools/
    registry.py       # central tool registry, capability-tagged
    search_tools.py    # web/news/fact-check search
    forensic_tools.py  # ELA, deepfake classifiers, ASR, OCR, metadata
    provenance_tools.py # WHOIS, publisher DB, archive lookups
  protocols/
    messages.py        # Pydantic models for inter-agent Finding/Request/Critique objects
    blackboard.py       # shared run-scoped state store
  memory/
    working.py          # per-run scratchpad (in-process / Redis)
    episodic.py         # past runs, for similar-claim recall (Postgres)
    semantic.py         # vector store: fact-check corpus, known-debunked media (pgvector)
    longterm.py         # durable source-reputation + calibration store (Postgres)
  evaluation/
    calibration.py      # tracks predicted-confidence vs. outcome over time
    tracing.py           # OpenTelemetry spans per agent step
  main.py                # FastAPI app assembly
```

### 5.1 Memory architecture (four tiers, deliberately distinct)

| Tier | Scope | Backing store | Purpose | Who writes |
|---|---|---|---|---|
| **Working** | single run | in-process dict + Redis for durability across async steps | the live scratchpad — current plan, findings-so-far, budget counters | all agents, run-scoped only |
| **Episodic** | cross-run | Postgres | "have we seen this or a near-duplicate claim before?" — full past run records with verdicts, for auditability and fast-path recall | Orchestrator, at run completion |
| **Semantic** | cross-run, content-addressed | pgvector | embeddings of verified claims, fact-check corpus, and perceptual hashes of known-debunked media — retrieval, not run logs | offline ingestion job + Orchestrator on completion |
| **Long-term / reputation** | cross-run, entity-addressed | Postgres | durable, slowly-updated profiles: source credibility history, agent calibration stats (is the Forensics agent's "80% confident" actually right 80% of the time?) | Credibility agent (proposes) + Orchestrator (confirms/commits) |

This separation matters concretely: conflating episodic and semantic memory is a common mistake that causes the system to "remember" a specific past verdict and treat it as ground truth for a superficially similar claim, rather than treating it as one data point to weigh against fresh evidence. Episodic memory informs *prioritization* (search here first), never substitutes for evidence-gathering on the current claim.

### 5.2 Tool architecture
Tools are stateless, versioned, capability-tagged, and registered once in `registry.py`. Every agent declares which tool *capabilities* (not specific tool names) it needs; the registry resolves to the current implementation. This indirection is what lets a reverse-image-search provider or a deepfake classifier be swapped later without touching agent logic. Tools never make judgment calls, only return structured, typed results — if a "tool" starts needing prompted judgment about its own output, that's a signal it should be absorbed into an agent's reasoning step, not stay a tool.

### 5.3 The blackboard, not a message-passing mesh
All agents read and write to a single **run-scoped blackboard** (structured Pydantic state object) rather than exchanging point-to-point messages with each other. The Orchestrator is the sole writer of *plan* state; sub-agents write their own *Finding* records to a namespaced section of the blackboard and never edit each other's sections. This gives:
- a complete, replayable audit trail per run (this matters for a misinformation platform specifically — verdicts need to be explainable and contestable after the fact)
- no N² communication complexity as agents are added
- a natural place to attach the final report

### 5.4 Agent-to-agent communication protocol
Deliberately **hub-and-spoke, not mesh.** All delegation flows through the Orchestrator. When Evidence needs Credibility's judgment on a source, or Forensics needs Evidence to fact-check a caption, that is modeled as a typed `AgentRequest` object placed on the blackboard and picked up by the Orchestrator's next loop iteration — not a direct function call between two sub-agent instances. Reasons this is a hard constraint, not a stylistic choice:
- **cost/runaway control** — direct mesh communication is exactly how multi-agent systems quietly explode into unbounded loops of agents re-triggering each other;
- **single source of truth for stopping criteria** — only the Orchestrator tracks global budget and confidence, so it must be in the loop for every delegation;
- **auditability** — a regulator or journalist asking "why did the system reach this verdict" needs one traceable decision log, not a scattered mesh of agent-to-agent chatter.

Message schema (illustrative):
```python
class Finding(BaseModel):
    agent: str
    claim_id: str
    stance: Literal["supports", "contradicts", "mixed", "insufficient_evidence"]
    evidence: list[EvidenceItem]
    confidence: float  # calibrated, not vibes
    rationale: str
    requests: list[AgentRequest] = []  # optional asks routed back through Orchestrator

class AgentRequest(BaseModel):
    from_agent: str
    to_agent: str
    reason: str
    payload: dict
```

---

## 6. The dynamic reasoning loop (replaces the fixed pipeline)

```
def orchestrate(run_id):
    blackboard = init_run(run_id)
    plan = planner.initial_plan(blackboard)        # PLAN
    while not stopping_criteria_met(blackboard) and budget_remaining(blackboard):
        step = plan.next_step()                     # what's next given current state
        result = execute(step, blackboard)           # ACT — invoke the chosen agent
        blackboard.record(result)                     # OBSERVE
        critique = evaluator.reflect(blackboard)       # REFLECT — self-critique, gap check
        if critique.requires_new_work:
            plan = planner.replan(blackboard, critique) # DELEGATE — add/re-order steps
        if critique.suggests_retry:
            plan.requeue(step, reason=critique.reason)  # RETRY — bounded, logged, not infinite
    return synthesize_final_report(blackboard)
```

Key properties that make this genuinely dynamic rather than a workflow with an if-statement bolted on:
- **The plan is mutable at runtime.** The initial plan for a plain text claim might be `[Decompose, Evidence, Reflect]`. If Evidence reports low confidence and conflicting sources, `replan()` inserts `[Credibility(source_x), Evidence(retry, narrower query)]` before proceeding — this branch is not hardcoded, it's a consequence of the reflection step's output.
- **Retry is bounded and reasoned, not blind.** Each retry carries an explicit reason from the evaluator (e.g., "evidence agent returned only republished wire copies, not independent sources") so the retried invocation gets a sharper instruction, not an identical re-run.
- **Stopping is a real decision, evaluated every iteration**, combining: confidence threshold met, Adversarial critique addressed, and budget (cost/time/iteration count) — whichever binds first, with the system defaulting to an honest "inconclusive" verdict over a forced guess when budget binds before confidence does.

---

## 7. Evaluation & reflection (system-level, not just per-run)
- **Per-run reflection:** the evaluator step above, using an LLM-as-judge rubric grounded in the blackboard's own evidence (not a vague "does this look right" — checks specific things: independence of sources, whether the Adversarial critique was substantively addressed, whether confidence is consistent with evidence quantity).
- **Cross-run calibration:** `evaluation/calibration.py` tracks, over time, whether stated confidence correlates with outcome (via follow-up corrections, user feedback, or known ground-truth benchmark sets) — this is what prevents the platform from being confidently wrong in a stable, undetected way, which is the single worst failure mode for a credibility-scoring product.
- **Tracing:** every agent invocation, tool call, and blackboard write emits an OpenTelemetry span, so a full run is replayable and every claim in the final report is traceable back to the specific tool output or agent finding that produced it.

---

## 8. Framework and library stack

Recommendation: **PydanticAI (V2, harness-first) as the per-agent runtime, hosted inside plain FastAPI, with a custom orchestration loop — not a graph-orchestration framework.**

Reasoning, evaluated against the actual requirements rather than framework popularity:

- **LangGraph — explicitly excluded**, per requirement, and also not the right shape here: LangGraph's value is when the *workflow itself* is a complex stateful DAG needing checkpoint/resume and human-in-the-loop interrupts as first-class citizens. This system's control flow is a bounded plan-act-reflect cycle with one coordinator — a `while` loop with logged state transitions is more debuggable than a graph DSL for this shape, and it avoids taking on a heavy dependency and a second mental model just to get branching that plain Python already gives you.
- **CrewAI** — good fit when a workflow maps cleanly onto a fixed cast of chatty, role-playing agents; weaker fit here because this design deliberately rejects free-form agent-to-agent chatter (Section 5.4) in favor of a strict hub-and-spoke protocol and typed state — CrewAI's crew/chat abstraction fights that constraint rather than supporting it.
- **OpenAI Agents SDK / Anthropic Agent SDK** — excellent lightweight runtimes, but vendor-coupled to one model provider's ecosystem. This platform needs to route different agents to different model strengths over time (e.g., a stronger reasoning model for the Adversarial agent, a cheaper/faster model for Decomposition, and provider flexibility for multimodal forensics as vision/audio models evolve), so single-vendor lock-in is a real cost, not a theoretical one.
- **SmolAgents** — good for lightweight/research prototyping and code-executing agents; not the right fit for a system that needs typed, validated structured output at every agent boundary (the whole report — score, evidence, reasoning, confidence — must be schema-valid, not best-effort text) and production observability out of the box.
- **Haystack Agents / LlamaIndex Workflows** — genuinely useful, but as **retrieval-subsystem components**, not as the orchestration layer: LlamaIndex's ingestion/indexing tooling is a reasonable fit for building the semantic-memory vector store (fact-check corpus, debunked-media hashes) described in Section 5.1, used underneath the Evidence agent — not as the thing coordinating six cognitive agents.
- **PydanticAI V2** fits the actual constraints well: it's model-agnostic (avoids the lock-in problem above), brings FastAPI-style ergonomics that drop cleanly into the required single-FastAPI-app shape, enforces typed/validated structured output at agent boundaries (exactly what the Finding/AgentRequest schema in Section 5.4 needs), ships native MCP support (useful for standardizing the tool registry as MCP tools later without a rewrite), and provides built-in test doubles (TestModel/FunctionModel) so the orchestration loop and agent logic can be unit-tested without live LLM calls — important given how much of this system's correctness lives in the *control logic*, not just prompt quality.

Supporting stack:
- **FastAPI** — host process, async throughout (agent calls, tool calls, and search are all I/O-bound).
- **Postgres + pgvector** — episodic, long-term reputation, and semantic memory in one engine to start; splits out later only if scale demands it.
- **Redis** — working-memory/session state and run-status polling for long-running verifications.
- **OpenTelemetry + a trace viewer (e.g., Logfire, given PydanticAI's native integration)** — tracing/observability from day one, since a credibility platform without an audit trail is not shippable.
- **MCP** as the standardization target for tools as the tool count grows, since both PydanticAI and the broader ecosystem are converging on it — this keeps the tool registry portable if agents are later split into separate services.

The above is the general-purpose, scale-ready version of the stack. Section 10 gives the concrete, cost-optimized variant actually being built for the first working version — same architecture, cheaper/free-tier substitutions where they don't compromise correctness.

---

## 9. Scaling path (not built now, but designed for)
The hub-and-spoke protocol and the blackboard's namespaced, serializable state are what make a later split viable without a rewrite: each cognitive agent can become its own process/service behind the same typed `AgentRequest`/`Finding` contracts, with the Orchestrator's loop swapped from in-process calls to queued calls (e.g., over MCP or a task queue) with no change to its planning/reflection logic. That migration is deliberately deferred — building it now would violate the same first-principles discipline this whole document is trying to apply: don't add structure the current problem doesn't need yet.

---

## 10. Implementation stack — first working build (demo/MVP scope)

This is the concrete, cost-optimized substitution of Section 8's general stack for the first real build: free-tier providers, embedded databases instead of managed servers, in-process state instead of Redis. Same architecture, same agent boundaries, same loop — cheaper infrastructure only where it doesn't compromise correctness. Two corrections were made to an earlier draft of this stack before locking it in, documented here so the reasoning isn't lost.

### 10.1 LLM providers and per-agent model assignment

Two providers, one API key each, native PydanticAI provider classes — **no LiteLLM.** PydanticAI's `GoogleModel` and `GroqModel` already give "switch providers by changing the model string" for free; adding LiteLLM underneath would be a second routing layer solving a problem PydanticAI already solves, at the cost of one more dependency to debug.

```python
Agent('google-gla:gemini-2.5-flash', ...)
Agent('groq:llama-3.3-70b-versatile', ...)
Agent('groq:llama-3.1-8b-instant', ...)
```

| Agent | Model | Rationale |
|---|---|---|
| Orchestrator | Gemini 2.5 Flash | integration point — needs the strongest available reasoning in this stack |
| Evidence & Corroboration | Gemini 2.5 Flash | multi-step tool-use judgment over retrieved text |
| **Multimodal Forensics** | **Gemini 2.5 Flash** | *(corrected)* must take image/video/audio input natively — the model previously assigned here (`llama-3.3-70b-versatile`) is text-only and cannot process media at all |
| **Adversarial Verifier** | **Groq `llama-3.3-70b-versatile`** | *(corrected)* deliberately placed on a different provider than Evidence & Orchestrator — the Adversarial agent's entire value (Section 1) is a structurally independent second read of the same evidence; same-provider placement would share the Evidence agent's training biases and blind spots, quietly undermining the one thing that justifies this being multi-agent instead of one model role-playing |
| Source & Provenance Credibility | Groq `llama-3.3-70b-versatile` | rubric-driven, structured judgment — doesn't need frontier-tier reasoning |
| Claim Decomposition | Groq `llama-3.1-8b-instant` | closer to structured parsing than open-ended reasoning; cheap and fast |

Net effect of the correction: same two providers, same free tiers, zero added cost — just a reassignment that gives Forensics the input capability it needs and gives Adversarial the cross-provider independence it exists for.

### 10.2 Memory (demo-scoped substitutions)

| Tier | General stack (§8) | Demo build | Notes |
|---|---|---|---|
| Working | Redis | in-process Python dict | fine for single-session demo; loses state across process restarts and doesn't support concurrent multi-user sessions — the known limitation, not a hidden one |
| Episodic | Postgres | SQLite (`aiosqlite`) | enable `PRAGMA journal_mode=WAL` on the connection — without it, concurrent async writes from multiple agents mid-run will throw "database is locked" |
| Semantic | pgvector | Pinecone (free tier: 1 index, 2 GB) | free tier gives one index only — use **namespaces** within it to separate claim-embeddings from media-hashes rather than provisioning a second index |
| Long-term / reputation | Postgres | separate SQLite table | same engine as episodic for now, split out only if scale demands it |

Two completeness notes carried over from the general design, easy to lose in a demo build:
- The blackboard must be **flushed into the SQLite episodic log at run completion** (not only held in the in-process dict) — otherwise a crash mid-run loses the entire audit trail, which Section 5.3 treats as non-negotiable for this kind of platform.
- **Embedding model naming, corrected:** `text-embedding-3-small` is an OpenAI model name and does not exist on Gemini. Use `gemini-embedding-001` for claim-text semantic search. For the Forensics agent's "have we seen this media before" check, prefer **perceptual hashing** (`imagehash` / a video-hash library) over semantic embeddings — that check wants to catch the *same* image/video re-uploaded, not a semantically similar one; a pHash lookup is cheaper and more precise for that specific job. Reserve embeddings (`gemini-embedding-001`, or `gemini-embedding-2` if genuinely cross-modal semantic search is needed later) for the claim-similarity case only.

### 10.3 Supporting stack

- **Backend:** FastAPI, async single-process, Python 3.11+, PydanticAI V2 managing agent execution directly (no LiteLLM).
- **Frontend:** Next.js + Tailwind, Server-Sent Events streaming the live blackboard state so the UI shows agent reasoning as it happens.
- **Rate limiting:** `aiolimiter` — genuinely necessary, not optional, given Groq's free-tier RPM limits and that three agents (Decomposition, Credibility, Adversarial) now hit Groq every run. Load-test against concurrent runs before any live demo.
- **Logging/observability:** Loguru streamed to the UI as a reasoning trace, in place of OpenTelemetry/Logfire. Reasonable scope-down for a single-process demo — it directly serves "watch the agents reason live" better than raw spans would — but it forfeits the replayable, queryable audit trail from Section 7. That's the first thing to upgrade if this moves past demo scope toward production.
- **Background execution:** FastAPI `BackgroundTasks` + in-process/SQLite-backed status polling. No Celery/arq at this scale — add a task queue only once a single process actually becomes the bottleneck, not preemptively.

### 10.4 What stays identical to the general design
Agent boundaries, the six-agent roster, the plan-act-observe-reflect-delegate-retry loop, the hub-and-spoke communication protocol, and the blackboard schema are all unchanged. Everything in this section is an infrastructure substitution, not an architecture change — which is exactly why Section 9's scaling path still applies untouched whenever it's time to move off free tiers.
