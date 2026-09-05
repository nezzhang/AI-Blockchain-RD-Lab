"""§34 Automated Pipeline: discover → research → filter → formalize →
simulate → red team → score/rank → report, with §35 interruption safety.

Resumability model: every stage consumes candidates by STATUS (its input
state) and advances them through the §11 state machine. A pipeline run is
therefore idempotent per stage — interrupted runs can be re-invoked and
they continue from whatever state the database holds. No in-memory
checkpoints, no lost progress: the database IS the checkpoint.

Failures are isolated per candidate (§35): an LLM call failing never
kills the run; the candidate stays in its prior status and the stage
report records the error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from blockchain_rd_lab.agents.base import LLMProvider
from blockchain_rd_lab.cost import BudgetExceededError
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus


class StageResult(BaseModel):
    """Outcome of one pipeline stage (§35: errors recorded, not raised)."""

    model_config = ConfigDict(validate_assignment=True)

    stage: str
    processed: int = 0
    advanced: int = 0
    errors: list[str] = Field(default_factory=list)
    skipped: bool = False  # nothing in the input state


class PipelineSummary(BaseModel):
    """Full pipeline run summary."""

    model_config = ConfigDict(validate_assignment=True)

    stages: list[StageResult] = Field(default_factory=list)
    finalists: list[str] = Field(default_factory=list)
    recommended_id: str | None = None
    completed: bool = False
    budget_exhausted: bool = False

    @property
    def total_errors(self) -> int:
        return sum(len(s.errors) for s in self.stages)


class PipelineService:
    """Runs the full §34 research loop with resume-on-rerun semantics."""

    # Stage names in §34 order.
    STAGES = (
        "discover",
        "research",
        "filter",
        "formalize",
        "simulate",
        "redteam",
        "improve",
        "retest",
        "score",
        "report",
    )

    def __init__(
        self,
        provider: LLMProvider,
        database: LabDatabase,
        repo_root: Path,
        research_config: Any = None,
        token_budget: int | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        """§31 cost control: the provider is wrapped in a BudgetGuard so
        one run cannot overspend; identical agent calls hit the response
        cache instead of re-paying. Budget exhausted → fail closed.
        """
        from blockchain_rd_lab.cost import BudgetGuard, ResponseCache, TokenBudget

        self.raw_provider = provider
        budget = TokenBudget(
            token_budget if token_budget is not None else 2_000_000
        )
        cache = ResponseCache(cache_dir or (repo_root / ".cache" / "llm"))
        self.provider: LLMProvider = BudgetGuard(provider, budget, cache)
        self.budget = budget
        self.database = database
        self.repo_root = repo_root
        self.research_config = research_config

    # -- stage implementations --------------------------------------------------

    def _stage_discover(self, count: int) -> StageResult:
        from blockchain_rd_lab.discovery.service import DiscoveryService

        result = StageResult(stage="discover")
        service = DiscoveryService(
            self.provider,
            self.database,
            research_config=self.research_config,
            ideas_dir=self.repo_root / "ideas" / "active",
        )
        summary = service.discover(count=count, avoid_existing=True)
        result.processed = summary.generated
        result.advanced = summary.stored
        result.errors.extend(summary.errors[:10])
        return result

    def _stage_research(self) -> StageResult:
        from blockchain_rd_lab.research.service import ResearchService

        result = StageResult(stage="research")
        # §35 resume: research interrupted mid-run leaves candidates at
        # RESEARCHING (the transition fires before the agent calls); a
        # fresh run must pick up BOTH fresh GENERATED candidates and
        # stranded RESEARCHING ones — the database is the checkpoint.
        stranded = self.database.list_candidates(status=CandidateStatus.RESEARCHING)
        generated = self.database.list_candidates(status=CandidateStatus.GENERATED)
        if not generated and not stranded:
            result.skipped = True
            return result
        service = ResearchService(
            self.provider, self.database, artifacts_dir=None
        )
        results = service.research_all(
            limit=None, only_status=CandidateStatus.GENERATED
        )
        # Stranded RESEARCHING candidates re-run their (replayed or fresh)
        # agent calls; _apply_findings completes the transition.
        for cand in stranded:
            results.append(service.research_candidate(cand))
        result.processed = len(results)
        for r in results:
            if r.errors:
                result.errors.extend(r.errors[:3])
            else:
                result.advanced += 1
        return result

    def _stage_filter(self, target: int) -> StageResult:
        from blockchain_rd_lab.research.service import ResearchFilter

        result = StageResult(stage="filter")
        checked = self.database.list_candidates(
            status=CandidateStatus.PRIOR_ART_CHECKED
        )
        if not checked:
            result.skipped = True
            return result
        outcome = ResearchFilter(target=target).apply(self.database)
        result.processed = outcome.considered
        result.advanced = outcome.kept
        return result

    def _stage_formalize(self) -> StageResult:
        from blockchain_rd_lab.formalization.service import FormalizationService

        result = StageResult(stage="formalize")
        pending = self.database.list_candidates(
            status=CandidateStatus.PRIOR_ART_CHECKED
        )
        if not pending:
            result.skipped = True
            return result
        service = FormalizationService(self.provider, self.database)
        summary = service.formalize_all(limit=None)
        result.processed = summary.attempted
        result.advanced = summary.formalized
        return result

    def _stage_simulate(self) -> StageResult:
        from blockchain_rd_lab.simulation.service import SimulationService

        result = StageResult(stage="simulate")
        formalized = self.database.list_candidates(status=CandidateStatus.FORMALIZED)
        # Also resume candidates already simulating (e.g. from Phase 4 runs).
        simulating = self.database.list_candidates(status=CandidateStatus.SIMULATING)
        if not formalized and not simulating:
            result.skipped = True
            return result
        service = SimulationService(self.database, seed=7, steps=60)
        outcomes = service.simulate_all(limit=None, mc_trials=20, sweep_points=5)
        result.processed = len(outcomes)
        for cid, outcome in outcomes.items():
            if outcome.get("error"):
                result.errors.append(f"{cid}: {outcome['error']}")
            elif not outcome.get("hard_failures"):
                result.advanced += 1
        return result

    def _stage_redteam(self) -> StageResult:
        from blockchain_rd_lab.redteam.service import RedTeamService

        result = StageResult(stage="redteam")
        simulating = self.database.list_candidates(status=CandidateStatus.SIMULATING)
        if not simulating:
            result.skipped = True
            return result
        service = RedTeamService(
            self.provider, self.database, artifacts_dir=self.repo_root / "redteam" / "runs"
        )
        summary = service.redteam_all(limit=None)
        result.processed = summary.attempted
        result.advanced = summary.completed
        for row in summary.per_candidate:
            if row.get("errors"):
                result.errors.append(f"{row['candidate_id']}: {row['errors'][0]}")
        return result

    def _stage_improve(self) -> StageResult:
        from blockchain_rd_lab.improvement.service import ImprovementService

        result = StageResult(stage="improve")
        redteam = self.database.list_candidates(status=CandidateStatus.RED_TEAM)
        if not redteam:
            result.skipped = True
            return result
        service = ImprovementService(self.provider, self.database)
        summary = service.improve_all(limit=None)
        result.processed = summary.attempted
        result.advanced = summary.improved
        for row in summary.per_candidate:
            if row.errors:
                result.errors.append(f"{row.candidate_id}: {row.errors[0]}")
        return result

    def _stage_retest(self) -> StageResult:
        from blockchain_rd_lab.improvement.retest import RetestService

        result = StageResult(stage="retest")
        pending = self.database.list_candidates(status=CandidateStatus.RETEST)
        if not pending:
            result.skipped = True
            return result
        service = RetestService(
            self.provider,
            self.database,
            redteam_artifacts_dir=self.repo_root / "redteam" / "runs",
        )
        summary = service.retest_all(limit=None)
        result.processed = summary.attempted
        result.advanced = summary.completed
        for row in summary.per_candidate:
            if row.errors:
                result.errors.append(f"{row.candidate_id}: {row.errors[0]}")
        return result

    def _stage_score(self, finalists: int) -> StageResult:
        from blockchain_rd_lab.ranking.service import RankingService

        result = StageResult(stage="score")
        service = RankingService(self.database)
        # Scores every RED_TEAM candidate, then ranks (which also promotes
        # the top N to FINALIST) — §34 score + rank.
        redteam = self.database.list_candidates(status=CandidateStatus.RED_TEAM)
        scored_exists = bool(
            self.database.list_candidates(status=CandidateStatus.SCORED, limit=1)
        )
        if not redteam and not scored_exists:
            # allow resume when candidates are already SCORED/FINALIST
            result.skipped = True
            return result
        for cand in redteam:
            service.score_candidate(cand)
        selection = service.select_finalists(count=finalists)
        result.processed = len(redteam)
        result.advanced = len(selection.finalists)
        return result

    def _stage_report(self) -> StageResult:
        from blockchain_rd_lab.archive import ArchiveBuilder
        from blockchain_rd_lab.reporting.service import ReportBuilder

        result = StageResult(stage="report")
        builder = ReportBuilder(self.database)
        outcome = builder.write_reports(self.repo_root / "reports")
        archive = ArchiveBuilder(self.database).build(self.repo_root / "ideas")
        result.processed = len(outcome.dossiers_written) + archive.rejected_indexed
        result.advanced = len(outcome.dossiers_written)
        return result

    # -- entry point ---------------------------------------------------------------

    def run(
        self,
        count: int = 10,
        target: int = 20,
        finalists: int = 5,
        stop_after: str | None = None,
    ) -> PipelineSummary:
        """Execute §34 stages in order; resumable at every boundary.

        `stop_after` interrupts the pipeline after the named stage — the
        database state lets a later `lab pipeline` invocation resume.
        """
        summary = PipelineSummary()
        stages: list[tuple[str, Any]] = [
            ("discover", lambda: self._stage_discover(count)),
            ("research", lambda: self._stage_research()),
            ("filter", lambda: self._stage_filter(target)),
            ("formalize", lambda: self._stage_formalize()),
            ("simulate", lambda: self._stage_simulate()),
            ("redteam", lambda: self._stage_redteam()),
            ("improve", lambda: self._stage_improve()),
            ("retest", lambda: self._stage_retest()),
            ("score", lambda: self._stage_score(finalists)),
            ("report", lambda: self._stage_report()),
        ]
        for name, run_stage in stages:
            try:
                stage_result = run_stage()
            except BudgetExceededError as exc:
                # §31: the run's token ceiling is crossed. Stop cleanly —
                # the database state remains resumable with a fresh budget
                # (§35). Record and stop; do not run further stages.
                summary.stages.append(
                    StageResult(
                        stage=name,
                        errors=[f"budget exhausted: {exc}"],
                    )
                )
                summary.budget_exhausted = True
                break
            summary.stages.append(stage_result)
            if stop_after == name:
                break

        # §31: persist the usage ledger for this run (auditable cost).
        from blockchain_rd_lab.cost import UsageLedger

        ledger = UsageLedger.from_budget(f"pipeline-{self._run_stamp()}", self.budget)
        ledger.to_artifact(self.repo_root / "reports" / "usage-latest.json")

        from blockchain_rd_lab.reporting.service import ReportBuilder

        lab = ReportBuilder(self.database).build_lab_report()
        summary.finalists = list(lab.finalists)
        summary.recommended_id = lab.recommended_id
        summary.completed = stop_after is None
        return summary

    def _run_stamp(self) -> str:
        """Deterministic-enough run id (time-based, not evidence)."""
        from datetime import UTC, datetime

        return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
