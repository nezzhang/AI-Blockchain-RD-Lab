"""§19 dimension-assessment path (r49): fill imputed dims via the bridge.

Covers: the DimensionAssessment contract (score bounds, confidence cap,
evidence label), missing-dimension discovery, additive-only writes (an
existing dimension score is never overwritten — never a silent re-score),
composite recomputation on save (r48), and the dimension-mismatch guard.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blockchain_rd_lab.agents.base import LLMValidationError
from blockchain_rd_lab.agents.providers import MockLLMProvider
from blockchain_rd_lab.schemas import Candidate, ScoreBreakdown
from blockchain_rd_lab.scoring import load_scoring_config
from blockchain_rd_lab.scoring.assessment import (
    MAX_ASSESSMENT_CONFIDENCE,
    DimensionAssessment,
    assess_candidate,
    missing_dimensions,
    no_agent_dimensions,
)


def _candidate(scores: dict[str, float] | None = None) -> Candidate:
    cand = Candidate(
        name="Separation-Keyed Fee Smoothing Escrow",
        category="market",
        description="Fee escrow with a separation key.",
        core_mechanism="Retention keyed to a slow anchor.",
    )
    for dim, score in (scores or {}).items():
        cand.scores[dim] = ScoreBreakdown(dimension=dim, score=score)
    return cand


def _scored_candidate(scores: dict[str, float] | None = None) -> Candidate:
    """A candidate in the SCORED lifecycle (r48's recompute scope)."""
    from blockchain_rd_lab.schemas import CandidateStatus

    cand = _candidate(scores)
    for st in (
        CandidateStatus.RESEARCHING,
        CandidateStatus.PRIOR_ART_CHECKED,
        CandidateStatus.FORMALIZED,
        CandidateStatus.SIMULATING,
        CandidateStatus.RED_TEAM,
        CandidateStatus.SCORED,
    ):
        cand.transition(st)
    return cand


def _answer(dimension: str, score: float = 7.0) -> str:
    return (
        f'{{"dimension": "{dimension}", "score": {score}, "confidence": 0.7, '
        '"rationale": "mechanism-specific reasoning for the dimension", '
        '"evidence_level": "INFERENCE"}'
    )


class TestDimensionAssessmentSchema:
    def test_valid(self):
        a = DimensionAssessment(
            dimension="security", score=7.0,
            rationale="a concrete mechanism-specific rationale here",
        )
        assert a.evidence_level == "INFERENCE"
        assert a.confidence == MAX_ASSESSMENT_CONFIDENCE

    def test_score_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            DimensionAssessment(
                dimension="security", score=11.0,
                rationale="a concrete mechanism-specific rationale here",
            )

    def test_confidence_capped(self):
        with pytest.raises(ValidationError):
            DimensionAssessment(
                dimension="security", score=7.0, confidence=0.95,
                rationale="a concrete mechanism-specific rationale here",
            )

    def test_fact_label_rejected_by_convention_field_exists(self):
        # evidence_level accepts FACT syntactically (the schema allows the
        # enum); the PROMPT forbids it. The pin here: the field exists and
        # defaults to INFERENCE so an unanswered label is never FACT.
        a = DimensionAssessment(
            dimension="security", score=7.0,
            rationale="a concrete mechanism-specific rationale here",
        )
        assert a.evidence_level != "FACT"

    def test_short_rationale_rejected(self):
        with pytest.raises(ValidationError):
            DimensionAssessment(
                dimension="security", score=7.0, rationale="too short",
            )


class TestMissingDimensions:
    def test_all_missing_when_no_scores(self):
        cand = _candidate()
        assert missing_dimensions(cand) == load_scoring_config().dimension_names

    def test_only_unstored_dims_missing(self):
        cand = _candidate({"novelty": 6.0, "security": 7.0})
        missing = missing_dimensions(cand)
        assert "novelty" not in missing
        assert "security" not in missing
        assert "technical_feasibility" in missing



class TestAssessCandidate:
    def test_fills_only_no_agent_dims_and_recomputes(self, memory_db):
        # candidate has novelty (agent-covered); the 5 no-agent dims get
        # filled, the agent-covered ones stay missing (not the assessor's job).
        cand = _scored_candidate({"novelty": 6.0})
        memory_db.save_candidate(cand)
        provider = MockLLMProvider()
        for dim in no_agent_dimensions():
            provider.queue_response(_answer(dim))
        before = memory_db.get_candidate(cand.id).overall_score
        filled = assess_candidate(cand, provider, memory_db)
        assert set(filled) == set(no_agent_dimensions())
        loaded = memory_db.get_candidate(cand.id)
        # all 5 no-agent dims now carry the operator's 7.0, not the floor
        for dim in no_agent_dimensions():
            assert loaded.scores[dim].score == 7.0
            assert loaded.scores[dim].evidence_level == "INFERENCE"
        # agent-covered dims still missing (left for their own stages)
        assert "security" not in loaded.scores
        assert "market_demand" not in loaded.scores
        # r48: the composite was recomputed from the fuller dimension set.
        from blockchain_rd_lab.scoring import ScoringEngine

        assert loaded.overall_score == ScoringEngine().score(loaded).overall_score
        assert loaded.overall_score != before

    def test_never_fills_agent_covered_dimension(self, memory_db):
        # security is agent-covered AND absent: the assessor must not even
        # REQUEST it — only no-agent dims are asked.
        cand = _scored_candidate({"novelty": 6.0})
        memory_db.save_candidate(cand)
        provider = MockLLMProvider()
        for dim in no_agent_dimensions():
            provider.queue_response(_answer(dim))
        filled = assess_candidate(cand, provider, memory_db)
        loaded = memory_db.get_candidate(cand.id)
        assert "security" not in loaded.scores
        assert "security" not in filled

    def test_never_overwrites_existing_dimension(self, memory_db):
        cand = _scored_candidate({"technical_feasibility": 3.0})
        memory_db.save_candidate(cand)
        # queue answers only for the dims actually requested (missing
        # no-agent dims — technical_feasibility is stored, so not asked)
        provider = MockLLMProvider()
        for dim in no_agent_dimensions():
            if dim != "technical_feasibility":
                provider.queue_response(_answer(dim, score=9.0))
        assess_candidate(cand, provider, memory_db)
        loaded = memory_db.get_candidate(cand.id)
        # technical_feasibility already had stored evidence at 3.0 — untouched
        # (never a silent re-score), even though the provider "scored" it 9.0.
        assert loaded.scores["technical_feasibility"].score == 3.0

    def test_idempotent_second_run_fills_nothing(self, memory_db):
        cand = _scored_candidate({"novelty": 6.0})
        memory_db.save_candidate(cand)
        provider = MockLLMProvider()
        for dim in no_agent_dimensions():
            provider.queue_response(_answer(dim))
        assess_candidate(cand, provider, memory_db)
        again = assess_candidate(
            memory_db.get_candidate(cand.id), MockLLMProvider(), memory_db
        )
        assert again == []

    def test_dimension_mismatch_rejected(self, memory_db):
        cand = _scored_candidate({"novelty": 6.0})
        memory_db.save_candidate(cand)
        provider = MockLLMProvider()
        provider.queue_response(_answer("WRONG_DIMENSION"))
        with pytest.raises(ValueError, match="dimension mismatch"):
            assess_candidate(cand, provider, memory_db)

    def test_invalid_answer_never_stored(self, memory_db):
        cand = _candidate()
        memory_db.save_candidate(cand)
        provider = MockLLMProvider()
        provider.queue_response('{"dimension": "x", "score": 99.0}')
        with pytest.raises(LLMValidationError):
            assess_candidate(cand, provider, memory_db)
        assert memory_db.get_candidate(cand.id).scores == {}

    def test_fully_scored_has_none_missing(self):
        cfg = load_scoring_config()
        cand = _candidate({d: 6.0 for d in cfg.dimension_names})
        assert missing_dimensions(cand) == []
