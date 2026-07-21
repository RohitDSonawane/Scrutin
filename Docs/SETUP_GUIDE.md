# Scrutin — Complete Setup & Configuration Guide

This guide provides step-by-step instructions to set up **Scrutin**, acquire all required API keys for each model/provider, configure environment variables, initialize databases, and run verification workflows.

---

## 📋 System Prerequisites

* **Python:** Version `3.11` or `3.12`
* **Git:** Installed on system
* **Optional Binaries:** `ffmpeg` (required only if testing multimodal video/audio transcription features)

---

## 🚀 Step-by-Step Installation

### 1. Clone the Repository & Navigate to Workspace
```bash
git clone https://github.com/yourusername/Scrutin.git
cd Scrutin
```

### 2. Create and Activate Virtual Environment
```bash
# On Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
python -m venv .venv
.\.venv\Scripts\activate.bat

# On macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🔑 How to Obtain API Keys

Scrutin uses a multi-provider strategy to enforce adversarial independence (e.g. Gemini vs. Groq Llama) and fast-path fact checking. Below is how to obtain keys for each provider:

### 1. Google Gemini API Key (`GOOGLE_API_KEY`) — **REQUIRED**
* **Used For:** Orchestrator Agent, Evidence Agent, Forensics Agent (`gemini-2.5-flash`)
* **How to Get Key:**
  1. Visit [Google AI Studio](https://aistudio.google.com/).
  2. Sign in with your Google account.
  3. Click **"Get API key"** in the top navigation bar.
  4. Click **"Create API key"** (in a new or existing project).
  5. Copy the generated key (starts with `AIza...`).

---

### 2. Groq API Key (`GROQ_API_KEY`) — **REQUIRED**
* **Used For:** Claim Decomposition Agent (`llama-3.1-8b-instant`), Credibility Agent & Adversarial Verifier Agent (`llama-3.3-70b-versatile`)
* **How to Get Key:**
  1. Visit the [Groq Console](https://console.groq.com/).
  2. Sign up or log in.
  3. Navigate to **API Keys** in the sidebar (or go to [console.groq.com/keys](https://console.groq.com/keys)).
  4. Click **"Create API Key"**, give it a name, and copy the key (starts with `gsk_...`).

---

### 3. Serper.dev Google Search API Key (`SERPER_API_KEY`) — **RECOMMENDED**
* **Used For:** Primary live Google web search retrieval for the Evidence agent.
* **How to Get Key:**
  1. Visit [Serper.dev](https://serper.dev/).
  2. Sign up for a free account (includes 2,500 free search queries).
  3. Copy your API Key from the dashboard.
  *Note: Scrutin supports key rotation. You can optionally add `SERPER_API_KEY_2`, `SERPER_API_KEY_3`, `SERPER_API_KEY_4` if using multiple free tier accounts.*

---

### 4. Google Fact Check Tools API Key (`GOOGLE_FACT_CHECK_API_KEY`) — **RECOMMENDED**
* **Used For:** Instant ClaimReview database fast-path lookup (verifies viral claims in $< 1.5$ seconds).
* **How to Get Key:**
  1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
  2. Create a project (or select an existing one).
  3. Go to **APIs & Services > Library**, search for **Fact Check Tools API**, and click **Enable**.
  4. Go to **APIs & Services > Credentials**, click **Create Credentials > API Key**, and copy the key.
  *(You can also reuse your `GOOGLE_API_KEY` if Fact Check Tools API is enabled on that GCP project).*

---

### 5. Pinecone Vector Database API Key (`PINECONE_API_KEY`) — **OPTIONAL**
* **Used For:** Cross-run semantic memory claim deduplication.
* **How to Get Key:**
  1. Visit [Pinecone.io](https://www.pinecone.io/) and create a free account.
  2. Create an API Key under the **API Keys** tab.

---

### 6. Reddit API Keys (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`) — **OPTIONAL**
* **Used For:** Social media trend verification.
* **How to Get Key:**
  1. Go to [Reddit Apps Preferences](https://www.reddit.com/prefs/apps).
  2. Click **"are you a developer? create an app..."**.
  3. Choose **"script"**, set name and redirect URI (`http://localhost:8080`), and create app.
  4. Copy `client_id` (under app name) and `secret`.

---

## ⚙️ Environment Configuration (`.env`)

1. Copy `.env.example` to create your active `.env` file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in your keys:
   ```env
   # LLM Providers
   GOOGLE_API_KEY=AIzaSyYourActualGoogleKeyHere
   GROQ_API_KEY=gsk_YourActualGroqKeyHere

   # Web Search & Fact Check
   SERPER_API_KEY=your_serper_key_here
   GOOGLE_FACT_CHECK_API_KEY=AIzaSyYourActualGoogleKeyHere

   # Optional Vector Store
   PINECONE_API_KEY=pcsk_your_pinecone_key_here

   # Default Models
   ORCHESTRATOR_MODEL=google:gemini-2.5-flash
   DECOMPOSITION_MODEL=groq:llama-3.1-8b-instant
   EVIDENCE_MODEL=google:gemini-2.5-flash
   CREDIBILITY_MODEL=groq:llama-3.3-70b-versatile
   FORENSICS_MODEL=google:gemini-2.5-flash
   ADVERSARIAL_MODEL=groq:llama-3.3-70b-versatile
   EMBEDDING_MODEL=gemini-embedding-001

   # Database
   SCRUTIN_DB_PATH=scrutin.db
   ```

---

## 🗄️ Database Initialization

Initialize the local SQLite WAL-mode schema (creates four WAL-optimized tables: `episodic_runs`, `source_reputation`, `claim_embeddings`, `calibration_log`):

```bash
python -m app.memory.migrations
```

---

## 💻 Running the System

Scrutin provides a rich CLI interface. Here are all execution modes:

### 1. Verify a Single Text Claim (with Live Agent Output)
```bash
python -m app.cli verify --claim "The Eiffel Tower was built in 1889" --trace
```

### 2. Verify an Article by URL
```bash
python -m app.cli verify --url "https://example.com/breaking-news-article"
```

### 3. Run Ground-Truth Test Cases
Runs tests against 5 ground-truth claims:
```bash
python -m app.cli test --db test_suite.db
```

### 4. Run Automated Pytest Suite (44 Unit Tests)
```bash
pytest
```

### 5. Check Database Statistics & ECE Calibration Scores
```bash
python -m app.cli stats
```

---

## 🛠️ Troubleshooting & FAQ

### Q1: `UnicodeEncodeError: 'charmap' codec can't encode character...` on Windows
Set `PYTHONIOENCODING=utf-8` in your PowerShell session before running commands:
```powershell
$env:PYTHONIOENCODING="utf-8"
python -m app.cli verify --claim "Your claim" --trace
```

### Q2: Rate Limit 429 (`RESOURCE_EXHAUSTED`) on Free Tiers
- **Gemini Free Tier:** 15 Requests Per Minute (RPM).
- **Groq Free Tier:** 30 Requests Per Minute (RPM).
*Scrutin includes built-in rate limiters (`app/utils/rate_limiter.py`). If running bulk claims in custom scripts, add a 10-12 second `asyncio.sleep()` between iterations.*
