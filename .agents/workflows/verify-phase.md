---
description: Execute an implementation phase of Scrutin with strict validation and checklist updates.
---

# Scrutin — Phase Execution Workflow

This workflow guides you through the step-by-step process of implementing, testing, and verifying a Scrutin phase. 

Whenever this command is run, follow these instructions:

---

## 🔄 The Phase Execution Loop

For the targeted Phase $N$:

### 1. Read Instructions & Checklist
1. Open and read the corresponding phase file: `d:/ENGR/Scrutin/Implementation/phase_0N_[name].md`.
2. Open and read the master task tracker in `task.md` (located in the brain/ conversation directory).
3. Validate that all prior phases are marked as complete `[x]`.
4. Assess if there are any ambiguities, missing credentials, API key requirements, or design decisions that require user input. **If anything is needed, stop and ask the user for clarification before beginning any code implementation.**

### 2. Implementation
1. Create or modify the files specified in the phase document.
2. Follow all workspace rules in `d:/ENGR/Scrutin/.agents/AGENTS.md`:
   - Hub-and-spoke topology (sub-agents do not call each other).
   - Structured Pydantic outputs (no raw dicts across agent boundaries).
   - Async SQLite calls via `aiosqlite` WAL mode.
   - Independent model providers for Adversarial (Groq Llama) vs. Evidence/Orchestrator (Gemini).
   - Use `asyncio.gather()` for parallel tool/agent calls.

### 3. Isolation Testing
1. Run the specific unit tests defined in the phase document.
2. If any test fails, correct the implementation and repeat until all tests pass.

### 4. Integration Verification
1. Run the terminal verification or smoke-test commands listed under the phase's "Verification" section.
2. Confirm the expected outputs appear exactly as specified.

### 5. Document Progress
1. Update `task.md` by marking completed tasks as `[x]`.
2. Summarize the completed phase:
   - **Files Created/Modified** (clickable file scheme links)
   - **Tests Run & Results** (test count, pass/fail status)
   - **Verification Output** (terminal snapshots or return values)
3. **STOP.** Do not start Phase $N+1$ until the user explicitly reviews and approves this summary.
