"""CLI tests using Typer's CliRunner (§36).

All tests run against an isolated tmp database (see conftest.tmp_lab_dir) —
the real lab database is never touched.
"""

from __future__ import annotations

from typer.testing import CliRunner

from blockchain_rd_lab.cli import app

runner = CliRunner()


class TestVersion:
    def test_version(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestInitAndStatus:
    def test_init(self, tmp_lab_dir):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()

    def test_status_empty(self, tmp_lab_dir):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "TOTAL" in result.output

    def test_status_with_candidate(self, tmp_lab_dir, sample_candidate):
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        db.save_candidate(sample_candidate)

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "generated" in result.output


class TestScore:
    def test_score_unknown_candidate(self, tmp_lab_dir):
        result = runner.invoke(app, ["score", "cand-doesnotexist"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_score_stored_candidate(self, tmp_lab_dir, fully_scored_candidate):
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase
        from blockchain_rd_lab.schemas import FatalFlaw

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        cand = fully_scored_candidate
        cand.fatal_flaws.append(
            FatalFlaw(flaw_id="ff-1", category="oracle", description="oracle manip", confirmed=True)
        )
        db.save_candidate(cand)

        result = runner.invoke(app, ["score", cand.id])
        assert result.exit_code == 0
        assert "FATAL FLAW" in result.output


class TestSearch:
    def test_search_no_match(self, tmp_lab_dir):
        result = runner.invoke(app, ["search", "zzz-no-match"])
        assert result.exit_code == 0
        assert "No candidates" in result.output

    def test_search_match(self, tmp_lab_dir, sample_candidate):
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        db.save_candidate(sample_candidate)

        result = runner.invoke(app, ["search", "population"])
        assert result.exit_code == 0
        # Rich wraps long names across lines in narrow consoles; the
        # candidate id must appear and at least one population hit exists.
        assert sample_candidate.id in result.output or "Population" in result.output


class TestPhaseStubs:
    """Remaining pipeline commands exist as stubs and fail fast (§7)."""

    def test_stub_commands_exit_nonzero(self):
        for cmd in (["rank"], ["report"], ["pipeline"]):
            result = runner.invoke(app, cmd)
            assert result.exit_code == 2, cmd
            assert "PHASE" in result.output or "later phase" in result.output

    def test_stub_mentions_phase(self):
        result = runner.invoke(app, ["rank"])
        assert "PHASE 6" in result.output


class TestSeedCommand:
    def test_seed_population_money(self, tmp_lab_dir):
        result = runner.invoke(app, ["seed", "--experiment", "population-money"])
        assert result.exit_code == 0, result.output
        assert "seeded" in result.output

    def test_seed_unknown_experiment(self, tmp_lab_dir):
        result = runner.invoke(app, ["seed", "--experiment", "nope"])
        assert result.exit_code == 1
        assert "Unknown experiment" in result.output


class TestResearchCommands:
    """Phase 2: research / prior-art / filter against the isolated tmp DB."""

    def _seed_one(self, tmp_lab_dir):
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase
        from blockchain_rd_lab.schemas import Candidate

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        cand = Candidate(
            name="Fixture Researched Idea",
            category="monetary economics",
            description="desc",
            core_mechanism="m",
        )
        db.save_candidate(cand)
        return db, cand

    def test_research_mock_fixtures(self, tmp_lab_dir, monkeypatch):
        # Keep run artifacts out of the real research/ tree.
        monkeypatch.setattr("blockchain_rd_lab.cli.REPO_ROOT", tmp_lab_dir)
        db, cand = self._seed_one(tmp_lab_dir)
        result = runner.invoke(app, ["research", "--mock-fixtures"])
        assert result.exit_code == 0, result.output
        assert "Research" in result.output
        stored = db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status.value == "prior_art_checked"
        assert "novelty" in stored.scores

    def test_research_dry_mock_provider_blocked(self, tmp_lab_dir):
        """A dry mock queue must fail closed, not emit digest garbage (§30)."""
        self._seed_one(tmp_lab_dir)
        result = runner.invoke(app, ["research"])  # provider = mock, no queue
        assert result.exit_code == 2
        assert "mock" in result.output

    def test_research_no_generated_candidates(self, tmp_lab_dir):
        result = runner.invoke(app, ["research", "--mock-fixtures"])
        assert result.exit_code == 0
        assert "No GENERATED" in result.output

    def test_prior_art_unknown_candidate(self, tmp_lab_dir):
        result = runner.invoke(app, ["prior-art", "cand-nope"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_filter_empty_is_noop(self, tmp_lab_dir):
        result = runner.invoke(app, ["filter"])
        assert result.exit_code == 0
        assert "kept" in result.output


class TestCLIImpolationGuards:
    def test_seed_does_not_persist_across_tests(self, tmp_lab_dir):
        """The real lab DB must be untouched by the test suite (§22)."""
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        names = [c.name for c in db.list_candidates()]
        assert "Fixture Researched Idea" not in names
