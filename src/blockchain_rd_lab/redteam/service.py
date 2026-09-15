"""Phase 5 orchestration: adversarial testing (§9, §17, §20).

Per candidate (SIMULATING): Game Theory → Security → Oracle → Red Team
(four LLM agents, structured output) → deterministic post-processing:

  - dimension scores: game_theory, security, oracle_feasibility
  - attack-vector inventory persisted to redteam_results
  - §20 fatal-flaw gate: a flaw is CONFIRMED only when deterministic code
    agrees — the red-team verdict is "fatal" AND (r33, external-audit
    F1) a MEASURED §20 battery edge over the canonical
    FLAW_EDGE_THRESHOLD backs the economic claim. The agent's
    `strongest_attack_is_profitable` boolean never decides anything and
    (r35, audit 2026-09-15) never even triggers the measurement: it is
    pure recorded metadata — the agent's economics hypothesis. Every
    fatal verdict is measured (the audit finding: an LLM-supplied free
    field was the gate's decisive economic predicate — first as the
    decider, then as the trigger; both residues removed). No stored
    model / no battery run / all edges under threshold → the fatal
    verdict is recorded but NOT confirmed (fail-closed for rejection:
    an unmeasured claim can never reject a candidate; every gate
    evaluation is persisted as a §21 record).
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
    ExperimentRecord,
    FatalFlaw,
    ScoreBreakdown,
)
from blockchain_rd_lab.simulation.adversarial import (
    FLAW_EDGE_THRESHOLD,
    AttackPattern,
    AttackPatternBattery,
    PatternSpec,
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

    def _measured_flaw_edge(self, candidate: Candidate) -> dict[str, Any] | None:
        """§20 gate evidence (r33, audit F1): run the deterministic
        attack battery against the candidate's LATEST stored model and
        return the measured evidence the gate decides on — worst
        headline edge, per-pattern edges, run count. None when no
        model is stored (fail-closed: the gate cannot confirm on an
        unmeasured claim; the fatal verdict is recorded, not
        confirmed).

        The battery is the SAME deterministic code the censuses and the
        published bundle run; the gate cites its canonical
        FLAW_EDGE_THRESHOLD. This method MEASURES; it never rejects.

        SCOPE (disclosed, r34): the gate measures the EIGHT default
        calibrations. Off-default robustness is the census layer's
        job (the r22 parameter sweep, published in §4b) — the gate is
        the rejection instrument, rejection is terminal, so its bar
        is the default battery, fail-closed when unmeasured. A flaw
        visible only at an off-default calibration surfaces (and
        has surfaced: the r22 sweep) in the census and §4 residual
        disclosure, not here.
        """
        model_json = self.database.get_latest_math_model(candidate.id)
        if not model_json:
            return None
        try:
            from blockchain_rd_lab.formalization import MathModel

            model = MathModel.model_validate_json(model_json)
        except Exception:
            return None
        battery = AttackPatternBattery(model)
        per_pattern: dict[str, Any] = {}
        worst: float | None = None
        worst_kind: str | None = None
        for kind in AttackPattern:
            try:
                bound = battery.run_pattern(
                    PatternSpec(kind=kind, steps=60)
                )
            except Exception:
                continue
            if bound.vacuous or bound.headline is None:
                per_pattern[kind.value] = None
                continue
            per_pattern[kind.value] = bound.headline
            if worst is None or bound.headline > worst:
                worst = bound.headline
                worst_kind = kind.value
        return {
            "worst_headline_edge": worst,
            "worst_pattern": worst_kind,
            "per_pattern": per_pattern,
            "threshold": FLAW_EDGE_THRESHOLD,
            "exceeds_threshold": bool(
                worst is not None and worst > FLAW_EDGE_THRESHOLD
            ),
        }

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

        # §20 fatal-flaw gate (deterministic code, not the prompt).
        # r33 (external-audit F1): the agent's profitable-attack
        # boolean is a HYPOTHESIS, never the decisive economic
        # predicate. A fatal verdict rejects ONLY when the
        # deterministic battery MEASURES a worst headline edge above
        # the canonical FLAW_EDGE_THRESHOLD (400) on the candidate's
        # latest stored model. Unmeasured (no model / vacuous runs /
        # every edge under threshold) → the fatal verdict is recorded,
        # the candidate stays un-rejected (fail-closed for rejection:
        # an LLM assertion can never reject; it can only point, and
        # the code then measures). Every gate evaluation is persisted
        # as a §21 record — the audit trail the audit asked for.
        # r35 (audit 2026-09-15, strongest form): the boolean no
        # longer TRIGGERS the measurement either — an agent asserting
        # profitable=false used to suppress the battery entirely,
        # shielding a model it would convict at 2266 (the
        # suppression-direction hiding vector, the last residue of
        # the trust bit one level up). Every fatal verdict is now
        # measured; the boolean is recorded as pure metadata. The
        # measurement can acquit despite the assertion AND convict
        # despite the denial — §20's confirmation instrument is the
        # battery, not the agent's economics opinion.
        rt = result.red_team
        gate_evidence: dict[str, Any] | None = None
        if (
            rt is not None
            and rt.verdict == _VERDICT_FATAL
            and candidate.status not in _TERMINAL
        ):
            gate_evidence = self._measured_flaw_edge(candidate)
            measured_confirmed = (
                gate_evidence is not None
                and gate_evidence["exceeds_threshold"]
            )
            self._persist_gate_record(
                candidate, rt, gate_evidence, measured_confirmed
            )
            if measured_confirmed and gate_evidence is not None:
                flaw = FatalFlaw(
                    flaw_id=f"ff-{candidate.id}-redteam",
                    category="game_theory",
                    description=(
                        f"Red team confirmed a profitable structural attack: "
                        f"{rt.strongest_attack} — measured worst battery "
                        f"edge {gate_evidence['worst_headline_edge']} "
                        f"(pattern {gate_evidence['worst_pattern']}) "
                        f"exceeds the {FLAW_EDGE_THRESHOLD} flaw "
                        f"threshold."
                    ),
                    confirmed=True,
                    identified_by="red_team",
                )
                candidate.fatal_flaws.append(flaw)
                result.confirmed_flaws.append(flaw.flaw_id)
                result.rejected = True
                candidate.transition(CandidateStatus.REJECTED)
        # r35: the boolean-as-trigger branch is GONE — a fatal
        # verdict with profitable=false is still measured now, so
        # there is no un-measured fatal path left to annotate (the
        # only non-evaluated case is terminal status, where the
        # state machine already prevents the transition).

    def _persist_gate_record(
        self,
        candidate: Candidate,
        rt: RedTeamReport,
        evidence: dict[str, Any] | None,
        confirmed: bool,
        note: str = "",
    ) -> None:
        """§21 record for every §20 gate evaluation (r33, audit F1):
        the verdict, the agent's profitability hypothesis, the measured
        battery evidence (or its absence), and the gate's decision —
        the audit trail that makes the gate's economics checkable
        after the fact."""
        try:
            record = ExperimentRecord(
                candidate_id=candidate.id,
                parameters={
                    "gate": "fatal_flaw_v2_measured",
                    "agent_verdict": rt.verdict,
                    "agent_strongest_attack": rt.strongest_attack,
                    "agent_profitability_hypothesis": (
                        rt.strongest_attack_is_profitable
                    ),
                    "note": note,
                },
                results={
                    "measured_evidence": evidence,
                    "confirmed": confirmed,
                    "threshold": FLAW_EDGE_THRESHOLD,
                },
                dataset="redteam-gate",
                model="battery:attack_patterns@r33",
                seed=None,
            )
            self.database.save_experiment(record)
        except Exception:
            # The gate's decision never depends on its own logging
            # (§35); a persistence failure is recorded in the run, not
            # fatal. The gate has already decided on measured evidence.
            return

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
