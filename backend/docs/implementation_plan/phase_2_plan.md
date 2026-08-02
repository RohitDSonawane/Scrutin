# Phase 2 Detailed Implementation Plan: Scientific, Medical, Academic & Multimodal Verification Infrastructure

## 1. Executive Goal
Expand the verification tooling ecosystem to support deep, domain-specific fact-checking across scientific literature, medical research, statistical data, academic publications, and multimodal media artifacts (image, video, audio). Enhance claim classification to route specialized assertions to dedicated research tools and evaluation criteria.

---

## 2. Subsystem Components & Scope

### 2.1 Academic & Scientific Literature Tool Suite
- PubMed Integration: Query open access biomedical and life sciences literature for clinical trial results, medical consensus statements, and health claims.
- ArXiv & Semantic Scholar Integration: Query preprints and peer-reviewed computer science, physics, mathematics, and climate science publications.
- Citation & Impact Verification: Check publication metadata, peer-review status, journal impact factors, and retractions.

### 2.2 Multimodal Forensics & Authentication Tool Suite
- Perceptual Hash (pHash) Matching: Compute perceptual hashes for images to perform fast-path matching against databases of known manipulated or debunked media.
- Error Level Analysis (ELA) & Metadata Inspector: Inspect image compression levels, ELA artifacts, and EXIF metadata (GPS coordinates, camera model, creation timestamp).
- Reverse Image Context Search: Perform reverse image searches to verify whether authentic media is being presented out of historical context.
- Media Transcription Engine: Transcribe audio and video clips via Groq Whisper for textual verification.

### 2.3 Domain-Aware Claim Decomposition Subsystem
- Claim Taxonomy Expansion: Classify atomic claims into domain categories:
  - `scientific_medical`: Assertions regarding health, clinical treatments, biology, or climate data.
  - `statistical`: Numerical ratios, percentage changes, demographic figures, or economic metrics.
  - `political_news`: Breaking news events, policy assertions, or government statements.
  - `multimodal_media`: Authenticity or context of attached image, audio, or video files.
  - `identity_quote`: Direct quotes or statements attributed to named public figures.
- Load-Bearing Identification: Identify critical scientific, statistical, or media authenticity assertions that control the overall validity of the submission.

### 2.4 Specialized Evidence Routing & Synthesis
- Evidence Weighting Logic: Assign higher epistemic weight to peer-reviewed scientific papers and systematic reviews when evaluating medical or scientific claims.
- Conflict Resolution Rules: Reconcile discrepancies between popular news reporting and primary scientific publication sources.

---

## 3. Step-by-Step Task Breakdown

### Step 1: Scientific Literature API & MCP Server Adapters
- Implement MCP tools for PubMed Entrez API queries.
- Implement MCP tools for Semantic Scholar Graph API queries.
- Implement MCP tools for ArXiv search API queries.
- Incorporate structured response schemas for authors, publication dates, journal names, abstracts, and DOI links.

### Step 2: Multimodal Forensics MCP Adapters
- Implement MCP tools for image perceptual hash (pHash) computation and lookup.
- Implement MCP tools for Error Level Analysis (ELA) and EXIF metadata extraction.
- Implement MCP tools for reverse image context verification.
- Implement media transcription wrappers for audio and video files.

### Step 3: Domain-Aware Decomposition Prompt & Schema Update
- Update decomposition specifications to enforce the expanded claim taxonomy.
- Add structured validation for scientific claim attributes, statistical parameters, and media authenticity assertions.
- Incorporate opinion and rhetoric filtering for academic and scientific framing.

### Step 4: Evidence & Forensics Agent Integration
- Register academic search tools and multimodal forensics tools in the capability registry.
- Configure Evidence Agent prompt parameters to select scientific tools when verifying `scientific_medical` or `statistical` claims.
- Configure Forensics Agent prompt parameters to synthesize pHash, ELA, EXIF metadata, and reverse image context signals.
- Add fast-path checks for retracted papers and scientific consensus database entries.

### Step 5: Verification & Automated Test Coverage
- Implement unit tests covering PubMed, ArXiv, Semantic Scholar, pHash, ELA, and reverse image search MCP dispatches.
- Implement integration tests verifying domain-aware claim decomposition output formats.
- Execute live claim verification tests against scientific, medical, statistical, and image authenticity test claims.

---

## 4. Phase 2 Implementation Checklist

### Academic & Scientific Literature Tool Infrastructure
- [ ] Create PubMed Entrez query MCP server specification.
- [ ] Create Semantic Scholar Graph API query MCP server specification.
- [ ] Create ArXiv search query MCP server specification.
- [ ] Implement abstract extraction and Markdown parsing for academic papers.
- [ ] Implement paper retraction status lookup helper.
- [ ] Enforce non-raising error boundaries across all academic tool wrappers.

### Multimodal Forensics Tool Infrastructure
- [ ] Implement image perceptual hash (pHash) calculation and fast-path lookup tool.
- [ ] Implement Error Level Analysis (ELA) tool and EXIF metadata parser.
- [ ] Implement reverse image context verification search tool.
- [ ] Implement Groq Whisper media transcription tool wrapper.
- [ ] Enforce non-raising error boundaries across all forensics tool wrappers.

### Domain-Aware Claim Decomposition & Taxonomy
- [ ] Update Claim Decomposition specifications with `scientific_medical`, `statistical`, `political_news`, `multimodal_media`, and `identity_quote` categories.
- [ ] Implement validation rules requiring at least one load-bearing claim tag per claim list.
- [ ] Implement statistical parameter extractor identifying numbers, percentages, and trend assertions.
- [ ] Add scientific framing mismatch detection logic.

### Evidence & Forensics Synthesis
- [ ] Register academic and forensics tools in capability registry.
- [ ] Update Evidence Agent prompt instructions to prioritize primary literature for medical and climate claims.
- [ ] Update Forensics Agent prompt instructions to classify technical manipulation vs out-of-context framing.
- [ ] Implement source hierarchy scoring giving systematic reviews higher weight than general news blogs.

### System Verification & Quality Assurance
- [ ] Run full automated test suite to verify no regressions across existing agents.
- [ ] Perform live verification test on a medical claim query.
- [ ] Perform live verification test on an image authenticity claim query.
