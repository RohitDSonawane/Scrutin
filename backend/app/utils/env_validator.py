from __future__ import annotations
import os
import sys

REQUIRED_KEYS = {
    "GROQ_API_KEY": "Groq LLM provider — Decomposition, Credibility, Adversarial agents",
    "GOOGLE_API_KEY": "Google Gemini — Orchestrator, Evidence, Forensics agents",
}

RECOMMENDED_KEYS = {
    "SERPER_API_KEY": "Google search via Serper.dev (falls back to free DuckDuckGo without this)",
    "GOOGLE_FACT_CHECK_API_KEY": "Google Fact Check API fast-path (optional but significantly improves speed)",
    "PINECONE_API_KEY": "Semantic memory for claim deduplication (optional for MVP)",
}

OTHER_KEYS = [
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_USER_AGENT",
    "ORCHESTRATOR_MODEL", "DECOMPOSITION_MODEL", "EVIDENCE_MODEL",
    "CREDIBILITY_MODEL", "FORENSICS_MODEL", "ADVERSARIAL_MODEL", "EMBEDDING_MODEL",
]

def _print_colored(text: str, color: str = "") -> None:
    colors = {
        "red": "\033[91m\033[1m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "reset": "\033[0m",
    }
    prefix = colors.get(color, "")
    suffix = colors["reset"] if color else ""
    sys.stdout.write(f"{prefix}{text}{suffix}\n")

def validate_env() -> dict:
    """
    Validate all required and recommended environment variables.
    Returns the valid config dict. Aborts if any REQUIRED key is missing.
    """
    config = {}
    has_error = False

    for key, purpose in REQUIRED_KEYS.items():
        val = os.getenv(key, "").strip()
        if not val:
            _print_colored(f"✗ MISSING REQUIRED: {key}\n  Purpose: {purpose}", "red")
            has_error = True
        else:
            config[key] = val
            _print_colored(f"OK {key}", "green")

    for key, purpose in RECOMMENDED_KEYS.items():
        val = os.getenv(key, "").strip()
        if not val:
            _print_colored(f"⚠ OPTIONAL MISSING: {key}\n  Purpose: {purpose}", "yellow")
        else:
            config[key] = val

    for suffix in ["_2", "_3", "_4"]:
        k = f"SERPER_API_KEY{suffix}"
        val = os.getenv(k, "").strip()
        if val:
            config[k] = val

    for key in OTHER_KEYS:
        val = os.getenv(key, "").strip()
        if val:
            config[key] = val

    if has_error:
        _print_colored("\nCannot start — required API keys are missing.", "red")
        _print_colored("Copy .env.example to .env and fill in the missing keys.", "yellow")
        sys.exit(1)

    return config
