from __future__ import annotations
import asyncio
import os
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

app_cli = typer.Typer(
    name="scrutin",
    help="Scrutin — Multi-Agent Misinformation Verification Platform",
    add_completion=False,
)
console = Console()





@app_cli.command("verify")
def verify_cmd(
    claim: Optional[str] = typer.Option(None, "--claim", help="Plain text claim to verify"),
    url: Optional[str] = typer.Option(None, "--url", help="URL of an article to verify"),
    trace: bool = typer.Option(False, "--trace", help="Show verbose agent trace output"),
    db_path: str = typer.Option("scrutin.db", "--db", help="Path to SQLite database"),
):
    """Verify a claim or article URL through the full multi-agent pipeline."""
    from dotenv import load_dotenv
    load_dotenv()
    from app.memory.migrations import run_migrations
    run_migrations(db_path)

    from app.utils.logger import configure_terminal_logger
    configure_terminal_logger(trace=trace)

    # Register all tools
    import app.tools._register_all  # noqa

    from app.utils.env_validator import validate_env
    config = validate_env()

    if not claim and not url:
        console.print("[bold red]ERROR:[/] Provide either --claim or --url")
        raise typer.Exit(1)

    raw_input = claim or url
    input_type = "text" if claim else "url"

    console.print(f"\n[bold cyan]Scrutin[/] — Verifying: [italic]{raw_input[:80]}...[/]\n")

    from app.orchestrator.loop import run_orchestrator
    report = asyncio.run(run_orchestrator(
        raw_input=raw_input,
        input_type=input_type,
        config=config,
        db_path=db_path,
    ))

    _print_verdict_banner(report)


def _print_verdict_banner(report) -> None:
    """Print the final formatted verdict to terminal."""
    verdict_colors = {
        "true": "green", "false": "red", "misleading": "yellow",
        "inconclusive": "dim", "unverifiable": "dim",
    }
    color = verdict_colors.get(report.overall_verdict, "white")

    # Build evidence table
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Key", style="dim", width=16)
    table.add_column("Value")
    table.add_row("Run ID", report.run_id)
    table.add_row("Verdict", f"[bold {color}]{report.overall_verdict.upper()}[/]")
    table.add_row("Score", f"{report.credibility_score:.0f} / 100")
    table.add_row("Confidence", f"{report.confidence:.0%}")
    table.add_row("Iterations", f"{report.iterations_used} / 20")
    table.add_row("Time", f"{report.processing_time_seconds:.1f}s")
    if report.budget_exhausted:
        table.add_row("Budget", "[bold yellow]EXHAUSTED[/]")

    # Evidence sources
    if report.evidence_used:
        sources = ", ".join(set(e.source_domain for e in report.evidence_used[:5] if e.source_domain))
        table.add_row("Sources", sources)

    # Adversarial summary
    if report.adversarial_summary:
        adv_short = report.adversarial_summary[:120] + "..." if len(report.adversarial_summary) > 120 else report.adversarial_summary
        table.add_row("Adversarial", adv_short)

    panel = Panel(table, title="[bold]Scrutin Verification Report[/]", border_style=color)
    console.print(panel)


@app_cli.command("test")
def test_cmd(
    db_path: str = typer.Option("scrutin.db", "--db"),
):
    """Run the ground-truth regression suite against 5 known-verdict claims."""
    from dotenv import load_dotenv
    load_dotenv()
    from app.memory.migrations import run_migrations
    run_migrations(db_path)
    import app.tools._register_all  # noqa

    from app.utils.env_validator import validate_env
    config = validate_env()

    try:
        from tests.fixtures.ground_truth import GROUND_TRUTH_CASES
    except ImportError:
        console.print("[red]tests/fixtures/ground_truth.py not found. Create it in Phase 9.[/]")
        raise typer.Exit(1)

    from app.orchestrator.loop import run_orchestrator
    from app.utils.logger import configure_terminal_logger
    from app.evaluation.calibration import log_calibration_entry
    configure_terminal_logger(trace=False)

    async def run_all_cases():
        results = []
        for case in GROUND_TRUTH_CASES:
            console.print(f"\n[cyan]Testing:[/] {case['claim'][:60]}...")
            report = await run_orchestrator(
                raw_input=case["claim"],
                config=config,
                db_path=db_path,
            )
            passed = report.overall_verdict == case["expected_verdict"]
            results.append((case["claim"][:50], case["expected_verdict"], report.overall_verdict, passed))
            status = "[green]PASS[/]" if passed else "[red]FAIL[/]"
            console.print(f"  {status} Expected: {case['expected_verdict']} | Got: {report.overall_verdict}")

            outcome = "correct" if passed else "incorrect"
            await log_calibration_entry(
                run_id=report.run_id,
                agent="orchestrator",
                stated_confidence=report.confidence,
                actual_outcome=outcome,
                db_path=db_path,
            )
        return results

    results = asyncio.run(run_all_cases())
    passed_count = sum(1 for r in results if r[3])
    console.print(f"\n[bold]Results: {passed_count}/{len(results)} passed[/]")


@app_cli.command("stats")
def stats_cmd(
    db_path: str = typer.Option("scrutin.db", "--db"),
):
    """Show database statistics — run counts, verdict distribution, calibration."""
    import asyncio
    from app.memory.episodic import get_run_stats
    from app.evaluation.calibration import print_calibration_report

    stats = asyncio.run(get_run_stats(db_path=db_path))
    table = Table(title="Scrutin Database Stats", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Total Runs", str(stats["total_runs"]))
    for verdict, count in (stats.get("verdicts") or {}).items():
        table.add_row(f"Verdict: {verdict}", str(count))
    console.print(table)
    print_calibration_report(db_path=db_path)


if __name__ == "__main__":
    app_cli()
