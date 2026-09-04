"""Lab CLI (§7).

Phase 0 implements working `init`, `status`, `score`, and `search` commands.
The pipeline commands (discover, research, prior-art, formalize, simulate,
redteam, rank, report, pipeline) are declared as stubs so the command surface
is stable from day one; they fail fast with "not implemented in Phase 0".
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from blockchain_rd_lab import __version__
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus
from blockchain_rd_lab.scoring import ScoringEngine, load_scoring_config

app = typer.Typer(
    name="lab",
    help="AI Blockchain R&D Lab — autonomous mechanism research laboratory.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db() -> LabDatabase:
    cfg = load_config()
    db = LabDatabase(REPO_ROOT / cfg.storage.database)
    db.create_all()
    return db


def _not_implemented(name: str, phase: str) -> None:
    console.print(
        f"[yellow]`lab {name}` is planned for {phase}. "
        f"Phase 0 provides the foundation only (see MASTER BUILD PROMPT §38).[/yellow]"
    )
    raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# Working commands
# ---------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Print lab version."""
    console.print(f"AI Blockchain R&D Lab v{__version__}")


@app.command()
def init(
    force: Annotated[bool, typer.Option("--force", help="Drop and recreate all tables")] = False,
) -> None:
    """Initialize the lab database and directory structure."""
    db = _db()
    if force:
        db.drop_all()
        db.create_all()
        console.print("[red]Dropped and recreated all tables.[/red]")
    else:
        console.print("[green]Database schema initialized.[/green]")
    console.print(f"Database: {load_config().storage.database}")


@app.command()
def status() -> None:
    """Show lab status: candidate counts by lifecycle state."""
    cfg = load_config()
    db = _db()

    table = Table(title=f"{cfg.lab.name} — Status")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")

    total = 0
    for state in CandidateStatus:
        n = db.count_candidates(state)
        total += n
        table.add_row(state.value, str(n))
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]")
    console.print(table)

    console.print(
        f"\n[dim]Provider: {cfg.runtime.llm_provider} · "
        f"Target: {cfg.pipeline.discovery_count} ideas → "
        f"{cfg.pipeline.post_prior_art} candidates → "
        f"{cfg.pipeline.finalists} finalists[/dim]"
    )


@app.command()
def score(
    candidate_id: Annotated[str, typer.Argument(help="Candidate ID to score")],
) -> None:
    """Run the deterministic scoring engine on a stored candidate."""
    db = _db()
    candidate = db.get_candidate(candidate_id)
    if candidate is None:
        console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
        raise typer.Exit(code=1)

    engine = ScoringEngine(load_scoring_config())
    result = engine.score(candidate)

    candidate.overall_score = result.overall_score
    db.save_candidate(candidate)

    table = Table(title=f"Score — {candidate.name}")
    table.add_column("Dimension")
    table.add_column("Weight", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Weighted", justify="right")
    table.add_column("Imputed")
    for d in result.dimensions:
        table.add_row(
            d.dimension,
            f"{d.weight:.0%}",
            f"{d.score:.2f}",
            f"{d.weighted:.3f}",
            "yes" if d.imputed else "",
        )
    table.add_row(
        "[bold]Overall[/bold]",
        "",
        "",
        f"[bold]{result.overall_score:.4f}[/bold]",
        "",
    )
    console.print(table)

    if result.fatal_flaw_applied:
        console.print(f"[red]FATAL FLAW CAP APPLIED ({result.fatal_flaw_count}):[/red]")
        for detail in result.fatal_flaw_details:
            console.print(f"  [red]• {detail}[/red]")


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search term (name/category/keywords)")],
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 20,
) -> None:
    """Search candidates by name, category, or keyword."""
    db = _db()
    q = query.lower()
    matches = [
        c
        for c in db.list_candidates()
        if q in c.name.lower()
        or q in c.category.lower()
        or q in c.core_mechanism.lower()
        or q in c.description.lower()
    ][:limit]

    if not matches:
        console.print(f"[yellow]No candidates matching {query!r}.[/yellow]")
        return

    table = Table(title=f"Search: {query!r}")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Status")
    table.add_column("Score", justify="right")
    for c in matches:
        table.add_row(
            c.id,
            c.name,
            c.category,
            c.status.value,
            f"{c.overall_score:.2f}" if c.overall_score is not None else "—",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Phase 1+ command stubs (§7) — declared now, implemented later
# ---------------------------------------------------------------------------


@app.command("discover")
def discover(
    count: Annotated[int, typer.Option("--count", "-n", min=1)] = 10,
) -> None:
    """Generate novel mechanism candidates (Phase 1)."""
    _not_implemented("discover", "PHASE 1 — DISCOVERY")


@app.command("research")
def research(
    candidate_id: str | None = typer.Argument(default=None),
) -> None:
    """Run research agents on candidates (Phase 2)."""
    _not_implemented("research", "PHASE 2 — RESEARCH")


@app.command("prior-art")
def prior_art(candidate_id: str | None = typer.Argument(default=None)) -> None:
    """Check prior art for candidates (Phase 2)."""
    _not_implemented("prior-art", "PHASE 2 — RESEARCH")


@app.command("formalize")
def formalize(candidate_id: str | None = typer.Argument(default=None)) -> None:
    """Build mathematical models for candidates (Phase 3)."""
    _not_implemented("formalize", "PHASE 3 — FORMALIZATION")


@app.command()
def simulate(candidate_id: str | None = typer.Argument(default=None)) -> None:
    """Run simulations on candidates (Phase 4)."""
    _not_implemented("simulate", "PHASE 4 — SIMULATION")


@app.command()
def redteam(candidate_id: str | None = typer.Argument(default=None)) -> None:
    """Adversarial testing on candidates (Phase 5)."""
    _not_implemented("redteam", "PHASE 5 — ADVERSARIAL TESTING")


@app.command()
def rank() -> None:
    """Rank scored candidates (Phase 6)."""
    _not_implemented("rank", "PHASE 6 — RANKING")


@app.command()
def report() -> None:
    """Generate research reports (Phase 7)."""
    _not_implemented("report", "PHASE 7 — REPORTING")


@app.command()
def pipeline(
    count: Annotated[int, typer.Option("--count", "-n", min=1)] = 10,
) -> None:
    """Run the full research pipeline end-to-end (Phase 8+)."""
    _not_implemented("pipeline", "a later phase once agents are implemented")


if __name__ == "__main__":
    app()
if __name__ == "__main__":
    app()
