"""Research schemas (Phase 2).

Structured outputs for Prior-Art, Economist, and Market agents (§9, §12,
§29). All agent output is Pydantic-validated before storage — unstructured
LLM text never controls deterministic parts of the system (§2).
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from blockchain_rd_lab.schemas import (
    FORBIDDEN_NOVELTY_CLAIM,
    REQUIRED_NOVELTY_CLAIM,
    NoveltyClass,
    utcnow,
)


class EvidenceLevel(enum.StrEnum):
    """§29: every research statement is labeled FACT, INFERENCE, or HYPOTHESIS."""

    FACT = "FACT"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"


class ResearchSource(BaseModel):
    """A source consulted or cited during research (§29 preferred sources)."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=2, max_length=512)
    url: str = Field(default="", max_length=512)
    source_type: str = Field(
        default="web",
        pattern="^(paper|protocol_doc|repo|gov_dataset|intl_org|research_inst|web|book|other)$",
    )
    retrieved_note: str = Field(default="", max_length=500)


class SimilarMechanism(BaseModel):
    """A similar mechanism identified during prior-art search (§12)."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=200)
    url: str = Field(default="", max_length=512)
    similarity_note: str = Field(default="", max_length=1000)


class PriorArtReport(BaseModel):
    """Prior-Art Agent output (§12).

    Language discipline is enforced: the conclusion must use the required
    claim when class D, and must NEVER assert absolute novelty.
    """

    model_config = ConfigDict(validate_assignment=True)

    novelty_class: NoveltyClass = NoveltyClass.E
    similar_mechanisms: list[SimilarMechanism] = Field(default_factory=list)
    # §12: a prior-art report IS its recorded queries, findings, conclusion.
    # These are required with no defaults so that garbage LLM output
    # (e.g. a bare mock digest) cannot validate as "evidence".
    search_queries: list[str] = Field(min_length=1)
    sources: list[ResearchSource] = Field(default_factory=list)
    findings: list[str] = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    conclusion: str = Field(min_length=20, max_length=2000)
    checked_at: str = Field(default_factory=lambda: utcnow().date().isoformat())

    @field_validator("search_queries", "findings", "similar_mechanisms")
    @classmethod
    def _dedupe(cls, v: list) -> list:
        seen: set = set()
        out = []
        for item in v:
            key = item if isinstance(item, str) else item.name
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    @model_validator(mode="after")
    def _language_discipline(self) -> PriorArtReport:
        low = self.conclusion.lower()
        if FORBIDDEN_NOVELTY_CLAIM.lower() in low:
            raise ValueError(
                "Prior-art conclusion must not assert absolute novelty; "
                f"use: {REQUIRED_NOVELTY_CLAIM}"
            )
        is_class_d = self.novelty_class is NoveltyClass.D
        if is_class_d and REQUIRED_NOVELTY_CLAIM.lower() not in low:
            raise ValueError(
                f"Class D requires the conclusion to state: {REQUIRED_NOVELTY_CLAIM}"
            )
        return self

    @property
    def novelty_score(self) -> float:
        from blockchain_rd_lab.schemas import novelty_score_for

        return novelty_score_for(self.novelty_class)


class EconomicConcern(BaseModel):
    """One economic risk or property identified by the Economist Agent."""

    model_config = ConfigDict(frozen=True)

    topic: str = Field(min_length=2, max_length=80)
    note: str = Field(min_length=10, max_length=1500)
    severity: float = Field(default=5.0, ge=0.0, le=10.0)
    evidence_level: EvidenceLevel = EvidenceLevel.INFERENCE
    fatal: bool = False


class EconomistReport(BaseModel):
    """Economist Agent output (§9: monetary policy, incentives, stability...)."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=10, max_length=3000)
    concerns: list[EconomicConcern] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    economic_coherence_score: float = Field(ge=0.0, le=10.0)
    evidence_level: EvidenceLevel = EvidenceLevel.INFERENCE


class MarketReport(BaseModel):
    """Market Agent output (§9: customer, problem, alternatives, size...)."""

    model_config = ConfigDict(frozen=True)

    customer: str = Field(min_length=2, max_length=300)
    problem: str = Field(min_length=3, max_length=1000)
    existing_alternatives: list[str] = Field(default_factory=list)
    market_size_note: str = Field(default="", max_length=1000)
    adoption_barriers: list[str] = Field(default_factory=list)
    market_demand_score: float = Field(ge=0.0, le=10.0)
    evidence_level: EvidenceLevel = EvidenceLevel.INFERENCE


class CandidateBrief(BaseModel):
    """Compact candidate summary handed to research agents."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str
    name: str
    category: str
    description: str
    core_mechanism: str
    problem: str = ""
    oracle_required: bool = False

    @classmethod
    def from_candidate(cls, cand) -> CandidateBrief:
        return cls(
            candidate_id=cand.id,
            name=cand.name,
            category=cand.category,
            description=cand.description,
            core_mechanism=cand.core_mechanism,
            problem=cand.problem,
            oracle_required=cand.oracle_required,
        )


class CandidateResearchResult(BaseModel):
    """Outcome of researching one candidate through all Phase 2 agents."""

    model_config = ConfigDict(validate_assignment=True)

    candidate_id: str
    prior_art: PriorArtReport | None = None
    economist: EconomistReport | None = None
    market: MarketReport | None = None
    errors: list[str] = Field(default_factory=list)
    rejected: bool = False
    rejection_reason: str = ""


class FilterOutcome(BaseModel):
    """Result of the deterministic 100→20 prior-art filter (§7)."""

    model_config = ConfigDict(validate_assignment=True)

    considered: int = 0
    kept: int = 0
    rejected: int = 0
    rejected_class_a: int = 0
    rejected_class_b: int = 0
    kept_ids: list[str] = Field(default_factory=list)
    rejected_details: list[str] = Field(default_factory=list)
    target: int = 20
