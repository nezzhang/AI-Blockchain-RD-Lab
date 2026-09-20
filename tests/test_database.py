"""Database layer tests (§21, §22)."""

from __future__ import annotations

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import (
    AgentRunRecord,
    Candidate,
    CandidateStatus,
    ExperimentRecord,
    FatalFlaw,
    ScoreBreakdown,
)


class TestCandidatePersistence:
    def test_save_and_load_roundtrip(self, memory_db, sample_candidate):
        memory_db.save_candidate(sample_candidate)
        loaded = memory_db.get_candidate(sample_candidate.id)
        assert loaded is not None
        assert loaded.name == sample_candidate.name
        assert loaded.core_mechanism == sample_candidate.core_mechanism
        assert loaded.inputs == sample_candidate.inputs
        assert loaded.oracle_required is True
        assert loaded.status == CandidateStatus.GENERATED

    def test_get_missing_returns_none(self, memory_db):
        assert memory_db.get_candidate("cand-nope") is None

    def test_update_upsert(self, memory_db, sample_candidate):
        memory_db.save_candidate(sample_candidate)
        sample_candidate.transition(CandidateStatus.RESEARCHING)
        memory_db.save_candidate(sample_candidate)
        loaded = memory_db.get_candidate(sample_candidate.id)
        assert loaded is not None
        assert loaded.status == CandidateStatus.RESEARCHING

    def test_list_and_count_by_status(self, memory_db, sample_candidate):
        memory_db.save_candidate(sample_candidate)
        other = Candidate(
            name="Other",
            category="energy",
            description="d",
            core_mechanism="m",
        )
        other.transition(CandidateStatus.REJECTED)
        memory_db.save_candidate(other)

        assert memory_db.count_candidates() == 2
        assert memory_db.count_candidates(CandidateStatus.GENERATED) == 1
        assert memory_db.count_candidates(CandidateStatus.REJECTED) == 1
        listed = memory_db.list_candidates(status=CandidateStatus.REJECTED)
        assert [c.id for c in listed] == [other.id]

    def test_scores_persisted(self, memory_db, sample_candidate):
        sample_candidate.scores["novelty"] = ScoreBreakdown(
            dimension="novelty", score=6.5, rationale="adjacent mechanisms exist"
        )
        memory_db.save_candidate(sample_candidate)
        loaded = memory_db.get_candidate(sample_candidate.id)
        assert loaded is not None
        assert loaded.scores["novelty"].score == 6.5
        assert loaded.scores["novelty"].rationale == "adjacent mechanisms exist"

    def test_fatal_flaws_persisted(self, memory_db, sample_candidate):
        sample_candidate.fatal_flaws.append(
            FatalFlaw(flaw_id="ff-1", category="liquidity", description="bank run", confirmed=True)
        )
        memory_db.save_candidate(sample_candidate)
        loaded = memory_db.get_candidate(sample_candidate.id)
        assert loaded is not None
        assert loaded.has_confirmed_fatal_flaw
        assert loaded.fatal_flaws[0].description == "bank run"

    def test_delete(self, memory_db, sample_candidate):
        memory_db.save_candidate(sample_candidate)
        assert memory_db.delete_candidate(sample_candidate.id) is True
        assert memory_db.delete_candidate(sample_candidate.id) is False
        assert memory_db.get_candidate(sample_candidate.id) is None


class TestOverallScoreIntegrity:
    """r48 (audit 2026-09-20, F3): overall_score is a denormalized cache of
    the §19 composite over `scores`. For candidates in the SCORED lifecycle
    (SCORED / FINALIST — the only statuses that carry dimension evidence),
    save_candidate must DERIVE it from the dimension rows being persisted,
    in the same transaction — it can never diverge from them. The published
    rank-1 bundle carried 6.45 while its stored scores recomputed to 5.95
    (oracle/security rows dropped without a re-score), reordering the
    ranking. These pins make that impossible."""

    @staticmethod
    def _scored(sample_candidate: Candidate) -> Candidate:
        for st in (
            CandidateStatus.RESEARCHING,
            CandidateStatus.PRIOR_ART_CHECKED,
            CandidateStatus.FORMALIZED,
            CandidateStatus.SIMULATING,
            CandidateStatus.RED_TEAM,
            CandidateStatus.SCORED,
        ):
            sample_candidate.transition(st)
        return sample_candidate

    def test_overall_score_derived_from_dimension_rows(self, memory_db, sample_candidate):
        cand = self._scored(sample_candidate)
        # set a composite that disagrees with the dimension rows
        cand.scores["novelty"] = ScoreBreakdown(dimension="novelty", score=6.0)
        cand.overall_score = 9.99  # stale / wrong on purpose
        memory_db.save_candidate(cand)
        loaded = memory_db.get_candidate(cand.id)
        # the stored composite is the engine's value over the actual rows,
        # NOT the 9.99 that was set on the object
        assert loaded is not None
        assert loaded.overall_score != 9.99
        from blockchain_rd_lab.scoring import ScoringEngine, load_scoring_config

        expected = ScoringEngine(load_scoring_config()).score(loaded).overall_score
        assert loaded.overall_score == expected

    def test_scores_cleared_drops_composite(self, memory_db, sample_candidate):
        cand = self._scored(sample_candidate)
        cand.scores["novelty"] = ScoreBreakdown(dimension="novelty", score=6.0)
        memory_db.save_candidate(cand)
        assert memory_db.get_candidate(cand.id).overall_score is not None
        # now clear the dimension evidence and re-save: no evidence -> no score
        cand.scores.clear()
        memory_db.save_candidate(cand)
        loaded = memory_db.get_candidate(cand.id)
        assert loaded.scores == {}
        assert loaded.overall_score is None

    def test_dimension_update_rescores_atomically(self, memory_db, sample_candidate):
        # add a dimension, save, then change it and save again — the stored
        # composite must track the rows each time (no stale cache).
        from blockchain_rd_lab.scoring import ScoringEngine, load_scoring_config

        cand = self._scored(sample_candidate)
        eng = ScoringEngine(load_scoring_config())
        cand.scores["security"] = ScoreBreakdown(dimension="security", score=4.0)
        memory_db.save_candidate(cand)
        first = memory_db.get_candidate(cand.id)
        assert first.overall_score == eng.score(first).overall_score

        cand.scores["security"] = ScoreBreakdown(dimension="security", score=9.0)
        cand.scores["game_theory"] = ScoreBreakdown(dimension="game_theory", score=8.0)
        memory_db.save_candidate(cand)
        second = memory_db.get_candidate(cand.id)
        assert second.overall_score == eng.score(second).overall_score
        assert second.overall_score != first.overall_score

    def test_unscored_status_never_gains_a_composite(self, memory_db, sample_candidate):
        """A candidate below the SCORED lifecycle (here: RED_TEAM) that
        carries stage sub-scores must NOT gain an overall composite on
        save — scoring happens once, at the score stage (§19/§35)."""
        for st in (
            CandidateStatus.RESEARCHING,
            CandidateStatus.PRIOR_ART_CHECKED,
            CandidateStatus.FORMALIZED,
            CandidateStatus.SIMULATING,
            CandidateStatus.RED_TEAM,
        ):
            sample_candidate.transition(st)
        sample_candidate.scores["novelty"] = ScoreBreakdown(dimension="novelty", score=6.0)
        memory_db.save_candidate(sample_candidate)
        loaded = memory_db.get_candidate(sample_candidate.id)
        assert loaded.status is CandidateStatus.RED_TEAM
        assert loaded.overall_score is None



class TestExperimentPersistence:
    def test_save_and_load(self, memory_db, sample_candidate):
        memory_db.save_candidate(sample_candidate)
        rec = ExperimentRecord(
            candidate_id=sample_candidate.id,
            parameters={"alpha": 0.5, "horizon_days": 365},
            seed=42,
            dataset="un_population_1950_2024",
            model="population_supply_v1",
            simulation_version="sim-0.1.0",
            results={"max_drawdown": 0.12, "final_supply": 1_050_000},
        )
        memory_db.save_experiment(rec)
        loaded = memory_db.get_experiment(rec.experiment_id)
        assert loaded is not None
        assert loaded.seed == 42
        assert loaded.parameters["alpha"] == 0.5
        assert loaded.results["final_supply"] == 1_050_000
        # Full reproducibility fields present (§21).
        for field in ("experiment_id", "candidate_id", "timestamp", "git_commit",
                     "parameters", "dataset", "model", "seed", "simulation_version", "results"):
            assert field in loaded.model_dump()

    def test_iter_by_candidate(self, memory_db, sample_candidate):
        memory_db.save_candidate(sample_candidate)
        for i in range(3):
            memory_db.save_experiment(
                ExperimentRecord(candidate_id=sample_candidate.id, seed=i)
            )
        got = list(memory_db.iter_experiments(candidate_id=sample_candidate.id))
        assert len(got) == 3


class TestAgentRunPersistence:
    def test_save_and_iter(self, memory_db, sample_candidate):
        memory_db.save_candidate(sample_candidate)
        run = AgentRunRecord(
            agent_name="discovery",
            candidate_id=sample_candidate.id,
            status="success",
            prompt_tokens=120,
            completion_tokens=80,
            output={"ideas": 1},
        )
        memory_db.save_agent_run(run)
        runs = list(memory_db.iter_agent_runs(agent_name="discovery"))
        assert len(runs) == 1
        assert runs[0].prompt_tokens == 120
        assert runs[0].output == {"ideas": 1}


class TestRedTeamResultTimestamp:
    """r48 follow-up: save_redteam_result's created_at override exists for
    §21 evidence recovery — a restored report keeps its ORIGINAL timestamp,
    which the release package's saw-the-final-version judgment is ordered on."""

    def test_created_at_override_roundtrips(self, memory_db, sample_candidate):
        from datetime import datetime

        memory_db.save_candidate(sample_candidate)
        original = datetime(2026, 9, 8, 11, 4, 14)
        memory_db.save_redteam_result(
            candidate_id=sample_candidate.id,
            agent_name="red_team",
            report_json='{"verdict": "survives"}',
            verdict="survives",
            created_at=original,
        )
        rows = memory_db.list_redteam_results(candidate_id=sample_candidate.id)
        assert len(rows) == 1
        assert str(rows[0]["created_at"]).startswith("2026-09-08T11:04:14")

    def test_created_at_defaults_to_now(self, memory_db, sample_candidate):
        memory_db.save_candidate(sample_candidate)
        memory_db.save_redteam_result(
            candidate_id=sample_candidate.id,
            agent_name="oracle",
            report_json='{"v": 1}',
        )
        rows = memory_db.list_redteam_results(candidate_id=sample_candidate.id)
        assert rows[0]["created_at"]  # non-null, set by the DB default


class TestFileBackedDatabase:
    def test_persists_across_connections(self, tmp_path, sample_candidate):
        path = tmp_path / "lab.db"
        db1 = LabDatabase(path)
        db1.create_all()
        db1.save_candidate(sample_candidate)

        db2 = LabDatabase(path)
        db2.create_all()
        loaded = db2.get_candidate(sample_candidate.id)
        assert loaded is not None
        assert loaded.name == sample_candidate.name
