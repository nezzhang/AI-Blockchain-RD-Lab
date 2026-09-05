"""Lab CLI (§7).

Phase 1: working `init`, `status`, `score`, `search`, `discover`, `seed`.
The remaining pipeline commands (research, prior-art, formalize, simulate,
redteam, rank, report, pipeline) are stubs that fail fast with a pointer to
their future phase.
"""

from __future__ import annotations

from pathlib import Path
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
    # Phase 6: scoring advances the state machine (RED_TEAM -> SCORED) and
    # applies the §20 gate consistently with the ranking service.
    from blockchain_rd_lab.ranking.service import RankingService

    result = RankingService(db, engine).score_candidate(candidate)

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
    combine: Annotated[
        bool,
        typer.Option(
            "--combine",
            help="Steer discovery with §18 mechanism-combination hints",
        ),
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

    hints: list[str] | None = None
    if combine:
        from blockchain_rd_lab.combinator.engine import MechanismCombinator

        cands = db.list_candidates(limit=None)
        comb = MechanismCombinator()
        proposed = comb.propose(cands, max_hints=max(count, 1))
        hints = [h.hint_text() for h in proposed]
        if hints:
            console.print("[cyan]§18 combination hints:[/cyan]")
            for h in hints[:5]:
                console.print(f"  • {h}")

    service = DiscoveryService(
        provider, db, research_config=research, ideas_dir=REPO_ROOT / "ideas" / "active"
    )
    summary = service.discover(
        count=count, avoid_existing=not no_avoid, combination_hints=hints
    )

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


@app.command("combine")
def combine(
    max_hints: Annotated[
        int, typer.Option("--max", "-m", min=1, help="Maximum pairs to show")
    ] = 10,
    all_pairs: Annotated[
        bool,
        typer.Option("--all", help="Show scored pairs below the emit threshold too"),
    ] = False,
) -> None:
    """Inspect §18 mechanism combinations (families mined from the corpus)."""
    from blockchain_rd_lab.combinator.engine import MechanismCombinator

    db = _db()
    cands = db.list_candidates(limit=None)
    comb = MechanismCombinator()

    families = comb.mine_families(cands)
    fam_table = Table(title=f"Mechanism families — {len(families)} found (§17)")
    fam_table.add_column("Family", style="cyan")
    fam_table.add_column("Members", justify="right")
    fam_table.add_column("Vocabulary hits")
    for f in families:
        fam_table.add_row(f.family, str(len(f.member_ids)), str(len(f.keywords)))
    console.print(fam_table)

    from itertools import combinations

    pairs = sorted(families, key=lambda f: f.family)
    rows = []
    for a, b in combinations(pairs, 2):
        bridge = comb.bridge_strength(a, b)
        compat = comb.compatibility(a, b)
        score = 0.5 * bridge + 0.5 * compat
        rows.append((a, b, bridge, compat, score))
    rows.sort(key=lambda r: -r[4])
    emitted = [r for r in rows if r[4] >= comb.min_score]
    shown = rows if all_pairs else emitted
    pair_table = Table(
        title=f"Combination pairs — {len(shown)} shown "
        f"({len(emitted)} above the emit threshold)"
    )
    pair_table.add_column("Family A", style="cyan")
    pair_table.add_column("Family B", style="cyan")
    pair_table.add_column("Bridge", justify="right")
    pair_table.add_column("Compat", justify="right")
    pair_table.add_column("Score", justify="right")
    pair_table.add_column("Emits")
    for a, b, bridge, compat, score in shown[:max_hints]:
        pair_table.add_row(
            a.family,
            b.family,
            f"{bridge:.3f}",
            f"{compat:.3f}",
            f"{score:.3f}",
            "yes" if score >= comb.min_score else "no",
        )
    console.print(pair_table)
    if not shown:
        console.print(
            "[dim]No pairs above the §18 gates. Add candidates across more "
            "mechanism families (see `lab seed`, `lab discover`).[/dim]"
        )


_bridge_cmd = typer.Typer(help="Agent-as-LLM bridge (§30): answer pending requests")
app.add_typer(_bridge_cmd, name="bridge")


def _bridge_provider():
    from blockchain_rd_lab.agents.bridge import AgentBridgeProvider

    cfg = load_config()
    return AgentBridgeProvider(bridge_dir=cfg.providers["bridge"].bridge_dir)


@_bridge_cmd.command("list")
def bridge_list(
    all_requests: Annotated[
        bool, typer.Option("--all", help="Include answered requests")
    ] = False,
) -> None:
    """List pending (or all) bridge requests waiting for an answer."""
    provider = _bridge_provider()
    requests = provider.list_requests(status=None if all_requests else "pending")
    if not requests:
        console.print("[green]No pending bridge requests.[/green]")
        return
    table = Table(title=f"Bridge requests — {len(requests)} pending")
    table.add_column("ID", style="cyan")
    table.add_column("Schema")
    table.add_column("Created")
    table.add_column("Preview", overflow="fold")
    for r in requests:
        last = r["messages"][-1]["content"] if r.get("messages") else ""
        preview = last.replace("\n", " ")[:80]
        table.add_row(r["id"], r.get("schema", ""), r.get("created_at", ""), preview)
    console.print(table)


@_bridge_cmd.command("show")
def bridge_show(request_id: str) -> None:
    """Print a full bridge request (prompt + schema + template)."""
    provider = _bridge_provider()

    req_path = provider.requests_dir / f"{request_id}.json"
    if not req_path.exists():
        console.print(f"[red]No request {request_id}.[/red]")
        raise typer.Exit(code=1)
    console.print(req_path.read_text(encoding="utf-8"))
    tpl_path = provider.requests_dir / f"{request_id}.template.json"
    if tpl_path.exists():
        console.print("\n[bold]--- answer template ---[/bold]")
        console.print(tpl_path.read_text(encoding="utf-8"))


@_bridge_cmd.command("answer")
def bridge_answer(
    request_id: str,
    answer: Annotated[
        str | None,
        typer.Argument(help="Inline JSON answer (or use --file)"),
    ] = None,
    answer_file: Annotated[
        Path | None,
        typer.Option("--file", help="Path to a JSON file with the answer"),
    ] = None,
) -> None:
    """Install an answer for a pending request (validated, then replayable)."""
    import json as _json

    if (answer is None) == (answer_file is None):
        console.print("[red]Give exactly one of: inline JSON or --file PATH.[/red]")
        raise typer.Exit(code=1)
    if answer_file is not None:
        payload = _json.loads(answer_file.read_text(encoding="utf-8"))
    elif answer is not None:
        payload = _json.loads(answer)
    else:  # pragma: no cover - guarded above
        raise typer.Exit(code=1)
    provider = _bridge_provider()
    try:
        path = provider.install_answer(request_id, payload)
    except Exception as exc:
        console.print(f"[red]Answer rejected:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Answer installed and validated:[/green] {path.name}")
    console.print(
        "Re-run the pipeline command to resume (§35: the database is the "
        "checkpoint; answered requests replay for free)."
    )


@_bridge_cmd.command("purge")
def bridge_purge() -> None:
    """Drop PENDING requests (answered answers are kept: replay is free)."""
    provider = _bridge_provider()
    n = provider.purge_pending()
    console.print(f"Purged {n} pending request(s). Answered answers kept.")


@app.command("graph")
def graph(
    candidate_id: Annotated[
        str | None,
        typer.Argument(help="Show only this idea's §33 subgraph"),
    ] = None,
    similar_attack: Annotated[
        str | None,
        typer.Option(
            "--similar-attack", help="Find historically similar attacks (§32 reuse)"
        ),
    ] = None,
    no_artifact: Annotated[
        bool, typer.Option("--no-artifact", help="Skip writing graph-latest.json")
    ] = False,
) -> None:
    """Inspect the §33 research knowledge graph (derived, deterministic)."""
    import json as _json

    from blockchain_rd_lab.graph.builder import GraphBuilder

    db = _db()
    builder = GraphBuilder(db)
    g = builder.build()

    if candidate_id is not None:
        node = g.node_by_id(candidate_id)
        if node is None:
            console.print(f"[red]Idea {candidate_id!r} not in the graph.[/red]")
            raise typer.Exit(code=1)
        sub = g.subgraph_for_idea(candidate_id)
        summary = builder.summary(sub)
        console.print(
            f"[bold]§33 subgraph for {candidate_id}[/bold] "
            f"({summary.nodes} nodes, {summary.edges} edges)"
        )
        for e in sub.edges:
            src = sub.node_by_id(e.source)
            tgt = sub.node_by_id(e.target)
            src_kind = src.kind.value if src else "?"
            tgt_kind = tgt.kind.value if tgt else "?"
            console.print(
                f"  • {e.source} -[{e.kind.value}]-> {e.target}"
                f"  [dim]{src_kind}→{tgt_kind}[/dim]"
            )
        return

    if similar_attack is not None:
        hits = builder.similar_attacks(g, similar_attack, limit=5)
        if not hits:
            console.print("[dim]No similar attacks on record.[/dim]")
            return
        table = Table(title=f"Similar attacks (§32 reuse) — {len(hits)}")
        table.add_column("Attack", style="cyan")
        table.add_column("Idea")
        table.add_column("Fixed")
        table.add_column("Fix summary")
        for h in hits:
            table.add_row(
                h.attack_label[:60],
                h.attacked_idea,
                "yes" if h.fixed_by else "no",
                (h.fix_summary or "—")[:60],
            )
        console.print(table)
        return

    summary = builder.summary(g)
    table = Table(
        title=f"Knowledge graph (§33) — {summary.nodes} nodes, {summary.edges} edges"
    )
    table.add_column("Node kind", style="cyan")
    table.add_column("Count", justify="right")
    for kind, count in sorted(summary.by_kind.items()):
        table.add_row(kind, str(count))
    table.add_row("[bold]attacks with fixes[/bold]", f"[bold]{summary.attacks_with_fixes}[/bold]")
    console.print(table)

    edge_kinds: dict[str, int] = {}
    for e in g.edges:
        edge_kinds[e.kind.value] = edge_kinds.get(e.kind.value, 0) + 1
    edges_table = Table(title="Relationships")
    edges_table.add_column("Edge kind", style="cyan")
    edges_table.add_column("Count", justify="right")
    for kind, count in sorted(edge_kinds.items()):
        edges_table.add_row(kind, str(count))
    console.print(edges_table)

    if not no_artifact:
        artifact = REPO_ROOT / "reports" / "graph-latest.json"
        payload = {
            "nodes": [n.model_dump(mode="json") for n in g.nodes],
            "edges": [e.model_dump(mode="json") for e in g.edges],
        }
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[green]Graph artifact:[/green] {artifact.name}")


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
# Phase 5: adversarial testing (implemented)
# ---------------------------------------------------------------------------


def _redteam_provider(mock_fixtures: bool, briefs):
    """Build the LLM provider; fixture mode queues one report set per brief."""
    from blockchain_rd_lab.agents import MockLLMProvider

    if mock_fixtures:
        provider = MockLLMProvider()
        from blockchain_rd_lab.redteam.agents import fixture_redteam_responses

        if not briefs:
            console.print("[yellow]No SIMULATING candidates to red-team.[/yellow]")
            raise typer.Exit(code=0)
        for response in fixture_redteam_responses(briefs):
            provider.queue_response(response)
        return provider
    provider = _provider_from_config()
    if isinstance(provider, MockLLMProvider):
        console.print(
            "[red]runtime.llm_provider is 'mock' with no queued responses.[/red]\n"
            "Use --mock-fixtures for the offline demo, or configure a real\n"
            "provider in config/lab.yaml (§30)."
        )
        raise typer.Exit(code=2)
    return provider


@app.command()
def redteam(
    candidate_id: str | None = typer.Argument(default=None),
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 50,
    mock_fixtures: Annotated[
        bool,
        typer.Option("--mock-fixtures", help="Use offline fixture reports"),
    ] = False,
) -> None:
    """Run Game-Theory/Security/Oracle/Red-Team agents on simulated candidates."""
    from blockchain_rd_lab.redteam.service import RedTeamService
    from blockchain_rd_lab.schemas import CandidateStatus

    db = _db()
    if candidate_id is not None:
        cand = db.get_candidate(candidate_id)
        if cand is None:
            console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
            raise typer.Exit(code=1)
        if cand.status is not CandidateStatus.SIMULATING:
            console.print(
                f"[red]Candidate is {cand.status.value!r}; red team requires "
                "simulating.[/red]"
            )
            raise typer.Exit(code=1)
        briefs = [_brief_of(cand)]
    else:
        cands = db.list_candidates(status=CandidateStatus.SIMULATING, limit=limit)
        briefs = [_brief_of(c) for c in cands]

    provider = _redteam_provider(mock_fixtures, briefs)
    service = RedTeamService(provider, db, artifacts_dir=REPO_ROOT / "redteam" / "runs")

    if candidate_id is not None and cand is not None:
        result = service.redteam_candidate(cand)
        summary_rows = [service._summary_row(cand, result)]
    else:
        summary = service.redteam_all(limit=limit)
        summary_rows = summary.per_candidate

    table = Table(title=f"Red Team — {len(summary_rows)} candidate(s)")
    table.add_column("Candidate", style="cyan")
    table.add_column("Verdict")
    table.add_column("Rejected", justify="right")
    table.add_column("Errors", justify="right")
    for row in summary_rows:
        table.add_row(
            str(row.get("candidate_id")),
            str(row.get("verdict") or "—"),
            "yes" if row.get("rejected") else "no",
            str(len(row.get("errors", []))),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# §34 loop: improve + retest (implemented)
# ---------------------------------------------------------------------------


@app.command()
def improve(
    candidate_id: str | None = typer.Argument(default=None),
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 50,
    mock_fixtures: Annotated[
        bool,
        typer.Option("--mock-fixtures", help="Use the offline fixture patch"),
    ] = False,
) -> None:
    """Propose patched models for red-teamed candidates (§34 improve).

    RED_TEAM -> IMPROVEMENT -> RETEST. The patched model must pass the
    same §13 integrity checks as any formalization (§2: the LLM never
    bypasses validation).
    """
    from blockchain_rd_lab.improvement.service import ImprovementService
    from blockchain_rd_lab.schemas import CandidateStatus

    db = _db()
    if candidate_id is not None:
        cand = db.get_candidate(candidate_id)
        if cand is None:
            console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
            raise typer.Exit(code=1)
        if cand.status is not CandidateStatus.RED_TEAM:
            console.print(
                f"[red]Candidate is {cand.status.value!r}; improve requires "
                "red_team.[/red]"
            )
            raise typer.Exit(code=1)

    provider = _improve_provider(mock_fixtures)
    service = ImprovementService(provider, db)

    if candidate_id is not None and cand is not None:
        outcomes = [service.improve_candidate(cand, offline=mock_fixtures)]
        attempted = 1
    else:
        summary = service.improve_all(limit=limit, offline=mock_fixtures)
        outcomes = summary.per_candidate
        attempted = summary.attempted

    table = Table(title=f"Improve — {attempted} candidate(s)")
    table.add_column("Candidate", style="cyan")
    table.add_column("Improved")
    table.add_column("New version", justify="right")
    table.add_column("Attacks fixed", justify="right")
    table.add_column("Reason / errors")
    for o in outcomes:
        reason = o.rejected_reason or "; ".join(o.errors) or "—"
        table.add_row(
            o.candidate_id,
            "yes" if o.improved else "no",
            str(o.new_version or "—"),
            str(o.attacks_addressed or "—"),
            reason[:80],
        )
    console.print(table)


@app.command()
def retest(
    candidate_id: str | None = typer.Argument(default=None),
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 50,
    mock_fixtures: Annotated[
        bool,
        typer.Option("--mock-fixtures", help="Use offline fixture reviews"),
    ] = False,
) -> None:
    """Re-simulate and re-attack improved candidates (§34 re-simulate).

    RETEST -> SIMULATING -> RED_TEAM (or REJECTED by the §20 gate). The
    patched model re-runs the same §15 battery and faces fresh adversarial
    review — evidence decides (§2).
    """
    from blockchain_rd_lab.improvement.retest import RetestService
    from blockchain_rd_lab.schemas import CandidateStatus

    db = _db()
    if candidate_id is not None:
        cand = db.get_candidate(candidate_id)
        if cand is None:
            console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
            raise typer.Exit(code=1)
        if cand.status is not CandidateStatus.RETEST:
            console.print(
                f"[red]Candidate is {cand.status.value!r}; retest requires "
                "retest (run `lab improve` first).[/red]"
            )
            raise typer.Exit(code=1)

    if mock_fixtures:
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        provider = build_pipeline_provider()
    else:
        provider = _provider_from_config()
    service = RetestService(
        provider, db, redteam_artifacts_dir=REPO_ROOT / "redteam" / "runs"
    )

    if candidate_id is not None and cand is not None:
        outcomes = [service.retest_candidate(cand)]
        attempted = 1
    else:
        summary = service.retest_all(limit=limit)
        outcomes = summary.per_candidate
        attempted = summary.attempted

    table = Table(title=f"Retest — {attempted} candidate(s)")
    table.add_column("Candidate", style="cyan")
    table.add_column("Re-simulated")
    table.add_column("Re-attacked")
    table.add_column("Final status")
    table.add_column("Errors")
    for o in outcomes:
        table.add_row(
            o.candidate_id,
            "yes" if o.resimulated else "no",
            "yes" if o.re_attacked else "no",
            o.final_status or "—",
            "; ".join(e[:60] for e in o.errors) or "—",
        )
    console.print(table)


def _improve_provider(mock_fixtures: bool):
    """Offline improvement uses the schema-aware fixture provider."""
    if mock_fixtures:
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        return build_pipeline_provider()
    from blockchain_rd_lab.agents import MockLLMProvider

    provider = _provider_from_config()
    if isinstance(provider, MockLLMProvider):
        console.print(
            "[red]runtime.llm_provider is 'mock' with no queued responses.[/red]\n"
            "Use --mock-fixtures for the offline demo, or configure a real\n"
            "provider in config/lab.yaml (§30)."
        )
        raise typer.Exit(code=2)
    return provider


# ---------------------------------------------------------------------------
# Phase 6: ranking (implemented)
# ---------------------------------------------------------------------------


@app.command()
def rank(
    finalists: Annotated[
        int, typer.Option("--finalists", "-f", min=1, help="Top N to select (§7)")
    ] = 5,
    limit: Annotated[int, typer.Option("--limit", "-l", min=1)] = 50,
    no_promote: Annotated[
        bool,
        typer.Option(
            "--no-promote", help="Rank only; do not transition SCORED -> FINALIST"
        ),
    ] = False,
) -> None:
    """Score red-teamed candidates, rank deterministically, select finalists."""
    from blockchain_rd_lab.ranking.service import RankingService
    from blockchain_rd_lab.schemas import CandidateStatus

    db = _db()
    service = RankingService(db)

    redteam = db.list_candidates(status=CandidateStatus.RED_TEAM, limit=limit)
    if not redteam and not db.list_candidates(status=CandidateStatus.SCORED, limit=1):
        console.print(
            "[yellow]No RED_TEAM or SCORED candidates to rank.[/yellow]\n"
            "Run `lab redteam` first (Phase 5)."
        )
        raise typer.Exit(code=0)

    # Score any RED_TEAM candidates first (deterministic engine, §19).
    for cand in redteam:
        service.score_candidate(cand)

    selection = service.select_finalists(
        count=finalists, promote=not no_promote
    )
    ranking = service.rank(limit=limit)

    # Persist the ranking artifact (§21-style run record).
    import json as _json

    out_dir = REPO_ROOT / "ranking"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ranking-latest.json").write_text(
        _json.dumps(
            {
                "finalists": [f.model_dump(mode="json") for f in selection.finalists],
                "ranking": [
                    r.model_dump(mode="json") for r in ranking.rows
                ],
                "rejected_by_gate": ranking.rejected_by_gate,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    table = Table(title=f"Ranking — {len(ranking.rows)} candidate(s)")
    table.add_column("#", justify="right")
    table.add_column("Candidate", style="cyan")
    table.add_column("Name")
    table.add_column("Score", justify="right")
    table.add_column("Imputed dims", justify="right")
    table.add_column("Status")
    for r in ranking.rows:
        is_finalist = any(f.candidate_id == r.candidate_id for f in selection.finalists)
        table.add_row(
            str(r.rank),
            r.candidate_id,
            r.name[:44],
            f"{r.overall_score:.4f}",
            str(len(r.imputed_dimensions)) if r.imputed_dimensions else "—",
            ("[bold]FINALIST[/bold]" if is_finalist else r.status),
        )
    console.print(table)

    console.print(
        f"Finalists (top {len(selection.finalists)} of "
        f"{selection.available} scored, §7): "
        + ", ".join(f.candidate_id for f in selection.finalists)
    )
    if ranking.rejected_by_gate:
        console.print(
            f"[red]{ranking.rejected_by_gate} candidate(s) excluded by the "
            "fatal-flaw gate (§20).[/red]"
        )


# ---------------------------------------------------------------------------
# Phase 7: reporting (implemented)
# ---------------------------------------------------------------------------


@app.command()
def report(
    candidate_id: str | None = typer.Argument(default=None),
    no_dossiers: Annotated[
        bool,
        typer.Option("--no-dossiers", help="Skip per-finalist dossiers"),
    ] = False,
) -> None:
    """Assemble research reports from stored evidence (Phase 7, §23)."""
    from pathlib import Path as _Path

    from blockchain_rd_lab.reporting.service import ReportBuilder

    db = _db()
    builder = ReportBuilder(db)

    if candidate_id is not None:
        cand = db.get_candidate(candidate_id)
        if cand is None:
            console.print(f"[red]Candidate {candidate_id!r} not found.[/red]")
            raise typer.Exit(code=1)
        from blockchain_rd_lab.ranking.service import RankingService
        from blockchain_rd_lab.schemas import CandidateStatus

        rank = None
        if cand.status in (CandidateStatus.SCORED, CandidateStatus.FINALIST):
            ranking = RankingService(db).rank()
            row = next((r for r in ranking.rows if r.candidate_id == cand.id), None)
            rank = row.rank if row else None
        dossier = builder.build_dossier(cand, rank=rank)
        console.print(dossier.to_markdown())
        return

    reports_dir = REPO_ROOT / "reports"
    outcome = builder.write_reports(
        reports_dir, include_dossiers=not no_dossiers
    )

    table = Table(title="Reports written")
    table.add_column("Artifact", style="cyan")
    table.add_column("Path")
    for path in outcome.dossiers_written:
        table.add_row("Finalist dossier", _Path(path).name)
    if outcome.lab_report_path:
        table.add_row("Lab report", _Path(outcome.lab_report_path).name)
    console.print(table)

    from blockchain_rd_lab.schemas import CandidateStatus

    finalists = db.list_candidates(status=CandidateStatus.FINALIST)
    if not finalists:
        console.print(
            "[yellow]No finalists yet; dossiers were skipped. Run `lab rank` "
            "first (Phase 6).[/yellow]"
        )
    if outcome.recommended_id:
        console.print(
            f"[bold]Recommended candidate (§7):[/bold] {outcome.recommended_id}"
        )


# ---------------------------------------------------------------------------
# Phase 8: pipeline (implemented, §34) + public research structure
# ---------------------------------------------------------------------------


@app.command()
def pipeline(
    count: Annotated[
        int, typer.Option("--count", "-n", min=1, help="Ideas to discover (§34)")
    ] = 10,
    target: Annotated[
        int, typer.Option("--target", "-t", min=1, help="Funnel cut after research (§7)")
    ] = 20,
    finalists: Annotated[
        int, typer.Option("--finalists", "-f", min=1, help="Finalist cut (§7)")
    ] = 5,
    stop_after: Annotated[
        str | None,
        typer.Option(
            "--stop-after",
            help="Interrupt after a stage (resume with a later run, §35)",
        ),
    ] = None,
    budget: Annotated[
        int,
        typer.Option(
            "--budget",
            min=0,
            help="Token budget for this run (§31); default from config",
        ),
    ] = 2_000_000,
    mock_fixtures: Annotated[
        bool,
        typer.Option("--mock-fixtures", help="Offline demo: fixture LLM responses"),
    ] = False,
) -> None:
    """Run the full research pipeline (§34): discover -> ... -> report."""
    from blockchain_rd_lab.pipeline import PipelineService

    db = _db()
    if mock_fixtures:
        from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider

        provider = build_pipeline_provider()
    else:
        from blockchain_rd_lab.agents import MockLLMProvider as _MockProvider

        provider = _provider_from_config()
        if isinstance(provider, _MockProvider):
            console.print(
                "[red]runtime.llm_provider is 'mock' with no queued responses.[/red]\n"
                "Use --mock-fixtures for the offline demo, or configure a real\n"
                "provider in config/lab.yaml (§30)."
            )
            raise typer.Exit(code=2)

    valid_stages = PipelineService.STAGES
    if stop_after is not None and stop_after not in valid_stages:
        console.print(
            f"[red]Unknown stage {stop_after!r}. Valid: {', '.join(valid_stages)}[/red]"
        )
        raise typer.Exit(code=1)

    service = PipelineService(
        provider,
        db,
        repo_root=REPO_ROOT,
        research_config=load_research(),
        token_budget=budget,
    )
    summary = service.run(
        count=count, target=target, finalists=finalists, stop_after=stop_after
    )

    # §31: report the run's token spend + cache savings.
    state = service.budget.state
    usage = Table(title="Token usage (§31)")
    usage.add_column("Metric", style="cyan")
    usage.add_column("Value", justify="right")
    usage.add_row("budget", str(state.budget))
    usage.add_row("spent", str(state.spent))
    usage.add_row("calls", str(state.calls))
    usage.add_row("cache hits (free)", str(state.cache_hits))
    console.print(usage)

    table = Table(title="Pipeline run (§34)")
    table.add_column("Stage", style="cyan")
    table.add_column("Processed", justify="right")
    table.add_column("Advanced", justify="right")
    table.add_column("Skipped", justify="right")
    table.add_column("Errors", justify="right")
    for stage in summary.stages:
        table.add_row(
            stage.stage,
            str(stage.processed),
            str(stage.advanced),
            "yes" if stage.skipped else "",
            str(len(stage.errors)),
        )
    console.print(table)

    for stage in summary.stages:
        for err in stage.errors[:5]:
            console.print(f"  [red]{stage.stage}:[/red] {err}")

    if summary.recommended_id:
        console.print(
            f"[bold]Recommended candidate (§7):[/bold] {summary.recommended_id}"
        )
    if summary.completed:
        console.print("[green]Pipeline complete.[/green]")
    else:
        console.print(
            "[yellow]Pipeline interrupted by --stop-after; re-run `lab "
            "pipeline` to resume from the database state (§35).[/yellow]"
        )


if __name__ == "__main__":
    app()
if __name__ == "__main__":
    app()
