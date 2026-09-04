"""Phase 6 orchestration: deterministic scoring, ranking, finalists (§19, §20, §7).

Per candidate in RED_TEAM: run the ScoringEngine (pure code — dimension
sub-scores in, weighted overall out; confirmed fatal flaws cap the score),
store `overall_score`, transition RED_TEAM → SCORED (§11). Then rank all
scored candidates deterministically (score desc, then name asc for stable
ties) and cut the top N finalists (§7: red-team → 5 finalists).

Confirmed-fatal candidates are already REJECTED by the Phase 5 gate and
never reach ranking; if one somehow arrives, it is counted as
`rejected_by_gate` and excluded from the ranked list (§20: never
averaged away, never ranked high).
"""

from __future__ import annotations

import json
from pathlib import Path

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.ranking import (
    FinalistSelection,
    RankedRow,
    RankingResult,
    RankingSummary,
)
from blockchain_rd_lab.schemas import (
    Candidate,
    CandidateStatus,
)
from blockchain_rd_lab.scoring import ScoringEngine, ScoringResult

# §7 funnel: red-team -> 5 finalists -> 1 recommended candidate.
DEFAULT_FINALISTS = 5


class RankingService:
    """Scores, ranks, and selects finalists — all deterministic (§2)."""

    def __init__(self, database: LabDatabase, engine: ScoringEngine | None = None) -> None:
        self.database = database
        self.engine = engine or ScoringEngine()

    # -- scoring ---------------------------------------------------------------

    def score_candidate(self, candidate: Candidate) -> ScoringResult:
        """Run the deterministic engine, persist overall_score, advance §11."""
        result = self.engine.score(candidate)

        if candidate.has_confirmed_fatal_flaw:
            # §20 belt-and-braces: confirmed flaws reject; they must never be
            # ranked. The Phase 5 gate should have caught this already.
            terminal = (
                CandidateStatus.REJECTED,
                CandidateStatus.FAILED,
                CandidateStatus.SUPERSEDED,
            )
            if candidate.status not in terminal:
                candidate.transition(CandidateStatus.REJECTED)
            self.database.save_candidate(candidate)
            return result

        candidate.overall_score = result.overall_score
        if candidate.status is CandidateStatus.RED_TEAM:
            candidate.transition(CandidateStatus.SCORED)
        self.database.save_candidate(candidate)
        return result

    def score_all(
        self,
        limit: int | None = None,
        only_status: CandidateStatus | None = CandidateStatus.RED_TEAM,
    ) -> list[ScoringResult]:
        """Score every candidate in the given state (§35: per-candidate isolation)."""
        candidates = self.database.list_candidates(status=only_status, limit=limit)
        results: list[ScoringResult] = []
        for cand in candidates:
            try:
                results.append(self.score_candidate(cand))
            except Exception:
                # Never let one bad candidate kill the run (§35); it simply
                # stays in its prior state for retry.
                continue
        return results

    # -- ranking -----------------------------------------------------------------

    def rank(
        self,
        only_statuses: tuple[CandidateStatus, ...] | None = None,
        limit: int | None = None,
    ) -> RankingResult:
        """Deterministic ranking over scored candidates.

        Order: overall_score desc, then name asc (stable, reproducible).
        Candidates with confirmed fatal flaws are excluded and counted.
        """
        if only_statuses is None:
            only_statuses = (CandidateStatus.SCORED, CandidateStatus.FINALIST)

        rows: list[RankedRow] = []
        gate_rejections = 0
        for cand in self.database.list_candidates(limit=None):
            if cand.status not in only_statuses:
                continue
            if cand.overall_score is None:
                continue
            if cand.has_confirmed_fatal_flaw:
                gate_rejections += 1
                continue
            imputed = [
                d.dimension
                for d in self.engine.score(cand).dimensions
                if d.imputed
            ]
            rows.append(
                RankedRow(
                    rank=0,  # assigned after sort
                    candidate_id=cand.id,
                    name=cand.name,
                    overall_score=cand.overall_score,
                    fatal_flaw_applied=False,
                    fatal_flaw_count=0,
                    imputed_dimensions=sorted(imputed),
                    status=cand.status.value,
                )
            )

        rows.sort(key=lambda r: (-r.overall_score, r.name))
        rows = [r.model_copy(update={"rank": i}) for i, r in enumerate(rows, start=1)]
        if limit is not None:
            rows = rows[:limit]
        return RankingResult(rows=rows, scored_count=len(rows), rejected_by_gate=gate_rejections)

    # -- finalist selection (§7) ------------------------------------------------

    def select_finalists(
        self,
        count: int = DEFAULT_FINALISTS,
        promote: bool = True,
        only_statuses: tuple[CandidateStatus, ...] | None = None,
    ) -> FinalistSelection:
        """Cut the top N finalists; optionally transition SCORED → FINALIST (§11)."""
        ranking = self.rank(only_statuses=only_statuses)
        take = ranking.rows[:count]
        selection = FinalistSelection(
            finalists=take,
            requested=count,
            available=ranking.scored_count,
            note=(
                f"top {len(take)} of {ranking.scored_count} scored candidates "
                f"(§7 funnel: -> {count} finalists)"
                if ranking.rows
                else "no scored candidates to select from"
            ),
        )
        if promote:
            for row in take:
                cand = self.database.get_candidate(row.candidate_id)
                if cand is None:
                    continue
                if cand.status is CandidateStatus.SCORED:
                    cand.transition(CandidateStatus.FINALIST)
                    self.database.save_candidate(cand)
        return selection

    # -- batch entry point -------------------------------------------------------

    def run_ranking(
        self,
        finalists: int = DEFAULT_FINALISTS,
        artifacts_dir: Path | None = None,
    ) -> RankingSummary:
        """Score RED_TEAM candidates, rank, select finalists, write artifact."""
        summary = RankingSummary()
        redteam = self.database.list_candidates(status=CandidateStatus.RED_TEAM)
        summary.attempted = len(redteam)

        gate_before = self._gate_count()
        self.score_all()
        gate_after = self._gate_count()
        summary.scored = len(
            self.database.list_candidates(status=CandidateStatus.SCORED)
        )
        summary.gate_rejections = gate_after - gate_before

        selection = self.select_finalists(count=finalists)
        summary.finalists = len(selection.finalists)

        ranking = self.rank()
        summary.per_candidate = [
            {
                "rank": r.rank,
                "candidate_id": r.candidate_id,
                "name": r.name,
                "overall_score": r.overall_score,
                "imputed": r.imputed_dimensions,
                "status": r.status,
            }
            for r in ranking.rows
        ]

        if artifacts_dir is not None:
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "summary": {
                    "attempted": summary.attempted,
                    "scored": summary.scored,
                    "gate_rejections": summary.gate_rejections,
                    "finalists": summary.finalists,
                },
                "ranking": summary.per_candidate,
                "finalists": [
                    r.model_dump(mode="json") for r in selection.finalists
                ],
            }
            (artifacts_dir / "ranking-latest.json").write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        return summary

    def _gate_count(self) -> int:
        """Confirmed-fatal candidates currently in non-terminal states."""
        n = 0
        for cand in self.database.list_candidates(limit=None):
            if cand.has_confirmed_fatal_flaw and cand.status not in (
                CandidateStatus.REJECTED,
                CandidateStatus.FAILED,
                CandidateStatus.SUPERSEDED,
            ):
                n += 1
        return n
