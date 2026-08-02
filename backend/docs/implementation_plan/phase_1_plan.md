# Phase 1 Detailed Implementation Plan: Local Vector Memory & Model Context Protocol (MCP) Infrastructure

## 1. Executive Goal
Establish a self-contained, zero-cost vector memory subsystem and standardize all external tool integrations under the Model Context Protocol (MCP) specification. Upgrade embedding generation to the latest standard Google GenAI SDK and ensure offline vector operations.

---

## 2. Subsystem Components & Scope

### 2.1 Local Vector Memory Subsystem (`sqlite-vec`)
- Embed 768-dimensional vector storage natively within the primary database engine using the `sqlite-vec` extension across both synchronous `sqlite3` and asynchronous `aiosqlite` connections.
- Upgrade embedding generation in semantic storage from deprecated generative AI SDKs to the official `google.genai` Client SDK (`genai.Client()`).
- Provide zero-cost local semantic indexing and similarity searches for claim texts, source snippets, and findings.
- Support hybrid operation: execute vector operations locally by default, with optional background sync to secondary vector stores when cloud credentials are present.

### 2.2 Model Context Protocol (MCP) Tool Architecture
- Implement Model Context Protocol (MCP) server adapters for all external tool services:
  - MCP Search Server: Dispatches web grounding queries with key-rotation and keyless fallback handling.
  - MCP Provenance Server: Executes WHOIS domain registration lookups and domain recency evaluations.
  - MCP Reference Server: Queries ClaimReview fact-checking indices.
  - MCP Media Server: Executes Jina Reader content extraction and media transcription wrappers.
- Enforce strict input validation, standardized error handling, and structured JSON-RPC responses across all tool invocation boundaries.

### 2.3 Environment & Configuration Provider Layer
- Ensure all model endpoints (orchestration models, decomposition models, evidence models, credibility models, forensics models, adversarial models, evaluator models, and embedding models) resolve dynamically from environment configuration variables.
- Implement cascading provider fallbacks to guarantee robust startup and run completion under varying provider availabilities.

---

## 3. Step-by-Step Task Breakdown

### Step 1: Database Schema & Vector Extension Initialization
- Initialize the `sqlite-vec` extension during application startup for both sync and async database connections.
- Create virtual vector tables dedicated to storing 768-dimensional claim embeddings using cosine distance metrics.
- Implement transactional metadata storage mapping vector identifiers to run IDs, claim texts, and overall verdicts.

### Step 2: Local Vector Operations & SDK Migration
- Migrate embedding generation functions to the unified `google.genai` Client SDK.
- Build asynchronous embedding generator handlers resolving target models dynamically from environment settings.
- Implement local vector insertion, upsertion, and similarity query functions.
- Enforce vector dimension truncation and normalization to align with index specifications.

### Step 3: MCP Server Adapter Development
- Develop MCP server specifications for web search grounding operations.
- Develop MCP server specifications for domain age and registrar WHOIS verification.
- Develop MCP server specifications for ClaimReview fact-check index queries.
- Develop MCP server specifications for keyless web page fetching and markdown rendering.

### Step 4: MCP Client & Tool Registration Layer
- Configure tool registration interfaces to dynamically discover and expose MCP tool capabilities.
- Implement structured input parsing and schema verification for incoming tool requests.
- Provide error boundary wrappers ensuring tool failures emit structured error messages without halting execution.

### Step 5: Verification & End-to-End Testing
- Execute unit and integration test suites validating database vector table operations.
- Execute test suites verifying MCP tool dispatches and error handling responses.
- Verify full verification runs operate successfully in offline/keyless configurations without SDK deprecation warnings.

---

## 4. Phase 1 Implementation Checklist

### Database & Vector Memory Subsystem
- [ ] Configure application startup lifecycle to load `sqlite-vec` extension binaries across sync and async database connections.
- [x] Upgrade embedding generator functions to use `google.genai` Client SDK (`genai.Client()`).
- [ ] Create virtual vector database table schema for 768-dimensional float arrays with cosine metric indexing.
- [ ] Implement claim embedding upsert function writing vector arrays and associated metadata to database.
- [ ] Implement vector similarity search handler returning top-k matching past claims with relevance scores.
- [ ] Implement optional cloud vector store synchronization pipeline.

### Model Context Protocol (MCP) Server Infrastructure
- [ ] Define MCP tool schema specifications for web search grounding queries.
- [ ] Define MCP tool schema specifications for domain WHOIS verification.
- [ ] Define MCP tool schema specifications for ClaimReview database lookup.
- [ ] Define MCP tool schema specifications for URL markdown content extraction.
- [ ] Implement MCP tool dispatch handler with structured request validation and response mapping.
- [ ] Integrate API key rotation and keyless fallback handling into the search tool server.
- [ ] Enforce non-raising error boundaries across all MCP tool function wrappers.

### Configuration & Environment Management
- [ ] Verify environment configuration loader handles default model cascades.
- [ ] Validate runtime initialization error reporting when required keys or defaults are missing.
- [ ] Update environment documentation templates with all supported model target keys.

### System Verification & Quality Assurance
- [ ] Run full automated test suite to confirm zero regressions across all core components.
- [ ] Perform offline verification run to confirm local vector memory functionality without cloud dependencies.
