"""Phase 6 ranking tests: deterministic scoring, §20 gate, ranking, finalists."""

from __future__ import annotations

import json

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.ranking.service import RankingService
from blockchain_rd_lab.schemas import (
    Candidate,
    CandidateStatus,
    FatalFlaw,
    ScoreBreakdown,
)


def make_candidate(name: str, scores: dict[str, float] | None = None, **overrides) -> Candidate:
    base = dict(
        name=name,
        category="monetary",
        description="Supply adjusts to a verified external anchor index.",
        core_mechanism="S_t1 = S_t * (1 + clip(alpha * dX_t / X_t, f, c)).",
    )
    base.update(overrides)
    cand = Candidate(**base)
    for dim, score in (scores or {}).items():
        cand.scores[dim] = ScoreBreakdown(dimension=dim, score=score)
    return cand


def advance_to_red_team(db: LabDatabase, cand: Candidate) -> Candidate:
    cand.transition(CandidateStatus.RESEARCHING)
    cand.transition(CandidateStatus.PRIOR_ART_CHECKED)
    cand.transition(CandidateStatus.FORMALIZED)
    cand.transition(CandidateStatus.SIMULATING)
    cand.transition(CandidateStatus.RED_TEAM)
    db.save_candidate(cand)
    return cand


# ---------------------------------------------------------------------------
# Scoring + §11 transitions
# ---------------------------------------------------------------------------


class TestScoring:
    def test_score_candidate_sets_overall_and_advances(self, memory_db):
        cand = make_candidate(
            "Scored One",
            scores={
                "novelty": 6.0,
                "economic_coherence": 7.0,
                "game_theory": 5.5,
                "security": 5.0,
                "oracle_feasibility": 5.0,
                "market_demand": 6.0,
            },
        )
        memory_db.save_candidate(cand)
        advance_to_red_team(memory_db, cand)

        service = RankingService(memory_db)
        result = service.score_candidate(cand)

        assert 0.0 <= result.overall_score <= 10.0
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.SCORED
        assert stored.overall_score == result.overall_score

    def test_deterministic_same_scores_same_result(self, memory_db):
        scores = {"novelty": 8.0, "security": 4.0, "market_demand": 6.0}
        c1 = make_candidate("Alpha", scores=scores)
        c2 = make_candidate("Beta", scores=scores)
        for c in (c1, c2):
            memory_db.save_candidate(c)
            advance_to_red_team(memory_db, c)
        service = RankingService(memory_db)
        r1 = service.score_candidate(c1)
        r2 = service.score_candidate(c2)
        assert r1.overall_score == r2.overall_score

    def test_confirmed_flaw_rejects_even_from_red_team(self, memory_db):
        cand = make_candidate("Flawed", scores={"novelty": 9.0})
        cand.fatal_flaws.append(
            FatalFlaw(
                flaw_id="ff-x",
                category="security",
                description="unfixable",
                confirmed=True,
                identified_by="red_team",
            )
        )
        memory_db.save_candidate(cand)
        advance_to_red_team(memory_db, cand)

        service = RankingService(memory_db)
        result = service.score_candidate(cand)
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.REJECTED
        # §20: capped, never averaged away
        assert result.overall_score <= 5.0

    def test_score_all_isolation(self, memory_db):
        good = make_candidate("Good One", scores={"novelty": 7.0})
        memory_db.save_candidate(good)
        advance_to_red_team(memory_db, good)
        # second candidate stays RED_TEAM (already SCORED above advances one;
        # save a fresh one to be scored in the batch)
        pending = make_candidate("Pending One", scores={"novelty": 6.0})
        memory_db.save_candidate(pending)
        advance_to_red_team(memory_db, pending)

        service = RankingService(memory_db)
        results = service.score_all()
        assert len(results) == 2
        for r in results:
            assert r.overall_score >= 0.0


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


class TestRanking:
    def _three_scored(self, memory_db):
        a = make_candidate("Alpha Rule", scores={"novelty": 6.0, "security": 6.0})
        b = make_candidate("Beta Rule", scores={"novelty": 8.0, "security": 7.0})
        c = make_candidate("Gamma Rule", scores={"novelty": 4.0, "security": 4.0})
        for cand in (a, b, c):
            memory_db.save_candidate(cand)
            advance_to_red_team(memory_db, cand)
            RankingService(memory_db).score_candidate(cand)
        return a, b, c

    def test_rank_orders_by_score_desc(self, memory_db):
        a, b, c = self._three_scored(memory_db)
        service = RankingService(memory_db)
        result = service.rank()
        assert [r.candidate_id for r in result.rows] == [b.id, a.id, c.id]
        assert result.rows[0].rank == 1
        assert result.rows[1].rank == 2
        assert result.rows[2].rank == 3

    def test_rank_tiebreak_by_name_asc(self, memory_db):
        # Same scores -> stable alphabetical order.
        x = make_candidate("Zeta", scores={"novelty": 6.0})
        y = make_candidate("Alpha", scores={"novelty": 6.0})
        for cand in (x, y):
            memory_db.save_candidate(cand)
            advance_to_red_team(memory_db, cand)
            RankingService(memory_db).score_candidate(cand)
        result = RankingService(memory_db).rank()
        assert [r.name for r in result.rows] == ["Alpha", "Zeta"]

    def test_confirmed_flaw_excluded_from_ranking(self, memory_db):
        a, _b, _c = self._three_scored(memory_db)
        # Corrupt a: give it a confirmed flaw post-scoring (stored state).
        stored = memory_db.get_candidate(a.id)
        assert stored is not None
        stored.fatal_flaws.append(
            FatalFlaw(
                flaw_id="ff-late",
                category="economic",
                description="late discovery",
                confirmed=True,
                identified_by="economist",
            )
        )
        memory_db.save_candidate(stored)

        result = RankingService(memory_db).rank()
        ids = [r.candidate_id for r in result.rows]
        assert a.id not in ids
        assert result.rejected_by_gate == 1

    def test_unscored_candidates_excluded(self, memory_db):
        unscored = make_candidate("Never Scored")
        memory_db.save_candidate(unscored)
        advance_to_red_team(memory_db, unscored)
        result = RankingService(memory_db).rank()
        assert all(r.candidate_id != unscored.id for r in result.rows)


# ---------------------------------------------------------------------------
# Finalist selection (§7)
# ---------------------------------------------------------------------------


class TestFinalists:
    def test_top_n_promotes_to_finalist(self, memory_db):
        a = make_candidate("Alpha Rule", scores={"novelty": 6.0})
        b = make_candidate("Beta Rule", scores={"novelty": 9.0})
        c = make_candidate("Gamma Rule", scores={"novelty": 3.0})
        for cand in (a, b, c):
            memory_db.save_candidate(cand)
            advance_to_red_team(memory_db, cand)
            RankingService(memory_db).score_candidate(cand)

        service = RankingService(memory_db)
        selection = service.select_finalists(count=2)
        assert [f.candidate_id for f in selection.finalists] == [b.id, a.id]
        assert selection.cutoff_score is not None

        for fid in (b.id, a.id):
            stored = memory_db.get_candidate(fid)
            assert stored is not None
            assert stored.status is CandidateStatus.FINALIST
        gamma = memory_db.get_candidate(c.id)
        assert gamma is not None
        assert gamma.status is CandidateStatus.SCORED  # not promoted

    def test_no_promote_leaves_status(self, memory_db):
        cand = make_candidate("Solo", scores={"novelty": 7.0})
        memory_db.save_candidate(cand)
        advance_to_red_team(memory_db, cand)
        RankingService(memory_db).score_candidate(cand)

        selection = RankingService(memory_db).select_finalists(count=1, promote=False)
        assert len(selection.finalists) == 1
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.SCORED

    def test_fewer_than_requested(self, memory_db):
        cand = make_candidate("Only One", scores={"novelty": 7.0})
        memory_db.save_candidate(cand)
        advance_to_red_team(memory_db, cand)
        RankingService(memory_db).score_candidate(cand)

        selection = RankingService(memory_db).select_finalists(count=5)
        assert len(selection.finalists) == 1
        assert selection.available == 1
        assert "1" in selection.note


# ---------------------------------------------------------------------------
# Batch run + artifact
# ---------------------------------------------------------------------------


class TestRunRanking:
    def test_run_ranking_end_to_end(self, memory_db, tmp_path):
        for _i, (name, score) in enumerate(
            [("A", 7.0), ("B", 9.0), ("C", 5.0), ("D", 6.0), ("E", 8.0), ("F", 4.0)]
        ):
            cand = make_candidate(f"Rule {name}", scores={"novelty": score})
            memory_db.save_candidate(cand)
            advance_to_red_team(memory_db, cand)

        service = RankingService(memory_db)
        summary = service.run_ranking(finalists=3, artifacts_dir=tmp_path)

        assert summary.attempted == 6
        assert summary.scored == 6
        assert summary.finalists == 3
        scores_in_order = [r["overall_score"] for r in summary.per_candidate]
        assert scores_in_order == sorted(scores_in_order, reverse=True)

        artifact = tmp_path / "ranking-latest.json"
        assert artifact.exists()
        payload = json.loads(artifact.read_text())
        assert payload["summary"]["finalists"] == 3
        assert len(payload["finalists"]) == 3
        statuses = {row["candidate_id"]: row["status"] for row in payload["ranking"]}
        finalists_ids = {f["candidate_id"] for f in payload["finalists"]}
        assert all(statuses[cid] == "finalist" for cid in finalists_ids if cid in statuses)

    def test_empty_ranking_notes_no_candidates(self, memory_db, tmp_path):
        service = RankingService(memory_db)
        selection = service.select_finalists(count=5)
        assert selection.finalists == []
        assert selection.cutoff_score is None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestRankCommand:
    def _setup(self, db):
        for name, score in [("Alpha Rule", 6.0), ("Beta Rule", 8.0)]:
            cand = make_candidate(name, scores={"novelty": score})
            db.save_candidate(cand)
            advance_to_red_team(db, cand)

    def test_rank_batch(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        self._setup(db)

        runner = CliRunner()
        result = runner.invoke(app, ["rank", "--finalists", "1"])
        assert result.exit_code == 0
        assert "FINALIST" in result.output
        stored = [
            c
            for c in db.list_candidates(limit=10)
            if c.status is CandidateStatus.FINALIST
        ]
        assert len(stored) == 1
        assert stored[0].name == "Beta Rule"

    def test_rank_no_promote(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        self._setup(db)

        runner = CliRunner()
        result = runner.invoke(app, ["rank", "--no-promote"])
        assert result.exit_code == 0
        finalists = [
            c
            for c in db.list_candidates(limit=10)
            if c.status is CandidateStatus.FINALIST
        ]
        assert finalists == []  # ranked, none promoted
        scored = [
            c
            for c in db.list_candidates(limit=10)
            if c.status is CandidateStatus.SCORED
        ]
        assert len(scored) == 2

    def test_rank_empty_lab(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["rank"])
        assert result.exit_code == 0
        assert "No RED_TEAM" in result.output

    def test_score_command_transitions_to_scored(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        cand = make_candidate("Score Me", scores={"novelty": 7.0})
        db.save_candidate(cand)
        advance_to_red_team(db, cand)

        runner = CliRunner()
        result = runner.invoke(app, ["score", cand.id])
        assert result.exit_code == 0
        stored = db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.SCORED
        assert stored.overall_score is not None
