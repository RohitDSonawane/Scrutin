# Phase 3 Detailed Implementation Plan: Stateful Graph Orchestration Engine & Reasoning Infrastructure

## 1. Executive Goal
Transition the core orchestration mechanism into a stateful directed graph engine. Implement dynamic state checkpointing, multi-step ReAct reasoning loops within sub-agents, dynamic context window pruning, and seamless event streaming to guarantee predictable, scalable, and audit-ready verification flows.

---

## 2. Subsystem Components & Scope

### 2.1 Stateful Directed Graph Orchestrator (LangGraph Engine)
- State Graph Topology: Implement explicit state graph nodes:
  - `DecompositionNode`: Converts raw claim inputs into structured atomic claims.
  - `EvidenceNode`: Dispatches iterative search and corroboration queries.
  - `CredibilityNode`: Evaluates domain age, WHOIS signals, and track record.
  - `ForensicsNode`: Performs media authenticity and context checks.
  - `AdversarialNode`: Executes mandatory devil's advocate red-teaming.
  - `EvaluatorNode`: Evaluates epistemic sufficiency and stopping criteria.
  - `FinalizerNode`: Synthesizes final verification reports.
- State Persistence & Checkpointing: Enable node-level state checkpointing to support pause, resume, and audit playback.
- Dynamic Conditional Edges: Route control flow dynamically based on claim domain, evidence readiness, and red-team feedback.
- Event Dispatch Compatibility: Ensure graph execution events emit structured `on_event` notifications for SSE streaming endpoints and terminal trace logs.

### 2.2 Sub-Agent ReAct Reasoning Loops
- Multi-Turn Tool ReAct Loop: Allow specialized sub-agents to run multi-turn ReAct reasoning loops (Thought -> Action -> Observation) before returning findings.
- Calibrated Red-Team Integration: Map Adversarial red-team counter-arguments to `stance="mixed"` with `confidence=0.5` to prevent false binary contradiction ties.
- Re-query & Query Sharpening: Enable sub-agents to autonomously reformulate search terms when initial evidence is sparse or ambiguous.

### 2.3 Dynamic Context Pruning & Window Management
- Sliding-Window Context Trimming: Implement intelligent token management that summarizes historical evidence traces while preserving load-bearing findings.
- Context Budgeting: Enforce a strict token budget (< 4,000 tokens) for LLM decision inputs to optimize latency and model attention performance.

---

## 3. Step-by-Step Task Breakdown

### Step 1: Graph State Schema & Event Emitter Layer
- Define the typed graph state structure containing run metadata, atomic claims, evidence store pointers, findings history, and plan status.
- Implement database-backed state checkpointing to save graph snapshots after every node execution.
- Wire event emitter hooks to support SSE streaming endpoints (`/api/verify/stream`) and CLI callbacks (`on_event`).

### Step 2: Node Implementation & Conditional Routing
- Build `DecompositionNode` with dynamic output validation.
- Build `EvidenceNode` with multi-step search capability.
- Build `CredibilityNode` with reputation lookup integration.
- Build `ForensicsNode` with multimodal signal synthesis.
- Build `AdversarialNode` with calibrated red-team critique generation (`stance="mixed"`, `confidence=0.5`).
- Build `EvaluatorNode` with qualitative readiness scoring.
- Build `FinalizerNode` with report assembly logic.
- Configure conditional routing edges directing workflow based on readiness thresholds and red-team findings.

### Step 3: Sub-Agent ReAct Execution Engine
- Configure PydanticAI agents to support multi-turn tool interaction cycles.
- Implement tool observation parsing and internal scratchpad management.
- Add loop bounds preventing sub-agent execution loops from exceeding allocated tool call budgets.

### Step 4: Context Pruning & Summarization Engine
- Implement evidence snippet summarization helpers.
- Implement finding history compressor retaining stance and confidence summaries.
- Add context budget enforcement before invoking orchestrator routing models.

### Step 5: System Testing & Graph Verification
- Implement unit tests covering state transitions, event emissions, and checkpoint saves.
- Implement integration tests verifying end-to-end graph traversal and SSE stream data outputs.
- Perform benchmark performance tests measuring execution latency and token efficiency.

---

## 4. Phase 3 Implementation Checklist

### Stateful Graph Engine Infrastructure
- [ ] Define Graph State schema covering claims, evidence pointers, findings, and plan status.
- [ ] Implement database state checkpointer for automatic state persistence.
- [ ] Implement event dispatch emitter supporting SSE streaming (`/api/verify/stream`) and terminal callbacks (`on_event`).
- [ ] Implement conditional edge router evaluating readiness scores and adversarial flags.

### Graph Nodes Implementation
- [ ] Construct Decomposition Node with claim structure validation.
- [ ] Construct Evidence Node with search and corroboration handlers.
- [ ] Construct Credibility Node with WHOIS and reputation score handlers.
- [ ] Construct Forensics Node with media signal synthesis.
- [ ] Construct Adversarial Node mapping critiques to `stance="mixed"` and `confidence=0.5`.
- [ ] Construct Evaluator Node with qualitative readiness scoring.
- [ ] Construct Finalizer Node with structured report output generation.

### Sub-Agent ReAct Loops & Context Management
- [ ] Configure multi-turn tool execution cycles for Evidence and Forensics agents.
- [ ] Implement query sharpening logic for iterative tool searches.
- [ ] Implement context pruning helper maintaining context window under 4,000 tokens.
- [ ] Add sub-agent tool call budget counters.

### System Verification & Quality Assurance
- [ ] Run automated test suite to confirm zero regressions across all core components.
- [ ] Perform graph checkpoint recovery verification test.
- [ ] Verify real-time event streaming output format on `/api/verify/stream`.
- [ ] Perform end-to-end multi-agent verification benchmark run.
