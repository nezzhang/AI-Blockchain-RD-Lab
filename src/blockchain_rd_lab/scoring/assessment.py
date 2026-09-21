"""§19 dimension-evidence completion: assess the dimensions no agent covers.

The §19 scorer weights 11 dimensions, but the lab's agents only ever wrote
6 of them (research: novelty, economic_coherence, market_demand; red team:
game_theory, security, oracle_feasibility). The other 5 —
technical_feasibility, capital_efficiency, network_effects, communication,
viral_potential (the §9 Blockchain Architect / Quant / Market scoring roles,
never implemented as scoring agents) — were always imputed at the 5.0 floor
(AUDITING.md known weakness #1).

This module closes that gap through the §30 bridge provider: the operator
(a reasoning agent or careful human) IS the assessor. For each missing
dimension the lab emits a structured bridge request carrying the candidate's
evidence and the dimension's rubric; the operator's answer is validated
against DimensionAssessment (§2: LLM proposes, code tests), recorded as a
§22 agent run, and stored as a ScoreBreakdown. save_candidate (r48) then
recomputes the composite from the fuller dimension set in the same
transaction.

Hard rules:
- ADDITIVE ONLY. An existing stored ScoreBreakdown is evidence with
  provenance; this path never overwrites one (never a silent re-score).
- Operator judgments are evidence_level INFERENCE, confidence <= 0.8 — never
  presented as FACT, never stronger than the lab's measured evidence.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from blockchain_rd_lab.agents.base import (
    BaseAgent,
    LLMMessage,
    LLMProvider,
    ModelTier,
)
from blockchain_rd_lab.schemas import Candidate, ScoreBreakdown
from blockchain_rd_lab.scoring import ScoringConfig, load_scoring_config

#: Operator assessments are calibrated judgments, not measurements. The cap
#: keeps a bridge-authored score from ever reading as strong as the lab's
#: measured evidence (the measured dims carry confidence <= 0.8 too).
MAX_ASSESSMENT_CONFIDENCE = 0.8

#: Dimensions a dedicated agent already produces (research: novelty,
#: economic_coherence, market_demand; red team: game_theory, security,
#: oracle_feasibility). This path NEVER fills those: a missing agent-covered
#: dimension means the candidate's evidence trail is incomplete (re-run that
#: stage), and a generic assessor must not impersonate a dedicated agent's
#: analysis (that would be its own honesty failure — a "security" score with
#: no adversarial work behind it). The assessor exists ONLY for the §19
#: dimensions that have no producing agent at all (the 5/11 floor).
COVERED_BY_AGENTS: frozenset[str] = frozenset(
    {
        "novelty",
        "economic_coherence",
        "market_demand",
        "game_theory",
        "security",
        "oracle_feasibility",
    }
)


def no_agent_dimensions(config: ScoringConfig | None = None) -> list[str]:
    """§19 dimensions with NO producing agent (the assessor's whole scope)."""
    cfg = config or load_scoring_config()
    return [d for d in cfg.dimension_names if d not in COVERED_BY_AGENTS]


class DimensionAssessment(BaseModel):
    """One operator-authored judgment for one §19 dimension (bridge schema).

    Structured output contract for the bridge: the operator proposes; this
    schema is the code that tests (§2).
    """

    dimension: str
    score: float = Field(ge=0.0, le=10.0)
    confidence: float = Field(
        default=MAX_ASSESSMENT_CONFIDENCE,
        le=MAX_ASSESSMENT_CONFIDENCE,
        ge=0.0,
    )
    rationale: str = Field(min_length=20)
    evidence_level: str = Field(
        default="INFERENCE", pattern="^(FACT|INFERENCE|HYPOTHESIS)$"
    )


class _AssessmentRequest(BaseModel):
    """Prompt payload for one dimension assessment (internal)."""

    candidate_id: str
    name: str
    category: str
    description: str
    core_mechanism: str
    problem: str
    dimension: str
    existing_scores: dict[str, float] = Field(default_factory=dict)
    dossier_excerpt: str = ""



class DimensionAssessmentAgent(BaseAgent):
    """Scores ONE §19 dimension for ONE candidate from its stored evidence.

    With the bridge provider the operator is the model (§30): the prompt
    carries the candidate's description, core mechanism, and every stored
    dimension score so far, plus the dimension's §19 rubric — the answer is
    a DimensionAssessment.
    """

    name = "dimension_assessor"
    role = "Assess one §19 score dimension from the candidate's stored evidence"
    output_schema = DimensionAssessment
    model_tier = ModelTier.STRONG
    temperature = 0.2

    def __init__(
        self,
        provider: LLMProvider,
        database: Any | None = None,
        config: ScoringConfig | None = None,
    ) -> None:
        super().__init__(provider, database)
        self.config = config or load_scoring_config()

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        assert isinstance(payload, _AssessmentRequest)
        dim = payload.dimension
        spec = self.config.dimensions[dim]
        system = (
            "You are the dimension-assessment reviewer of an independent "
            "blockchain economic-mechanism research laboratory (§9/§19).\n\n"
            f"DIMENSION UNDER ASSESSMENT: {dim} (weight {spec.weight}).\n"
            f"Rubric: {spec.description}\n\n"
            "RULES:\n"
            "- Score 0-10 for THIS dimension only, from the evidence given.\n"
            "- This is a calibrated judgment, not a measurement: label it\n"
            "  INFERENCE (or HYPOTHESIS if the evidence is thin). Never FACT.\n"
            "- Give a concrete, mechanism-specific rationale grounded in the\n"
            "  candidate's own design — no generic praise. Reference the\n"
            "  actual mechanism.\n"
            "- Be willing to score BELOW the 5.0 midpoint: an unimpressive\n"
            "  or risky dimension should score low. Do not anchor on 5.\n"
            "- Confidence <= 0.8: you are reasoning over a research dossier,\n"
            "  not running the mechanism.\n\n"
            "OUTPUT: only a JSON object matching the DimensionAssessment schema."
        )
        user = (
            f"CANDIDATE: {payload.name}\n"
            f"category: {payload.category}\n"
            f"description: {payload.description}\n"
            f"core mechanism: {payload.core_mechanism}\n"
            f"problem: {payload.problem}\n"
        )
        if payload.existing_scores:
            lines = "; ".join(
                f"{k}={v}" for k, v in sorted(payload.existing_scores.items())
            )
            user += f"\nstored dimension evidence so far: {lines}\n"
        if payload.dossier_excerpt:
            user += f"\nresearch dossier (excerpt):\n{payload.dossier_excerpt}\n"
        return [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]


def missing_dimensions(
    candidate: Candidate, config: ScoringConfig | None = None
) -> list[str]:
    """§19 dimensions with no stored ScoreBreakdown (the imputation set).

    These are exactly the dimensions the scorer would impute at the 5.0
    floor for this candidate.
    """
    cfg = config or load_scoring_config()
    return [d for d in cfg.dimension_names if d not in candidate.scores]


def assess_candidate(
    candidate: Candidate,
    provider: LLMProvider,
    database: Any,
    *,
    config: ScoringConfig | None = None,
    dossier_excerpt: str = "",
) -> list[str]:
    """Fill every missing NO-AGENT §19 dimension for one candidate.

    Only the dimensions no dedicated agent produces (COVERED_BY_AGENTS'
    complement) are assessable here — a missing agent-covered dimension
    signals an incomplete evidence trail to rebuild by re-running that stage,
    never a gap for a generic assessor to paper over.

    Returns the dimensions assessed (empty when the candidate already has
    every no-agent dimension). ADDITIVE ONLY: a dimension with a stored
    ScoreBreakdown is skipped, so re-running is idempotent and no stored
    evidence is ever overwritten (never a silent re-score). The candidate is
    saved once at the end; save_candidate (r48) recomputes the composite from
    the fuller dimension set in the same transaction.

    With the bridge provider, the first un-answered dimension raises the
    bridge's fail-closed PENDING error — the run halts, resumable by
    re-running once the operator has answered (§30/§35).
    """
    cfg = config or load_scoring_config()
    agent = DimensionAssessmentAgent(provider, database=database, config=cfg)
    assessable = set(no_agent_dimensions(cfg))
    targets = [d for d in missing_dimensions(candidate, cfg) if d in assessable]
    assessed: list[str] = []
    for dim in targets:
        payload = _AssessmentRequest(
            candidate_id=candidate.id,
            name=candidate.name,
            category=candidate.category,
            description=candidate.description,
            core_mechanism=candidate.core_mechanism,
            problem=candidate.problem,
            dimension=dim,
            existing_scores={k: v.score for k, v in candidate.scores.items()},
            dossier_excerpt=dossier_excerpt,
        )
        output, _record = agent.execute(payload)
        assert isinstance(output, DimensionAssessment)
        # Defense in depth: the agent is told which dimension it is scoring;
        # never let a mislabeled answer write the wrong row (§2).
        if output.dimension != dim:
            raise ValueError(
                f"assessment dimension mismatch: asked {dim!r}, "
                f"got {output.dimension!r}"
            )
        candidate.scores[dim] = ScoreBreakdown(
            dimension=dim,
            score=output.score,
            confidence=min(output.confidence, MAX_ASSESSMENT_CONFIDENCE),
            rationale=output.rationale,
            evidence_level=output.evidence_level,
        )
        assessed.append(dim)
    if assessed:
        candidate.source_agent = "dimension_assessor"
        database.save_candidate(candidate)
    return assessed

