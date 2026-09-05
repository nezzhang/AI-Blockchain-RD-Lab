"""Improvement stage schemas (§3/§34: RED_TEAM → IMPROVEMENT → RETEST).

An ImprovementProposal is what the Improvement Agent (LLM) returns after
reading the adversarial reports: a patched MathModel v(n+1) plus an
explicit account of which attacks it addresses and how (§29 evidence
discipline: hypotheses must state what changed and why).

Deterministic code (not the LLM) decides whether the proposal is
accepted: the patched model must pass the same MathModel §13 integrity
checks as any other formalization, and the proposal must reference the
attacks it claims to fix (§2).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AddressedAttack(BaseModel):
    """One adversarial finding the improvement claims to address."""

    model_config = ConfigDict(validate_assignment=True)

    agent_name: str = Field(min_length=1, max_length=64)
    vector_description: str = Field(min_length=8, max_length=600)
    fix_strategy: str = Field(min_length=8, max_length=600)
    fixes_attack: bool = True


class ImprovementProposal(BaseModel):
    """The Improvement Agent's output: patched model + fix account."""

    model_config = ConfigDict(validate_assignment=True)

    summary: str = Field(min_length=10, max_length=2000)
    addressed_attacks: list[AddressedAttack] = Field(min_length=1, max_length=20)
    model: dict = Field(description="Patched MathModel as a JSON object (v n+1)")

    @model_validator(mode="after")
    def _at_least_one_fix(self) -> ImprovementProposal:
        if not any(a.fixes_attack for a in self.addressed_attacks):
            raise ValueError(
                "an improvement proposal must address at least one attack"
            )
        return self


class ImprovementOutcome(BaseModel):
    """Result of improving one candidate (deterministic, §35)."""

    model_config = ConfigDict(validate_assignment=True)

    candidate_id: str
    improved: bool = False
    new_version: int = 0
    attacks_addressed: int = 0
    rejected_reason: str | None = None
    errors: list[str] = Field(default_factory=list)


class ImprovementRunSummary(BaseModel):
    """Aggregate over one improve-all run."""

    model_config = ConfigDict(validate_assignment=True)

    attempted: int = 0
    improved: int = 0
    rejected: int = 0
    errors: int = 0
    per_candidate: list[ImprovementOutcome] = Field(default_factory=list)
