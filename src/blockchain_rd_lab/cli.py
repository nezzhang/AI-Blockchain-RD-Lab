"""Lab CLI (§7).

Phase 1: working `init`, `status`, `score`, `search`, `discover`, `seed`.
The remaining pipeline commands (research, prior-art, formalize, simulate,
redteam, rank, report, pipeline) are stubs that fail fast with a pointer to
their future phase.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from blockchain_rd_lab import __version__
from blockchain_rd_lab.config import REPO_ROOT, load_config, load_research
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
# Phase 1: discovery (implemented)
# ---------------------------------------------------------------------------


def _provider_from_config():
    """Resolve the configured LLM provider (mock by default)."""
    from blockchain_rd_lab.agents import get_provider

    cfg = load_config()
    name = cfg.runtime.llm_provider
    if name == "mock":
        return get_provider("mock")
    settings = cfg.providers.get(name)
    kwargs = settings.model_dump() if settings else {}
    return get_provider(name, **kwargs)


@app.command("discover")
def discover(
    count: Annotated[int, typer.Option("--count", "-n", min=1)] = 10,
    no_avoid: Annotated[
        bool, typer.Option("--no-avoid", help="Skip dedup against existing ideas")
    ] = False,
    mock_fixtures: Annotated[
        bool,
        typer.Option(
            "--mock-fixtures",
            help="Use offline fixture batches instead of the configured provider",
        ),
    ] = False,
) -> None:
    """Generate novel mechanism candidates: LLM → normalize → dedup → store."""
    from blockchain_rd_lab.discovery.service import DiscoveryService

    db = _db()
    if mock_fixtures:
        from blockchain_rd_lab.agents import MockLLMProvider
        from blockchain_rd_lab.testing import fixture_responses

        provider = MockLLMProvider()
        for response in fixture_responses():
            provider.queue_response(response)
    else:
        provider = _provider_from_config()
    research = load_research()
    service = DiscoveryService(
        provider, db, research_config=research, ideas_dir=REPO_ROOT / "ideas" / "active"
    )
    summary = service.discover(count=count, avoid_existing=not no_avoid)

    table = Table(title=f"Discovery — {summary.stored} new candidates")
    for col in ("Metric", "Value"):
        table.add_column(col, justify="right" if col == "Value" else "left")
    table.add_row("generated", str(summary.generated))
    table.add_row("normalized", str(summary.normalized))
    table.add_row("duplicates removed", str(summary.duplicates_removed))
    table.add_row("stored", str(summary.stored))
    table.add_row("failed batches", str(summary.failed_batches))
    console.print(table)

    if summary.errors:
        console.print("[dim]Notes:[/dim]")
        for e in summary.errors[:10]:
            console.print(f"  [dim]• {e}[/dim]")

    for cid in summary.candidate_ids:
        console.print(f"  [green]stored[/green] {cid}")


@app.command("seed")
def seed(
    experiment: Annotated[str, typer.Option("--experiment", "-e")] = "population-money",
) -> None:
    """Seed a canonical experiment candidate (§25: Population Money = #001).

    The seeded idea enters the funnel as an ORDINARY candidate — it must
    compete fairly (§24: do not prematurely select the Population idea).
    """
    from blockchain_rd_lab.seeds import EXPERIMENT_SEEDS

    if experiment not in EXPERIMENT_SEEDS:
        known = ", ".join(sorted(EXPERIMENT_SEEDS))
        console.print(f"[red]Unknown experiment {experiment!r}. Known: {known}[/red]")
        raise typer.Exit(code=1)

    db = _db()
    created = []
    for draft in EXPERIMENT_SEEDS[experiment]:
        candidate = draft.to_candidate()
        # Seed ideas are hypotheses, not confirmed mechanisms.
        db.save_candidate(candidate)
        created.append(candidate)

    for c in created:
        console.print(f"  [green]seeded[/green] {c.id} — {c.name}")


# ---------------------------------------------------------------------------
# Phase 2: research (implemented)
# ---------------------------------------------------------------------------


def _research_service(mock_fixtures: bool):
    from blockchain_rd_lab.agents import MockLLMProvider
    from blockchain_rd_lab.research.service import ResearchService

    db = _db()
    if mock_fixtures:
        provider = MockLLMProvider()
        from blockchain_rd_lab.research.agents import fixture_research_responses
        from blockchain_rd_lab.schemas import CandidateStatus

        briefs = [
            _brief_of(c)
            for c in db.list_candidates(status=CandidateStatus.GENERATED)
        ]
        if not briefs:
            console.print("[yellow]No GENERATED candidates to research.[/yellow]")
            raise typer.Exit(code=0)
        for response in fixture_research_responses(briefs):
            provider.queue_response(response)
    else:
        provider = _provider_from_config()
        if isinstance(provider, MockLLMProvider):
            console.print(
                "[red]runtime.llm_provider is 'mock' with no queued responses.[/red]\n"
                "Use --mock-fixtures for the offline demo, or configure a real\n"
                "provider in config/lab.yaml (§30)."
            )
            raise typer.Exit(code=2)
    return ResearchService(provider, db, artifacts_dir=REPO_ROOT / "research" / "prior_art")


def _brief_of(cand):
    from blockchain_rd_lab.research import CandidateBrief

    return CandidateBrief.from_candidate(cand)


def _run_research(
    service,
    candidate_id: str | None,
    limit: int | None,
) -> None:
    if candidate_id is not None:
        cand = service.database.get_candidate(candidate_id)
        if cand is None:
            console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
            raise typer.Exit(code=1)
        results = [service.research_candidate(cand)]
    else:
        results = service.research_all(limit=limit)

    table = Table(title=f"Research — {len(results)} candidate(s)")
    table.add_column("Candidate", style="cyan")
    table.add_column("Novelty")
    table.add_column("Coherence", justify="right")
    table.add_column("Demand", justify="right")
    table.add_column("Status")
    for r in results:
        cand = service.database.get_candidate(r.candidate_id)
        table.add_row(
            r.candidate_id,
            r.prior_art.novelty_class.value if r.prior_art else "—",
            f"{r.economist.economic_coherence_score:.1f}" if r.economist else "—",
            f"{r.market.market_demand_score:.1f}" if r.market else "—",
            cand.status.value if cand else "?",
        )
    console.print(table)

    rejected = [r for r in results if r.rejected]
    if rejected:
        console.print(f"[red]{len(rejected)} rejected (fatal economic concern):[/red]")
        for r in rejected:
            console.print(f"  [red]• {r.candidate_id}: {r.rejection_reason}[/red]")
    errs = [(r.candidate_id, e) for r in results for e in r.errors]
    if errs:
        console.print("[dim]Agent errors (candidates left in place for retry):[/dim]")
        for cid, e in errs[:10]:
            console.print(f"  [dim]• {cid}: {e}[/dim]")


@app.command("research")
def research(
    candidate_id: str | None = typer.Argument(default=None),
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 50,
    mock_fixtures: Annotated[
        bool,
        typer.Option("--mock-fixtures", help="Use offline fixture reports"),
    ] = False,
) -> None:
    """Run Prior-Art, Economist, and Market agents on candidates (Phase 2)."""
    service = _research_service(mock_fixtures)
    _run_research(service, candidate_id, limit)


@app.command("prior-art")
def prior_art(
    candidate_id: str | None = typer.Argument(default=None),
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 50,
    mock_fixtures: Annotated[
        bool,
        typer.Option("--mock-fixtures", help="Use offline fixture reports"),
    ] = False,
) -> None:
    """Run only the Prior-Art agent on candidates (Phase 2, §12)."""
    from blockchain_rd_lab.research.service import ResearchService

    db = _db()
    provider = _provider_from_config()
    service = ResearchService(provider, db, artifacts_dir=None)
    if candidate_id is not None:
        cand = db.get_candidate(candidate_id)
        if cand is None:
            console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
            raise typer.Exit(code=1)
        cands = [cand]
    else:
        from blockchain_rd_lab.schemas import CandidateStatus

        cands = db.list_candidates(status=CandidateStatus.GENERATED, limit=limit)

    for cand in cands:
        brief = _brief_of(cand)
        try:
            result, _ = service.prior_art_agent.execute(brief)
            from blockchain_rd_lab.research import PriorArtReport

            if not isinstance(result, PriorArtReport):
                raise TypeError("PriorArtAgent returned unexpected output type")
            report = result
            cand.novelty_class = report.novelty_class
            cand.novelty_score = report.novelty_score
            if cand.status.value == "generated":
                cand.transition(CandidateStatus.RESEARCHING)
                cand.transition(CandidateStatus.PRIOR_ART_CHECKED)
            db.save_candidate(cand)
            service._persist_prior_art(cand.id, report)
            console.print(
                f"  {cand.id} — {cand.name}: "
                f"[cyan]{report.novelty_class.value}[/cyan] "
                f"(confidence {report.confidence:.2f})"
            )
        except Exception as exc:
            console.print(f"  [red]{cand.id} failed:[/red] {exc}")


@app.command("filter")
def filter_cmd(
    target: Annotated[int, typer.Option("--target", "-t", min=1)] = 20,
) -> None:
    """Deterministic funnel cut: keep top candidates after prior-art (§7)."""
    from blockchain_rd_lab.research.service import ResearchFilter

    db = _db()
    outcome = ResearchFilter(target=target).apply(db)

    table = Table(title=f"Filter — {outcome.kept} kept of {outcome.considered}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("considered", str(outcome.considered))
    table.add_row("kept", str(outcome.kept))
    table.add_row("rejected (class A)", str(outcome.rejected_class_a))
    table.add_row("rejected (class B)", str(outcome.rejected_class_b))
    overflow = outcome.rejected - outcome.rejected_class_a - outcome.rejected_class_b
    table.add_row("rejected (overflow)", str(overflow))
    console.print(table)

    if outcome.rejected_details:
        console.print("[dim]Rejections:[/dim]")
        for d in outcome.rejected_details[:15]:
            console.print(f"  [dim]• {d}[/dim]")
    if outcome.kept_ids:
        console.print("[green]Kept for Phase 3 (formalization):[/green]")
        for cid in outcome.kept_ids:
            console.print(f"  [green]•[/green] {cid}")


# ---------------------------------------------------------------------------
# Phase 3: formalization (implemented)
# ---------------------------------------------------------------------------


def _formalization_summary_table(
    title: str,
    attempted: int,
    formalized: int,
    failed: int,
    versions: dict,
) -> Table:
    table = Table(title=title)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("attempted", str(attempted))
    table.add_row("formalized", str(formalized))
    table.add_row("failed", str(failed))
    table.add_row("model versions stored", str(len(versions)))
    return table


@app.command("formalize")
def formalize(
    candidate_id: str | None = typer.Argument(default=None),
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 50,
    mock_fixtures: Annotated[
        bool,
        typer.Option(
            "--mock-fixtures", help="Use offline fixture models (same validation/storage path)"
        ),
    ] = False,
) -> None:
    """Turn researched candidates into formal mathematical models (Phase 3, §13)."""
    from blockchain_rd_lab.formalization import FormalizationSummary
    from blockchain_rd_lab.formalization.service import FormalizationService

    db = _db()
    if mock_fixtures:
        # Offline path: no LLM needed, but keep provider plumbing for the service.
        from blockchain_rd_lab.agents import MockLLMProvider

        service = FormalizationService(MockLLMProvider(), db)
    else:
        from blockchain_rd_lab.agents import MockLLMProvider

        provider = _provider_from_config()
        if isinstance(provider, MockLLMProvider):
            console.print(
                "[red]runtime.llm_provider is 'mock' with no queued responses.[/red]\n"
                "Use --mock-fixtures for the offline demo, or configure a real\n"
                "provider in config/lab.yaml (§30)."
            )
            raise typer.Exit(code=2)
        service = FormalizationService(provider, db)

    if candidate_id is not None:
        cand = db.get_candidate(candidate_id)
        if cand is None:
            console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
            raise typer.Exit(code=1)
        if mock_fixtures:
            summary = FormalizationSummary()
            result = service._formalize_one_fixture(cand)
            summary.attempted = 1
            if result.formalized:
                summary.formalized = 1
                assert result.model is not None
                summary.model_versions[cand.id] = result.model.version
            else:
                summary.failed = 1
                summary.errors[cand.id] = result.error
        else:
            result = service.formalize_candidate(cand)
            summary = FormalizationSummary(
                attempted=1,
                formalized=1 if result.formalized else 0,
                failed=0 if result.formalized else 1,
                model_versions={cand.id: result.model.version} if result.model else {},
                errors={} if result.formalized else {cand.id: result.error},
            )
        console.print(
            _formalization_summary_table(
                f"Formalization — {summary.formalized} of {summary.attempted}",
                summary.attempted,
                summary.formalized,
                summary.failed,
                summary.model_versions,
            )
        )
        return

    if mock_fixtures:
        summary = service.formalize_all_fixtures(
            limit=limit, artifacts_dir=REPO_ROOT / "formalization" / "models"
        )
    else:
        summary = service.formalize_all(limit=limit)

    console.print(
        _formalization_summary_table(
            f"Formalization — {summary.formalized} of {summary.attempted}",
            summary.attempted,
            summary.formalized,
            summary.failed,
            summary.model_versions,
        )
    )
    if summary.errors:
        console.print("[dim]Failures (candidates left in place for retry):[/dim]")
        for cid, err in list(summary.errors.items())[:10]:
            console.print(f"  [dim]• {cid}: {err}[/dim]")


# ---------------------------------------------------------------------------
# Phase 4: simulation (implemented)
# ---------------------------------------------------------------------------


@app.command()
def simulate(
    candidate_id: str | None = typer.Argument(default=None),
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 50,
    trials: Annotated[int, typer.Option("--trials", "-t", min=1)] = 30,
    sweep_points: Annotated[int, typer.Option("--sweep-points", min=2)] = 5,
    seed: Annotated[int, typer.Option("--seed", min=0)] = 7,
    steps: Annotated[int, typer.Option("--steps", min=10)] = 120,
) -> None:
    """Run §15 scenario battery + Monte Carlo + sweep on formalized candidates."""
    from blockchain_rd_lab.schemas import CandidateStatus
    from blockchain_rd_lab.simulation.service import SimulationService

    db = _db()
    service = SimulationService(db, seed=seed, steps=steps)

    if candidate_id is not None:
        cand = db.get_candidate(candidate_id)
        if cand is None:
            console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
            raise typer.Exit(code=1)
        ok = (CandidateStatus.FORMALIZED, CandidateStatus.SIMULATING)
        if cand.status not in ok:
            console.print(
                f"[red]Candidate is {cand.status.value!r}; simulation requires "
                "formalized.[/red]"
            )
            raise typer.Exit(code=1)
        outcomes = {
            cand.id: service.simulate_candidate(
                cand, mc_trials=trials, sweep_points=sweep_points
            )
        }
    else:
        outcomes = service.simulate_all(
            limit=limit,
            mc_trials=trials,
            sweep_points=sweep_points,
            artifacts_dir=REPO_ROOT / "simulation" / "runs",
        )

    table = Table(title=f"Simulation — {len(outcomes)} candidate(s)")
    table.add_column("Candidate", style="cyan")
    table.add_column("MC mean final", justify="right")
    table.add_column("MC p95", justify="right")
    table.add_column("Failed scenarios", justify="right")
    table.add_column("Status", justify="left")
    for cid, outcome in outcomes.items():
        cand = db.get_candidate(cid)
        mc = outcome.get("monte_carlo", {})
        n_failed = len(outcome.get("hard_failures", [])) or (
            1 if outcome.get("error") else 0
        )
        table.add_row(
            cid,
            f"{mc.get('mean_final', float('nan')):.2f}" if mc else "—",
            f"{mc.get('p95_final', float('nan')):.2f}" if mc else "—",
            str(n_failed),
            cand.status.value if cand else "?",
        )
    console.print(table)

    for cid, outcome in outcomes.items():
        if outcome.get("error"):
            console.print(f"  [red]{cid} failed:[/red] {outcome['error']}")
        for k, fails in outcome.get("hard_failures", [])[:5]:
            console.print(f"  [red]{cid} scenario {k}:[/red] {fails[0]}")


# ---------------------------------------------------------------------------
# Phase 5+ command stubs (§7) — declared now, implemented later
# ---------------------------------------------------------------------------


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
