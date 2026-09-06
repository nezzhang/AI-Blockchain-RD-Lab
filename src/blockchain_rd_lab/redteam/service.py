"""Phase 5 orchestration: adversarial testing (§9, §17, §20).

Per candidate (SIMULATING): Game Theory → Security → Oracle → Red Team
(four LLM agents, structured output) → deterministic post-processing:

  - dimension scores: game_theory, security, oracle_feasibility
  - attack-vector inventory persisted to redteam_results
  - §20 fatal-flaw gate: a flaw is CONFIRMED only when deterministic code
    agrees — the red-team verdict is "fatal" AND the strongest attack is
    profitable for the attacker. Both conditions are structured fields the
    schema enforces; the prompt alone can never reject a candidate (§2).
  - verdict fatal → REJECTED (§11); otherwise SIMULATING → RED_TEAM,
    ready for improvement/Phase 6.

A failing agent never kills the run (§35): errors are recorded per
candidate and the candidate stays in its prior state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from blockchain_rd_lab.agents.base import LLMError, LLMProvider
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.redteam import (
    GameTheoryReport,
    OracleReport,
    RedTeamReport,
    RedTeamResult,
    RedTeamSummary,
    SecurityReport,
)
from blockchain_rd_lab.redteam.agents import (
    GameTheoryAgent,
    OracleAgent,
    RedTeamAgent,
    SecurityAgent,
)
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import (
    Candidate,
    CandidateStatus,
    FatalFlaw,
    ScoreBreakdown,
)

# Dimension names must match config/scoring.yaml.
_DIM_GAME_THEORY = "game_theory"
_DIM_SECURITY = "security"
_DIM_ORACLE = "oracle_feasibility"

_VERDICT_FATAL = "fatal"
_TERMINAL = (
    CandidateStatus.REJECTED,
    CandidateStatus.FAILED,
    CandidateStatus.SUPERSEDED,
)


class RedTeamService:
    """Runs the Phase 5 adversarial battery over simulated candidates."""

    def __init__(
        self,
        provider: LLMProvider,
        database: LabDatabase,
        artifacts_dir: Path | None = None,
    ) -> None:
        self.provider = provider
        self.database = database
        self.artifacts_dir = artifacts_dir
        self.game_theory_agent = GameTheoryAgent(provider, database=database)
        self.security_agent = SecurityAgent(provider, database=database)
        self.oracle_agent = OracleAgent(provider, database=database)
        self.red_team_agent = RedTeamAgent(provider, database=database)

    # -- public API -----------------------------------------------------------

    def redteam_candidate(self, candidate: Candidate) -> RedTeamResult:
        """Run all four adversarial agents on one candidate; persist findings.

        §34/§9: when a formalized MathModel exists, agents attack THE MODEL
        (the latest stored version, including improvement patches) — the
        brief carries it so the adversarial prompt reflects the design as
        formalized, not just as described. Red-team after improve sees the
        patched parameters and must find attacks against THEM.
        """
        brief = CandidateBrief.from_candidate(candidate)
        model_json = self.database.get_latest_math_model(candidate.id)
        if model_json:
            brief = brief.model_copy(update={"formal_model": model_json})
        result = RedTeamResult(candidate_id=candidate.id)

        try:
            report, _ = self.game_theory_agent.execute(brief)
            assert isinstance(report, GameTheoryReport)
            result.game_theory = report
            self._persist_report(candidate.id, "game_theory", report)
        except LLMError as exc:
            result.errors.append(f"game_theory: {exc}")

        try:
            report, _ = self.security_agent.execute(brief)
            assert isinstance(report, SecurityReport)
            result.security = report
            self._persist_report(candidate.id, "security", report)
        except LLMError as exc:
            result.errors.append(f"security: {exc}")

        try:
            report, _ = self.oracle_agent.execute(brief)
            assert isinstance(report, OracleReport)
            result.oracle = report
            self._persist_report(candidate.id, "oracle", report)
        except LLMError as exc:
            result.errors.append(f"oracle: {exc}")

        try:
            report, _ = self.red_team_agent.execute(brief)
            assert isinstance(report, RedTeamReport)
            result.red_team = report
            self._persist_report(
                candidate.id, "red_team", report, verdict=report.verdict
            )
        except LLMError as exc:
            result.errors.append(f"red_team: {exc}")

        # Deterministic post-processing (code, §2) — includes the §20 gate.
        self._apply_findings(candidate, result)
        self.database.save_candidate(candidate)
        return result

    def redteam_all(
        self,
        limit: int | None = None,
        only_status: CandidateStatus | None = CandidateStatus.SIMULATING,
        artifacts_dir: Path | None = None,
    ) -> RedTeamSummary:
        """Red-team every candidate in the given state (§35 isolation)."""
        candidates = self.database.list_candidates(status=only_status, limit=limit)
        summary = RedTeamSummary(attempted=len(candidates))
        out_dir = artifacts_dir if artifacts_dir is not None else self.artifacts_dir
        for cand in candidates:
            try:
                result = self.redteam_candidate(cand)
            except Exception as exc:  # §35: never kill the run
                summary.per_candidate.append(
                    {"candidate_id": cand.id, "error": str(exc)}
                )
                summary.errors += 1
                continue
            summary.completed += 1 if result.complete else 0
            if result.errors:
                summary.errors += 1
            if result.rejected:
                summary.rejected += 1
            elif result.red_team is not None:
                if result.red_team.verdict == _VERDICT_FATAL:
                    # fatal verdict but gate didn't confirm: recorded, kept
                    summary.vulnerable += 1
                elif result.red_team.verdict == "vulnerable":
                    summary.vulnerable += 1
                else:
                    summary.survives += 1
            summary.per_candidate.append(self._summary_row(cand, result))
        if out_dir is not None:
            self._write_artifacts(out_dir, summary)
        return summary

    # -- deterministic post-processing -------------------------------------------

    def _apply_findings(self, candidate: Candidate, result: RedTeamResult) -> None:
        gt = result.game_theory
        if gt is not None:
            candidate.scores[_DIM_GAME_THEORY] = ScoreBreakdown(
                dimension=_DIM_GAME_THEORY,
                score=gt.game_theory_score,
                confidence=0.8,
                rationale=gt.summary,
                evidence_level=gt.evidence_level.value,
            )

        sec = result.security
        if sec is not None:
            candidate.scores[_DIM_SECURITY] = ScoreBreakdown(
                dimension=_DIM_SECURITY,
                score=sec.security_score,
                confidence=0.8,
                rationale=sec.summary,
                evidence_level=sec.evidence_level.value,
            )

        orc = result.oracle
        if orc is not None:
            candidate.scores[_DIM_ORACLE] = ScoreBreakdown(
                dimension=_DIM_ORACLE,
                score=orc.oracle_feasibility_score,
                confidence=0.7,
                rationale=orc.data_source_assessment,
                evidence_level=orc.evidence_level.value,
            )

        # §11: SIMULATING → RED_TEAM once adversarial review completes.
        if candidate.status is CandidateStatus.SIMULATING and result.complete:
            candidate.transition(CandidateStatus.RED_TEAM)

        # §20 fatal-flaw gate (deterministic code, not the prompt):
        # fatal verdict AND a profitable strongest attack → confirmed flaw.
        rt = result.red_team
        if (
            rt is not None
            and rt.verdict == _VERDICT_FATAL
            and rt.strongest_attack_is_profitable
            and candidate.status not in _TERMINAL
        ):
            flaw = FatalFlaw(
                flaw_id=f"ff-{candidate.id}-redteam",
                category="game_theory",
                description=(
                    f"Red team confirmed a profitable structural attack: "
                    f"{rt.strongest_attack}"
                ),
                confirmed=True,
                identified_by="red_team",
            )
            candidate.fatal_flaws.append(flaw)
            result.confirmed_flaws.append(flaw.flaw_id)
            result.rejected = True
            candidate.transition(CandidateStatus.REJECTED)

    def _persist_report(
        self,
        candidate_id: str,
        agent_name: str,
        report: Any,
        verdict: str = "",
    ) -> None:
        self.database.save_redteam_result(
            candidate_id=candidate_id,
            agent_name=agent_name,
            report_json=json.dumps(report.model_dump(mode="json")),
            verdict=verdict,
        )

    def _summary_row(self, cand: Candidate, result: RedTeamResult) -> dict[str, Any]:
        rt = result.red_team
        return {
            "candidate_id": cand.id,
            "name": cand.name,
            "verdict": rt.verdict if rt is not None else None,
            "rejected": result.rejected,
            "errors": result.errors,
            "confirmed_flaws": result.confirmed_flaws,
        }

    def _write_artifacts(self, out_dir: Path, summary: RedTeamSummary) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "redteam-latest.json").write_text(
            summary.model_dump_json(indent=2), encoding="utf-8"
        )
