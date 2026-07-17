from __future__ import annotations
import os
import sys
from rich.console import Console

console = Console()

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


def validate_env() -> dict:
    """
    Validate all required and recommended environment variables.
    Returns the valid config dict.
    Aborts if any REQUIRED key is missing.
    Warns for RECOMMENDED keys.
    """
    config = {}
    has_error = False

    for key, purpose in REQUIRED_KEYS.items():
        val = os.getenv(key, "").strip()
        if not val:
            console.print(f"[bold red]✗ MISSING REQUIRED:[/] {key}\n  Purpose: {purpose}")
            has_error = True
        else:
            config[key] = val
            console.print(f"[green]✓[/] {key}")

    for key, purpose in RECOMMENDED_KEYS.items():
        val = os.getenv(key, "").strip()
        if not val:
            console.print(f"[yellow]⚠ OPTIONAL MISSING:[/] {key}\n  Purpose: {purpose}")
        else:
            config[key] = val

    # Load all Serper rotation keys
    for suffix in ["_2", "_3", "_4"]:
        k = f"SERPER_API_KEY{suffix}"
        val = os.getenv(k, "").strip()
        if val:
            config[k] = val

    # Load all other keys needed by agents/tools
    for key in OTHER_KEYS:
        val = os.getenv(key, "").strip()
        if val:
            config[key] = val

    if has_error:
        console.print("\n[bold red]Cannot start — required API keys are missing.[/]")
        console.print("Copy [dim].env.example[/] to [dim].env[/] and fill in the missing keys.")
        sys.exit(1)

    return config
