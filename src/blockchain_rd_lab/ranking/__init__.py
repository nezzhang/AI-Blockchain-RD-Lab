"""Phase 6 schemas: deterministic ranking (§19, §20, §7 funnel).

No LLM involvement: ranking consumes the per-dimension scores agents
attached and the ScoringEngine's weighted result. Confirmed fatal flaws
cap scores and are reported per row — never averaged away (§20).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RankedRow(BaseModel):
    """One row of the ranking table (deterministic output)."""

    model_config = ConfigDict(frozen=True)

    rank: int
    candidate_id: str
    name: str
    overall_score: float
    fatal_flaw_applied: bool
    fatal_flaw_count: int = 0
    imputed_dimensions: list[str] = Field(default_factory=list)
    status: str = ""


class RankingResult(BaseModel):
    """Full ranked list plus funnel provenance (§7)."""

    model_config = ConfigDict(frozen=True)

    rows: list[RankedRow] = Field(default_factory=list)
    scored_count: int = 0
    rejected_by_gate: int = 0


class FinalistSelection(BaseModel):
    """Outcome of the top-N finalist cut (§7: red-team -> 5 finalists)."""

    model_config = ConfigDict(frozen=True)

    finalists: list[RankedRow] = Field(default_factory=list)
    requested: int = 5
    available: int = 0
    note: str = ""

    @property
    def cutoff_score(self) -> float | None:
        if not self.finalists:
            return None
        return self.finalists[-1].overall_score


class RankingSummary(BaseModel):
    """Run summary for CLI tables and artifacts."""

    model_config = ConfigDict(validate_assignment=True)

    attempted: int = 0
    scored: int = 0
    gate_rejections: int = 0
    finalists: int = 0
    per_candidate: list[dict[str, Any]] = Field(default_factory=list)
