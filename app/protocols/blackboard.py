from __future__ import annotations
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field
from app.protocols.messages import Plan, Finding


# Evidence ID prefix convention
# WB = Web search | FC = Fact Check | RD = Reddit
# WK = Wikipedia | YT = YouTube | TR = Transcript | NW = News

class Blackboard(BaseModel):
    run_id: str
    raw_input: str
    input_type: Literal["text", "url", "image", "video"] = "text"

    # Decomposition outputs
    atomic_claims: dict[str, str] = Field(default_factory=dict)

    # Evidence store — heavy content keyed by pointer IDs
    evidence_store: dict[str, Any] = Field(default_factory=dict)

    # Agent findings — APPEND-ONLY
    findings: list[dict] = Field(default_factory=list)

    # Orchestration
    plan: Plan = Field(default_factory=Plan)
    iterations: int = 0
    budget_limit: int = 20
    provisional_verdict: Optional[str] = None
    final_report: Optional[dict] = None

    model_config = {"arbitrary_types_allowed": True}

    def next_evidence_id(self, prefix: str) -> str:
        count = sum(1 for k in self.evidence_store if k.startswith(prefix))
        return f"{prefix}{count + 1}"

    def store_evidence(self, prefix: str, data: dict) -> str:
        """Store heavy evidence data and return pointer ID. Agents store IDs, not content."""
        from loguru import logger
        eid = self.next_evidence_id(prefix)
        self.evidence_store[eid] = data
        logger.debug(f"Stored {eid} ← {data.get('url', '')[:60]}")
        return eid

    def append_finding(self, finding: Finding) -> None:
        """Append-only — never overwrites existing findings."""
        self.findings.append(finding.model_dump())

    def get_findings_for_claim(self, claim_id: str) -> list[dict]:
        return [f for f in self.findings if f["claim_id"] == claim_id]

    def get_pending_requests(self) -> list[dict]:
        """Collect all outbound AgentRequests from all findings."""
        requests = []
        for f in self.findings:
            requests.extend(f.get("requests", []))
        return requests

    def budget_remaining(self) -> bool:
        return self.iterations < self.budget_limit

    def flush_to_sqlite(self, conn) -> None:
        """
        Lightweight audit-trail flush — writes raw Blackboard JSON to episodic_runs.
        Called with a SYNCHRONOUS sqlite3 connection from try/finally in loop.py.

        IMPORTANT TWO-WRITE PATTERN (architecture §5.3):
        1. This method: raw JSON audit trail (always runs, even on crash)
        2. episodic.record_run(): structured fields (overall_verdict, score, etc.)
           Called separately by the Orchestrator loop ONLY when a clean VerificationReport exists.

        Why two writes? If the loop crashes mid-run, we still get the audit trail.
        The structured fields are only meaningful at clean completion.
        """
        conn.execute(
            """INSERT OR REPLACE INTO episodic_runs
               (run_id, raw_input, input_type, data_json, iterations_used, created_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (self.run_id, self.raw_input, self.input_type,
             self.model_dump_json(), self.iterations)
        )
