"""§15/§21 evidence-quality audit: re-run every stored model today.

The corpus carries models authored across the lab's history — some
under older interpreter semantics (declaration-order evaluation
tolerated dependency cycles), some against a different implicit input
contract than the §15 battery enforces. Their STORED experiment
verdicts ("13/13 clean") may therefore describe runs today's code
would reject or flag as vacuous.

This audit re-executes every stored model version through the CURRENT
interpreter + §15 battery and reports, per candidate:

  interpret   OK | cycle | error        (can today's code even run it?)
  battery     n/13 clean, k degenerate (does it exercise dynamics?)
  verdict     healthy | vacuous | uninterpretable

It changes nothing — it measures (§2: deterministic code decides; the
human/agent decides what to do about it). The §11 corrections
(SUPERSEDED transitions with recorded reasons) are made by the
operator with this census in hand, never silently here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.schemas import CandidateStatus
from blockchain_rd_lab.simulation import MechanismSimulation, ScenarioBattery
from blockchain_rd_lab.simulation.interpreter import SimulationError


class AuditVerdict(StrEnum):
    HEALTHY = "healthy"
    VACUOUS = "vacuous"  # runs, but trajectories are degenerate
    UNINTERPRETABLE = "uninterpretable"  # today's code cannot run it
    NO_MODEL = "no_model"


@dataclass
class _Row:
    candidate_id: str
    name: str
    status: str
    version: int
    interpret: str = "ok"
    degenerate: int = 0
    clean: int = 0
    scenarios: int = 0
    error: str = ""
    verdict: AuditVerdict = AuditVerdict.HEALTHY
    failures: list[str] = field(default_factory=list)


class AuditReport(BaseModel):
    """The census result (one row per stored model)."""

    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    rows: list[dict[str, object]] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class AuditService:
    """Re-runs stored models through today's §14/§15 code."""

    def __init__(self, database: LabDatabase, steps: int = 120, seed: int = 7) -> None:
        self.database = database
        self.steps = steps
        self.seed = seed

    def audit_candidate(self, candidate_id: str) -> _Row | None:
        cand = self.database.get_candidate(candidate_id)
        if cand is None:
            return None
        mj = self.database.get_latest_math_model(candidate_id)
        if mj is None:
            row = _Row(
                candidate_id, cand.name, cand.status.value, version=0,
                verdict=AuditVerdict.NO_MODEL,
            )
            return row
        import json as _json

        row = _Row(
            candidate_id, cand.name, cand.status.value,
            version=int(_json.loads(mj).get("version", 1)),
        )
        try:
            model = MathModel.model_validate(_json.loads(mj))
            runs = ScenarioBattery(
                MechanismSimulation(model), steps=self.steps, seed=self.seed
            ).run()
        except SimulationError as exc:
            row.interpret = "cycle" if "dependency cycle" in str(exc) else "error"
            row.error = str(exc)[:160]
            row.verdict = AuditVerdict.UNINTERPRETABLE
            return row
        except Exception as exc:  # malformed model record
            row.interpret = "error"
            row.error = f"{type(exc).__name__}: {str(exc)[:140]}"
            row.verdict = AuditVerdict.UNINTERPRETABLE
            return row
        row.scenarios = len(runs)
        row.degenerate = sum(1 for r in runs.values() if r.degenerate)
        row.clean = sum(1 for r in runs.values() if not r.failures)
        if row.degenerate == row.scenarios and row.scenarios:
            row.verdict = AuditVerdict.VACUOUS
        else:
            row.verdict = AuditVerdict.HEALTHY
        return row

    def audit_all(self, statuses: tuple[CandidateStatus, ...] | None = None) -> AuditReport:
        """Census every candidate that carries ranking weight (or all)."""
        statuses = statuses or (
            CandidateStatus.FINALIST,
            CandidateStatus.SCORED,
        )
        report = AuditReport()
        for cand in self.database.list_candidates(limit=None):
            if cand.status not in statuses:
                continue
            row = self.audit_candidate(cand.id)
            if row is None:
                continue
            report.rows.append(
                {
                    "candidate_id": row.candidate_id,
                    "name": row.name,
                    "status": row.status,
                    "model_version": row.version,
                    "interpret": row.interpret,
                    "scenarios": row.scenarios,
                    "clean": row.clean,
                    "degenerate": row.degenerate,
                    "error": row.error,
                    "verdict": row.verdict.value,
                }
            )
            report.counts[row.verdict.value] = (
                report.counts.get(row.verdict.value, 0) + 1
            )
        return report
