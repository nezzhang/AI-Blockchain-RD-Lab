"""CLI tests using Typer's CliRunner (§36)."""

from __future__ import annotations

from typer.testing import CliRunner

from blockchain_rd_lab.cli import app
from blockchain_rd_lab.config import REPO_ROOT

runner = CliRunner()


class TestVersion:
    def test_version(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestInitAndStatus:
    def test_init(self, tmp_path, monkeypatch):
        monkeypatch.setattr("blockchain_rd_lab.config.CONFIG_DIR", tmp_path / "config")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()

    def test_status_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("blockchain_rd_lab.config.CONFIG_DIR", tmp_path / "config")
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "TOTAL" in result.output

    def test_status_with_candidate(self, tmp_path, monkeypatch):
        monkeypatch.setattr("blockchain_rd_lab.config.CONFIG_DIR", tmp_path / "config")
        from blockchain_rd_lab.config import load_config
        from blockchain_rd_lab.database import LabDatabase
        from blockchain_rd_lab.schemas import Candidate

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        cand = Candidate(name="X", category="c", description="d", core_mechanism="m")
        db.save_candidate(cand)

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "generated" in result.output
        db.delete_candidate(cand.id)


class TestScore:
    def test_score_unknown_candidate(self, tmp_path, monkeypatch):
        monkeypatch.setattr("blockchain_rd_lab.config.CONFIG_DIR", tmp_path / "config")
        result = runner.invoke(app, ["score", "cand-doesnotexist"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_score_stored_candidate(self, tmp_path, monkeypatch, fully_scored_candidate):
        monkeypatch.setattr("blockchain_rd_lab.config.CONFIG_DIR", tmp_path / "config")
        from blockchain_rd_lab.config import load_config
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
        db.delete_candidate(cand.id)


class TestSearch:
    def test_search_no_match(self, tmp_path, monkeypatch):
        monkeypatch.setattr("blockchain_rd_lab.config.CONFIG_DIR", tmp_path / "config")
        result = runner.invoke(app, ["search", "zzz-no-match"])
        assert result.exit_code == 0
        assert "No candidates" in result.output

    def test_search_match(self, tmp_path, monkeypatch, sample_candidate):
        monkeypatch.setattr("blockchain_rd_lab.config.CONFIG_DIR", tmp_path / "config")
        from blockchain_rd_lab.config import load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        db.save_candidate(sample_candidate)

        result = runner.invoke(app, ["search", "population"])
        assert result.exit_code == 0
        assert "Population-Linked" in result.output
        db.delete_candidate(sample_candidate.id)


class TestPhaseStubs:
    """Pipeline commands exist as stubs and fail fast with a phase pointer."""

    @staticmethod
    def _seed_db():
        from blockchain_rd_lab.config import load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        return db

    def test_stub_commands_exit_nonzero(self):
        for cmd in (["discover"], ["research"], ["prior-art"], ["formalize"],
                    ["simulate"], ["redteam"], ["rank"], ["report"], ["pipeline"]):
            result = runner.invoke(app, cmd)
            assert result.exit_code == 2, cmd
            assert "PHASE" in result.output or "later phase" in result.output

    def test_stub_mentions_phase(self):
        result = runner.invoke(app, ["discover"])
        assert "PHASE 1" in result.output
