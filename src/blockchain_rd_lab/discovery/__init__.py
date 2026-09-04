"""Discovery schemas (Phase 1).

IdeaDraft is the raw LLM output; NormalizedIdea is the deterministic,
canonical form; both are Pydantic-validated so unstructured text can never
enter the pipeline (§2).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from blockchain_rd_lab.schemas import Candidate, new_id


class IdeaDraft(BaseModel):
    """One raw mechanism idea as produced by the Discovery Agent (§9)."""

    model_config = ConfigDict(validate_assignment=True)

    name: str = Field(min_length=3, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    domain: str = Field(default="", max_length=80)  # §24 source domain
    description: str = Field(min_length=10, max_length=2000)
    core_mechanism: str = Field(min_length=10, max_length=2000)
    problem: str = Field(default="", max_length=2000)
    innovation_claim: str = Field(default="", max_length=2000)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    oracle_required: bool = False
    blockchain_required: bool = True
    token_required: bool = False

    @field_validator("name", "category", "domain", "description", "core_mechanism")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must be non-empty")
        return v


class IdeaBatch(BaseModel):
    """A batch of ideas from one discovery call, with provenance."""

    model_config = ConfigDict(frozen=True)

    batch_id: str = Field(default_factory=lambda: f"batch-{new_id()}")
    ideas: list[IdeaDraft] = Field(min_length=1, max_length=50)
    source_agent: str = "discovery"
    domains_requested: list[str] = Field(default_factory=list)


class NormalizedIdea(BaseModel):
    """Canonical, dedup-ready form of an idea (deterministic output)."""

    model_config = ConfigDict(frozen=True)

    idea_id: str = Field(default_factory=lambda: f"idea-{new_id()}")
    name: str
    name_key: str            # normalized name for exact-dup detection
    keywords: list[str]      # ordered, deduped keyword tokens
    category: str
    domain: str
    description: str
    core_mechanism: str
    problem: str
    innovation_claim: str
    inputs: list[str]
    outputs: list[str]
    oracle_required: bool
    blockchain_required: bool
    token_required: bool
    source_batch: str = ""

    def to_candidate(self) -> Candidate:
        """Convert into a stored Candidate (status=GENERATED, §11)."""
        return Candidate(
            name=self.name,
            category=self.category,
            description=self.description,
            core_mechanism=self.core_mechanism,
            problem=self.problem,
            innovation_claim=self.innovation_claim,
            inputs=list(self.inputs),
            outputs=list(self.outputs),
            oracle_required=self.oracle_required,
            blockchain_required=self.blockchain_required,
            token_required=self.token_required,
            source_agent="discovery",
        )


class DuplicateVerdict(BaseModel):
    """Result of comparing a candidate idea against stored ideas."""

    model_config = ConfigDict(frozen=True)

    is_duplicate: bool
    similarity: float
    matched_idea_id: str | None = None
    matched_name: str | None = None
    reason: str = ""


class DiscoveryRunSummary(BaseModel):
    """Aggregate outcome of one `lab discover` run (evidence, §21 spirit)."""

    model_config = ConfigDict(validate_assignment=True)

    generated: int = 0          # raw ideas accepted from the agent
    normalized: int = 0
    duplicates_removed: int = 0
    stored: int = 0             # new candidates persisted
    failed_batches: int = 0
    errors: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
