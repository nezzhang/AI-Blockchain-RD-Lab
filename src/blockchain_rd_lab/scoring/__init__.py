"""Deterministic scoring engine (§19, §20).

Pure code — no LLM involvement. Takes the per-dimension sub-scores attached
to a Candidate by agents and computes the weighted overall score. Confirmed
fatal flaws are never averaged away: they cap the overall score and are
reported separately.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from blockchain_rd_lab.config import REPO_ROOT
from blockchain_rd_lab.schemas import Candidate

DEFAULT_SCORING_CONFIG_PATH = REPO_ROOT / "config" / "scoring.yaml"


class DimensionSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    weight: float = Field(gt=0.0, le=1.0)
    description: str = ""


class ScoringRules(BaseModel):
    model_config = ConfigDict(frozen=True)

    fatal_flaw_penalty: float = 0.35
    fatal_flaw_cap: float = 5.0
    missing_score_default: float = 5.0


class ScoringConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    dimensions: dict[str, DimensionSpec]
    rules: ScoringRules = ScoringRules()

    @field_validator("dimensions")
    @classmethod
    def _weights_must_sum_to_one(cls, v: dict[str, DimensionSpec]) -> dict[str, DimensionSpec]:
        total = sum(d.weight for d in v.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")
        return v

    @property
    def dimension_names(self) -> list[str]:
        return list(self.dimensions)


class ScoredDimension(BaseModel):
    model_config = ConfigDict(frozen=True)

    dimension: str
    weight: float
    score: float
    weighted: float
    imputed: bool = False


class ScoringResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: str
    overall_score: float = Field(ge=0.0, le=10.0)
    dimensions: list[ScoredDimension]
    fatal_flaw_applied: bool
    fatal_flaw_count: int
    fatal_flaw_details: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ScoringEngine:
    """Deterministic weighted scoring with a fatal-flaw gate (§19, §20)."""

    def __init__(self, config: ScoringConfig | None = None) -> None:
        self.config = config or load_scoring_config()

    def score(self, candidate: Candidate) -> ScoringResult:
        cfg = self.config
        notes: list[str] = []
        scored: list[ScoredDimension] = []

        for name, spec in cfg.dimensions.items():
            breakdown = candidate.scores.get(name)
            if breakdown is None:
                score = cfg.rules.missing_score_default
                imputed = True
                notes.append(f"imputed:{name}")
            else:
                score = breakdown.score
                imputed = False
            scored.append(
                ScoredDimension(
                    dimension=name,
                    weight=spec.weight,
                    score=score,
                    weighted=score * spec.weight,
                    imputed=imputed,
                )
            )

        raw = sum(d.weighted for d in scored)

        confirmed_flaws = [f for f in candidate.fatal_flaws if f.confirmed]
        flaw_applied = bool(confirmed_flaws)
        overall = raw
        if flaw_applied:
            # §20: fatal flaws cap the score — never averaged away.
            overall = min(raw, cfg.rules.fatal_flaw_cap)
            notes.append("fatal_flaw_cap_applied")

        # Clamp into [0, 10].
        overall = max(0.0, min(10.0, overall))

        return ScoringResult(
            candidate_id=candidate.id,
            overall_score=round(overall, 4),
            dimensions=scored,
            fatal_flaw_applied=flaw_applied,
            fatal_flaw_count=len(confirmed_flaws),
            fatal_flaw_details=[f.description for f in confirmed_flaws],
            notes=notes,
        )


def load_scoring_config(path: str | None = None) -> ScoringConfig:
    """Load scoring dimensions and weights from config/scoring.yaml."""
    target = Path(path) if path else DEFAULT_SCORING_CONFIG_PATH
    with open(target, encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh) or {}
    return ScoringConfig.model_validate(data)
