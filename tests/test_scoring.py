"""Deterministic scoring engine tests (§19, §20)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blockchain_rd_lab.schemas import Candidate, FatalFlaw, ScoreBreakdown
from blockchain_rd_lab.scoring import ScoringConfig, ScoringEngine, load_scoring_config

ALL_DIMS = (
    "novelty",
    "economic_coherence",
    "game_theory",
    "technical_feasibility",
    "oracle_feasibility",
    "security",
    "market_demand",
    "capital_efficiency",
    "network_effects",
    "communication",
    "viral_potential",
)


class TestScoringConfig:
    def test_weights_sum_to_one(self):
        cfg = load_scoring_config()
        assert sum(d.weight for d in cfg.dimensions.values()) == pytest.approx(1.0)

    def test_all_prompt_dimensions_present(self):
        cfg = load_scoring_config()
        for dim in ALL_DIMS:
            assert dim in cfg.dimensions, f"missing dimension {dim}"

    def test_weights_match_master_prompt(self):
        cfg = load_scoring_config()
        expected = {
            "novelty": 0.10,
            "economic_coherence": 0.15,
            "game_theory": 0.10,
            "technical_feasibility": 0.10,
            "oracle_feasibility": 0.10,
            "security": 0.10,
            "market_demand": 0.15,
            "capital_efficiency": 0.05,
            "network_effects": 0.05,
            "communication": 0.05,
            "viral_potential": 0.05,
        }
        for dim, weight in expected.items():
            assert cfg.dimensions[dim].weight == pytest.approx(weight), dim

    def test_invalid_weights_rejected(self):
        with pytest.raises(ValidationError):
            ScoringConfig(
                dimensions={
                    "a": {"weight": 0.7},
                    "b": {"weight": 0.7},
                }
            )


class TestScoringEngine:
    def test_uniform_scores_weighted_average(self, fully_scored_candidate: Candidate):
        engine = ScoringEngine(load_scoring_config())
        result = engine.score(fully_scored_candidate)
        assert result.overall_score == pytest.approx(7.0, abs=1e-6)
        assert not result.fatal_flaw_applied
        assert not any(d.imputed for d in result.dimensions)

    def test_missing_dimensions_imputed_at_default(self, sample_candidate: Candidate):
        engine = ScoringEngine(load_scoring_config())
        result = engine.score(sample_candidate)
        assert all(d.imputed for d in result.dimensions)
        assert result.overall_score == pytest.approx(5.0, abs=1e-6)

    def test_deterministic(self, fully_scored_candidate: Candidate):
        engine = ScoringEngine(load_scoring_config())
        r1 = engine.score(fully_scored_candidate)
        r2 = engine.score(fully_scored_candidate)
        assert r1 == r2

    def test_fatal_flaw_caps_not_averages(self, fully_scored_candidate: Candidate):
        fully_scored_candidate.fatal_flaws.append(
            FatalFlaw(
                flaw_id="ff-1",
                category="oracle",
                description="oracle manipulation impossible to prevent",
                confirmed=True,
            )
        )
        engine = ScoringEngine(load_scoring_config())
        result = engine.score(fully_scored_candidate)
        # Raw weighted score is 7.0; the cap forces <= 5.0.
        assert result.fatal_flaw_applied
        assert result.overall_score <= 5.0
        assert "fatal_flaw_cap_applied" in result.notes
        assert "oracle manipulation impossible to prevent" in result.fatal_flaw_details

    def test_unconfirmed_flaw_does_not_cap(self, fully_scored_candidate: Candidate):
        fully_scored_candidate.fatal_flaws.append(
            FatalFlaw(flaw_id="ff-2", category="security", description="maybe", confirmed=False)
        )
        engine = ScoringEngine(load_scoring_config())
        result = engine.score(fully_scored_candidate)
        assert not result.fatal_flaw_applied
        assert result.overall_score == pytest.approx(7.0, abs=1e-6)

    def test_high_raw_score_still_capped_by_flaw(self, fully_scored_candidate: Candidate):
        for dim, breakdown in fully_scored_candidate.scores.items():
            fully_scored_candidate.scores[dim] = breakdown.model_copy(update={"score": 10.0})
        fully_scored_candidate.fatal_flaws.append(
            FatalFlaw(
                flaw_id="ff-3",
                category="economic",
                description="death spiral",
                confirmed=True,
            )
        )
        engine = ScoringEngine(load_scoring_config())
        result = engine.score(fully_scored_candidate)
        assert result.overall_score == pytest.approx(5.0)  # exactly the cap

    def test_custom_config(self, sample_candidate: Candidate):
        cfg = ScoringConfig(
            dimensions={
                "only": {"weight": 1.0},
            }
        )
        sample_candidate.scores["only"] = ScoreBreakdown(dimension="only", score=8.0)
        engine = ScoringEngine(cfg)
        result = engine.score(sample_candidate)
        assert result.overall_score == pytest.approx(8.0)

    def test_candidate_score_persisted(self, fully_scored_candidate: Candidate, memory_db):
        engine = ScoringEngine(load_scoring_config())
        result = engine.score(fully_scored_candidate)
        fully_scored_candidate.overall_score = result.overall_score
        memory_db.save_candidate(fully_scored_candidate)
        loaded = memory_db.get_candidate(fully_scored_candidate.id)
        assert loaded is not None
        assert loaded.overall_score == pytest.approx(7.0)


class TestCandidateFactoryHelper:
    def test_make(self):
        cand = Candidate(name="N", category="c", description="d", core_mechanism="m")
        assert cand.id.startswith("cand-")
