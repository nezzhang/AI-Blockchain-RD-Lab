"""Schema and state-machine tests (§10, §11, §12)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blockchain_rd_lab.schemas import (
    FORBIDDEN_NOVELTY_CLAIM,
    REQUIRED_NOVELTY_CLAIM,
    AgentRunRecord,
    Candidate,
    CandidateStatus,
    ExperimentRecord,
    FatalFlaw,
    InvalidTransitionError,
    NoveltyClass,
    ScoreBreakdown,
    assert_all_transitions_valid,
    can_transition,
)


class TestStatusMachine:
    def test_all_states_have_transitions(self):
        assert_all_transitions_valid()

    def test_happy_path(self, sample_candidate: Candidate):
        path = [
            CandidateStatus.RESEARCHING,
            CandidateStatus.PRIOR_ART_CHECKED,
            CandidateStatus.FORMALIZED,
            CandidateStatus.SIMULATING,
            CandidateStatus.RED_TEAM,
            CandidateStatus.IMPROVEMENT,
            CandidateStatus.RETEST,
            CandidateStatus.SIMULATING,
            CandidateStatus.RED_TEAM,
            CandidateStatus.SCORED,
            CandidateStatus.FINALIST,
        ]
        for target in path:
            sample_candidate.transition(target)
        assert sample_candidate.status == CandidateStatus.FINALIST

    def test_terminal_states_are_absorbing(self, sample_candidate: Candidate):
        terminals = (CandidateStatus.REJECTED, CandidateStatus.FAILED, CandidateStatus.SUPERSEDED)
        for terminal in terminals:
            cand = sample_candidate.model_copy(deep=True)
            assert cand.status == CandidateStatus.GENERATED
            # Only REJECTED/FAILED reachable directly from GENERATED in most cases
            if can_transition(CandidateStatus.GENERATED, terminal):
                cand.transition(terminal)
                for other in CandidateStatus:
                    if other == terminal:
                        continue
                    with pytest.raises(InvalidTransitionError):
                        cand.transition(other)

    def test_illegal_skip_rejected(self, sample_candidate: Candidate):
        with pytest.raises(InvalidTransitionError):
            sample_candidate.transition(CandidateStatus.FINALIST)

    def test_generated_to_rejected_is_allowed(self, sample_candidate: Candidate):
        sample_candidate.transition(CandidateStatus.REJECTED)
        assert sample_candidate.status == CandidateStatus.REJECTED

    def test_failed_reachable_from_simulating(self, sample_candidate: Candidate):
        sample_candidate.transition(CandidateStatus.RESEARCHING)
        sample_candidate.transition(CandidateStatus.PRIOR_ART_CHECKED)
        sample_candidate.transition(CandidateStatus.FORMALIZED)
        sample_candidate.transition(CandidateStatus.SIMULATING)
        sample_candidate.transition(CandidateStatus.FAILED)
        assert sample_candidate.status == CandidateStatus.FAILED


class TestCandidateSchema:
    def test_minimal_candidate_valid(self, sample_candidate: Candidate):
        assert sample_candidate.status == CandidateStatus.GENERATED
        assert sample_candidate.novelty_class == NoveltyClass.E
        assert sample_candidate.novelty_score == 5.0  # derived from class E

    def test_novelty_score_derived_from_class(self):
        cand = Candidate(
            name="X",
            category="payments",
            description="d",
            core_mechanism="m",
            novelty_class=NoveltyClass.D,
        )
        assert cand.novelty_score == 8.5

    def test_missing_required_fields_rejected(self):
        with pytest.raises(ValidationError):
            Candidate(name="", category="c", description="d", core_mechanism="m")

    def test_absolute_novelty_claim_forbidden(self):
        with pytest.raises(ValidationError, match="absolute novelty"):
            Candidate(
                name="X",
                category="c",
                description="d",
                core_mechanism="m",
                innovation_claim=f"Amazing! {FORBIDDEN_NOVELTY_CLAIM}",
            )

    def test_required_novelty_language_accepted(self, sample_candidate: Candidate):
        assert REQUIRED_NOVELTY_CLAIM in sample_candidate.innovation_claim

    def test_roundtrip_serialization(self, sample_candidate: Candidate):
        data = sample_candidate.model_dump(mode="json")
        clone = Candidate.model_validate(data)
        assert clone == sample_candidate

    def test_score_bounds_enforced(self):
        with pytest.raises(ValidationError):
            ScoreBreakdown(dimension="novelty", score=11.0)

    def test_fatal_flaw_flag(self, sample_candidate: Candidate):
        assert not sample_candidate.has_confirmed_fatal_flaw
        sample_candidate.fatal_flaws.append(
            FatalFlaw(
                flaw_id="ff-1",
                category="economic",
                description="unbacked redemption promises",
                confirmed=True,
            )
        )
        assert sample_candidate.has_confirmed_fatal_flaw


class TestExperimentRecord:
    def test_defaults(self, sample_candidate: Candidate):
        rec = ExperimentRecord(candidate_id=sample_candidate.id, seed=42)
        assert rec.experiment_id.startswith("exp-")
        assert rec.git_commit == "unknown"
        assert rec.results == {}


class TestAgentRunRecord:
    def test_defaults(self):
        rec = AgentRunRecord(agent_name="discovery")
        assert rec.run_id.startswith("run-")
        assert rec.status == "pending"
