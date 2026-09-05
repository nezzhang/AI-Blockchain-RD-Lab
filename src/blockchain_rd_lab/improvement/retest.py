"""Retest orchestration service (§3/§34 loop: RETEST → SIMULATING → RED_TEAM).

After an improvement, the patched model v(n+1) must re-run the SAME
deterministic battery (§15 scenarios, Monte Carlo, sweep — with §21
reproducibility records) and then face a FRESH adversarial review. Only
the full loop decides: the patched candidate re-enters at SIMULATING,
red-team re-attacks it, and the §20 gate re-evaluates (fatal + profitable
→ REJECTED; otherwise → RED_TEAM for scoring).

Nothing here is new science — it composes the Phase 4 + Phase 5 services
over the new model version (§2: code tests; evidence decides).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from blockchain_rd_lab.agents.base import LLMProvider
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.redteam.service import RedTeamService
from blockchain_rd_lab.schemas import Candidate, CandidateStatus
from blockchain_rd_lab.simulation.service import SimulationService


class RetestOutcome(BaseModel):
    """Result of retesting one improved candidate."""

    model_config = ConfigDict(validate_assignment=True)

    candidate_id: str
    resimulated: bool = False
    re_attacked: bool = False
    final_status: str = ""
    rejected_by_gate: bool = False
    errors: list[str] = Field(default_factory=list)


class RetestRunSummary(BaseModel):
    """Aggregate over one retest-all run."""

    model_config = ConfigDict(validate_assignment=True)

    attempted: int = 0
    completed: int = 0
    rejected_by_gate: int = 0
    errors: int = 0
    per_candidate: list[RetestOutcome] = Field(default_factory=list)


class RetestService:
    """Re-simulates and re-attacks improved candidates (§34 loop)."""

    def __init__(
        self,
        provider: LLMProvider,
        database: LabDatabase,
        artifacts_dir: Path | None = None,
        redteam_artifacts_dir: Path | None = None,
    ) -> None:
        self.provider = provider
        self.database = database
        self.artifacts_dir = artifacts_dir
        self.simulation = SimulationService(database, seed=7, steps=60)
        self.redteam = RedTeamService(
            provider, database, artifacts_dir=redteam_artifacts_dir
        )

    def retest_candidate(self, candidate: Candidate) -> RetestOutcome:
        outcome = RetestOutcome(candidate_id=candidate.id)
        try:
            if candidate.status is not CandidateStatus.RETEST:
                outcome.errors.append(
                    f"status {candidate.status.value} is not retest"
                )
                return outcome

            # 1) RETEST → SIMULATING: re-run the battery over model v(n+1).
            candidate.transition(CandidateStatus.SIMULATING)
            self.database.save_candidate(candidate)
            sim_result = self.simulation.simulate_candidate(
                candidate, mc_trials=20, sweep_points=5
            )
            if sim_result.get("error") or sim_result.get("hard_failures"):
                outcome.errors.append("re-simulation reported failures")
                return outcome
            outcome.resimulated = True

            # 2) SIMULATING → RED_TEAM: fresh adversarial review; the §20
            #    gate inside _apply_findings may REJECT (fatal + profitable)
            #    or advance to RED_TEAM for scoring.
            result = self.redteam.redteam_candidate(candidate)
            if result.errors and not result.complete:
                outcome.errors.extend(result.errors[:3])
                return outcome
            outcome.re_attacked = True
            outcome.rejected_by_gate = candidate.status is CandidateStatus.REJECTED
            outcome.final_status = candidate.status.value
        except Exception as exc:  # §35 isolation
            outcome.errors.append(f"{type(exc).__name__}: {exc}")
        return outcome

    def retest_all(
        self,
        limit: int | None = None,
        only_status: CandidateStatus | None = CandidateStatus.RETEST,
    ) -> RetestRunSummary:
        summary = RetestRunSummary()
        candidates = self.database.list_candidates(status=only_status, limit=limit)
        summary.attempted = len(candidates)
        for cand in candidates:
            outcome = self.retest_candidate(cand)
            summary.per_candidate.append(outcome)
            if outcome.errors:
                summary.errors += 1
            elif outcome.re_attacked:
                summary.completed += 1
                if outcome.rejected_by_gate:
                    summary.rejected_by_gate += 1
        return summary
