"""Phase 5 schemas: adversarial testing reports (§9, §17, §20).

All agent output must pass Pydantic validation before storage (§2).
Evidence levels follow §29 (FACT / INFERENCE / HYPOTHESIS). Fatal flaws
are confirmed only when *deterministic code* agrees — an LLM alone can
propose a flaw, but confirmation requires either simulation evidence or
an unambiguous structural argument; the Red Team verdict gate lives in
the service, not the prompt (§2, §20).
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------------------


class EvidenceLevel(enum.StrEnum):
    """§29 evidence discipline."""

    FACT = "FACT"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"


class AttackVector(BaseModel):
    """One adversarial play against the mechanism (§9 red-team questions)."""

    model_config = ConfigDict(frozen=True)

    vector: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=10, max_length=2000)
    attacker: str = Field(
        default="unspecified",
        pattern="^(whale|validator|oracle_provider|governance|arbitrageur|"
        "liquidity_provider|attacker|governance_participant|unspecified)$",
    )
    profitable_for_attacker: bool = False
    requires_collusion: bool = False
    evidence_level: EvidenceLevel = EvidenceLevel.HYPOTHESIS


class AdversarialConcern(BaseModel):
    """A structural concern (non-vector) raised by an adversarial agent."""

    model_config = ConfigDict(frozen=True)

    topic: str = Field(min_length=3, max_length=120)
    note: str = Field(min_length=10, max_length=2000)
    severity: float = Field(ge=0.0, le=10.0)
    evidence_level: EvidenceLevel = EvidenceLevel.INFERENCE
    fatal: bool = False


# ---------------------------------------------------------------------------
# Agent reports
# ---------------------------------------------------------------------------


class GameTheoryReport(BaseModel):
    """Game Theory Agent output (§9: rational profit maximizers)."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=20, max_length=4000)
    attack_vectors: list[AttackVector] = Field(min_length=1)
    equilibria_notes: str = Field(min_length=20, max_length=4000)
    death_spiral_risk: float = Field(ge=0.0, le=10.0)
    game_theory_score: float = Field(ge=0.0, le=10.0)
    evidence_level: EvidenceLevel = EvidenceLevel.HYPOTHESIS


class SecurityReport(BaseModel):
    """Security Agent output (§9: contract/economic/oracle/governance/
    validator attacks)."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=20, max_length=4000)
    attack_vectors: list[AttackVector] = Field(min_length=1)
    hardest_attack_to_defend: str = Field(min_length=10, max_length=1000)
    security_score: float = Field(ge=0.0, le=10.0)
    evidence_level: EvidenceLevel = EvidenceLevel.HYPOTHESIS


class OracleReport(BaseModel):
    """Oracle Agent output (§9: data sources, accuracy, latency, revisions,
    manipulation, decentralization, oracle incentives, conflicting data)."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=20, max_length=4000)
    data_source_assessment: str = Field(min_length=20, max_length=4000)
    manipulation_vectors: list[AttackVector] = Field(min_length=1)
    oracle_feasibility_score: float = Field(ge=0.0, le=10.0)
    evidence_level: EvidenceLevel = EvidenceLevel.HYPOTHESIS


class RedTeamReport(BaseModel):
    """Red Team Agent output — DESTROY THE IDEA (§9)."""

    model_config = ConfigDict(frozen=True)

    verdict: str = Field(pattern="^(survives|vulnerable|fatal)$")
    strongest_attack: str = Field(min_length=10, max_length=2000)
    strongest_attack_is_profitable: bool = False
    attack_vectors: list[AttackVector] = Field(min_length=1)
    what_would_save_it: str = Field(min_length=10, max_length=2000)
    evidence_level: EvidenceLevel = EvidenceLevel.HYPOTHESIS

    @field_validator("strongest_attack")
    @classmethod
    def _no_throwaway(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("strongest_attack must be substantive")
        return v.strip()


# ---------------------------------------------------------------------------
# Run-level rollups (deterministic code, not LLM)
# ---------------------------------------------------------------------------


class RedTeamResult(BaseModel):
    """Aggregated adversarial result for one candidate (built by code)."""

    model_config = ConfigDict(validate_assignment=True)

    candidate_id: str
    game_theory: GameTheoryReport | None = None
    security: SecurityReport | None = None
    oracle: OracleReport | None = None
    red_team: RedTeamReport | None = None
    errors: list[str] = Field(default_factory=list)
    confirmed_flaws: list[str] = Field(default_factory=list)
    rejected: bool = False

    @property
    def complete(self) -> bool:
        return all(
            x is not None
            for x in (self.game_theory, self.security, self.oracle, self.red_team)
        )


class RedTeamSummary(BaseModel):
    """Run summary for the CLI table and artifacts."""

    model_config = ConfigDict(validate_assignment=True)

    attempted: int = 0
    completed: int = 0
    rejected: int = 0
    vulnerable: int = 0
    survives: int = 0
    errors: int = 0
    per_candidate: list[dict[str, Any]] = Field(default_factory=list)
