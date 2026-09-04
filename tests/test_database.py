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
