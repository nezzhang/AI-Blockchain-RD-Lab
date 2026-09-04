"""Core Pydantic schemas: candidates, status machine, scores, experiments.

This module is the deterministic backbone of the lab (MASTER BUILD PROMPT §2):
LLM agents produce *validated* structured data, never free-form text that
controls deterministic parts of the system.
"""

from __future__ import annotations

import enum
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# IDs and timestamps
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def new_id() -> str:
    """Generate a short unique id (prefixed at the call site)."""
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Status machine (§11)
# ---------------------------------------------------------------------------


class CandidateStatus(enum.StrEnum):
    """Controlled lifecycle states for candidates (§11).

    Terminal states: REJECTED, FAILED, SUPERSEDED.
    """

    GENERATED = "generated"
    RESEARCHING = "researching"
    PRIOR_ART_CHECKED = "prior_art_checked"
    FORMALIZED = "formalized"
    SIMULATING = "simulating"
    RED_TEAM = "red_team"
    IMPROVEMENT = "improvement"
    RETEST = "retest"
    SCORED = "scored"
    FINALIST = "finalist"

    # Terminal states
    REJECTED = "rejected"
    FAILED = "failed"
    SUPERSEDED = "superseded"


# Directed edges: allowed forward transitions plus terminal exits (§11).
# A candidate may also stay in its current state (idempotent re-run).
_ALLOWED_TRANSITIONS: dict[CandidateStatus, frozenset[CandidateStatus]] = {
    CandidateStatus.GENERATED: frozenset(
        {CandidateStatus.GENERATED, CandidateStatus.RESEARCHING, CandidateStatus.REJECTED}
    ),
    CandidateStatus.RESEARCHING: frozenset(
        {CandidateStatus.RESEARCHING, CandidateStatus.PRIOR_ART_CHECKED, CandidateStatus.REJECTED}
    ),
    CandidateStatus.PRIOR_ART_CHECKED: frozenset(
        {
            CandidateStatus.PRIOR_ART_CHECKED,
            CandidateStatus.RESEARCHING,  # re-research on new prior-art evidence
            CandidateStatus.REJECTED,
            CandidateStatus.FORMALIZED,
        }
    ),
    CandidateStatus.FORMALIZED: frozenset(
        {CandidateStatus.FORMALIZED, CandidateStatus.SIMULATING, CandidateStatus.REJECTED}
    ),
    CandidateStatus.SIMULATING: frozenset(
        {CandidateStatus.SIMULATING, CandidateStatus.FAILED, CandidateStatus.RED_TEAM}
    ),
    CandidateStatus.RED_TEAM: frozenset(
        {
            CandidateStatus.RED_TEAM,
            CandidateStatus.REJECTED,
            CandidateStatus.IMPROVEMENT,
            CandidateStatus.SCORED,
        }
    ),
    CandidateStatus.IMPROVEMENT: frozenset(
        {CandidateStatus.IMPROVEMENT, CandidateStatus.RETEST, CandidateStatus.REJECTED}
    ),
    CandidateStatus.RETEST: frozenset(
        {
            CandidateStatus.RETEST,
            CandidateStatus.SIMULATING,
            CandidateStatus.FAILED,
            CandidateStatus.REJECTED,
        }
    ),
    CandidateStatus.SCORED: frozenset(
        {CandidateStatus.SCORED, CandidateStatus.FINALIST, CandidateStatus.SUPERSEDED}
    ),
    CandidateStatus.FINALIST: frozenset({CandidateStatus.FINALIST, CandidateStatus.SUPERSEDED}),
    CandidateStatus.REJECTED: frozenset({CandidateStatus.REJECTED}),
    CandidateStatus.FAILED: frozenset({CandidateStatus.FAILED}),
    CandidateStatus.SUPERSEDED: frozenset({CandidateStatus.SUPERSEDED}),
}


class InvalidTransitionError(ValueError):
    """Raised on an illegal status transition (§11: never allow arbitrary transitions)."""


def can_transition(source: CandidateStatus, target: CandidateStatus) -> bool:
    """True if source → target is an allowed state-machine edge."""
    return target in _ALLOWED_TRANSITIONS[source]


def assert_transition(source: CandidateStatus, target: CandidateStatus) -> None:
    if not can_transition(source, target):
        raise InvalidTransitionError(
            f"Illegal transition {source.value!r} -> {target.value!r}; "
            f"allowed: {sorted(s.value for s in _ALLOWED_TRANSITIONS[source])}"
        )


def assert_all_transitions_valid() -> None:
    """Sanity check used by tests: every state has a defined transition set."""
    for status in CandidateStatus:
        if status not in _ALLOWED_TRANSITIONS:
            raise RuntimeError(f"Missing transition table entry for {status.value}")


# ---------------------------------------------------------------------------
# Novelty classification (§12)
# ---------------------------------------------------------------------------


class NoveltyClass(enum.StrEnum):
    A = "clearly_existing"
    B = "very_similar_existing"
    C = "adjacent_mechanism"
    D = "appears_substantially_novel"
    E = "insufficient_evidence"


NOVELTY_LANGUAGE = {
    NoveltyClass.A: "clearly existing",
    NoveltyClass.B: "a very similar existing mechanism",
    NoveltyClass.C: "an adjacent mechanism",
    NoveltyClass.D: "substantially novel relative to the searched sources",
    NoveltyClass.E: "of undetermined novelty (insufficient evidence)",
}

FORBIDDEN_NOVELTY_CLAIM = "Nobody has ever done this."
REQUIRED_NOVELTY_CLAIM = (
    "No substantially similar implementation was identified in the searched sources."
)


# ---------------------------------------------------------------------------
# Candidate schema (§10)
# ---------------------------------------------------------------------------

SCORE_MIN = 0.0
SCORE_MAX = 10.0

DimensionName = str  # semantic alias; validated by ScoringConfig at use-site


class ScoreBreakdown(BaseModel):
    """Per-dimension sub-scores on a 0-10 scale, plus provenance."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    score: float = Field(ge=SCORE_MIN, le=SCORE_MAX)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""
    evidence_level: str = Field(default="INFERENCE", pattern="^(FACT|INFERENCE|HYPOTHESIS)$")


class FatalFlaw(BaseModel):
    model_config = ConfigDict(frozen=True)

    flaw_id: str
    category: str = Field(
        pattern="^(economic|game_theory|security|oracle|governance|liquidity|market|data|other)$"
    )
    description: str
    confirmed: bool = False
    identified_by: str = "red_team"  # agent id
    identified_at: datetime = Field(default_factory=utcnow)
    mitigations_attempted: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    """A proposed blockchain economic mechanism (§10)."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: f"cand-{new_id()}")
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=4000)
    core_mechanism: str = Field(min_length=1, max_length=4000)
    problem: str = Field(default="", max_length=4000)
    innovation_claim: str = Field(default="", max_length=4000)

    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)

    oracle_required: bool = False
    blockchain_required: bool = True
    token_required: bool = False

    status: CandidateStatus = CandidateStatus.GENERATED
    novelty_class: NoveltyClass = NoveltyClass.E
    novelty_score: float | None = Field(default=None, ge=SCORE_MIN, le=SCORE_MAX)

    # Dimension scores (populated by agents; consumed by the scoring engine)
    scores: dict[str, ScoreBreakdown] = Field(default_factory=dict)

    fatal_flaws: list[FatalFlaw] = Field(default_factory=list)

    # overall_score is set ONLY by the deterministic scoring engine.
    overall_score: float | None = Field(default=None, ge=0.0, le=10.0)

    source_agent: str = "discovery"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("name", "category", "description", "core_mechanism")
    @classmethod
    def _strip_required_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text fields must be non-empty")
        return v

    @model_validator(mode="after")
    def _validate_semantics(self) -> Candidate:
        # Innovation claims must use the required novelty language (§12).
        claim = self.innovation_claim.lower()
        if self.innovation_claim and FORBIDDEN_NOVELTY_CLAIM.lower() in claim:
            raise ValueError(
                "Innovation claim must not assert absolute novelty; "
                f"use: {REQUIRED_NOVELTY_CLAIM}"
            )
        # Derive novelty_score from novelty_class unless explicitly provided.
        if self.novelty_score is None:
            self.novelty_score = _novelty_score_for(self.novelty_class)
        return self

    @property
    def has_confirmed_fatal_flaw(self) -> bool:
        return any(f.confirmed for f in self.fatal_flaws)

    def transition(self, target: CandidateStatus) -> CandidateStatus:
        """Apply a validated status transition; bumps updated_at."""
        assert_transition(self.status, target)
        self.status = target
        self.updated_at = utcnow()
        return target


def novelty_score_for(cls_: NoveltyClass) -> float:
    """Deterministic novelty sub-score per §12 class (code is authoritative)."""
    return {
        NoveltyClass.A: 2.0,
        NoveltyClass.B: 4.0,
        NoveltyClass.C: 6.0,
        NoveltyClass.D: 8.5,
        NoveltyClass.E: 5.0,
    }[cls_]


# Backwards-compatible private alias.
_novelty_score_for = novelty_score_for


# ---------------------------------------------------------------------------
# Experiments / reproducibility (§21)
# ---------------------------------------------------------------------------


class ExperimentRecord(BaseModel):
    """Every experiment must be reproducible (§21)."""

    model_config = ConfigDict(frozen=True)

    experiment_id: str = Field(default_factory=lambda: f"exp-{new_id()}")
    candidate_id: str
    timestamp: datetime = Field(default_factory=utcnow)
    git_commit: str = "unknown"
    parameters: dict[str, Any] = Field(default_factory=dict)
    dataset: str = "none"
    model: str = "none"
    seed: int | None = None
    simulation_version: str = "none"
    results: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent run records (§22)
# ---------------------------------------------------------------------------


class AgentRunRecord(BaseModel):
    """Provenance record for one agent invocation."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(default_factory=lambda: f"run-{new_id()}")
    agent_name: str
    candidate_id: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    provider: str = "mock"
    model: str = "mock-model"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    status: str = "pending"  # pending | success | validation_error | error
    error: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)
