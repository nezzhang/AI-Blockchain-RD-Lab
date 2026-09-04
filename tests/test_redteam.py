"""Phase 5 adversarial testing tests: agents, §20 gate, service, DB, CLI."""

from __future__ import annotations

import json

import pytest

from blockchain_rd_lab.agents import MockLLMProvider
from blockchain_rd_lab.agents.base import LLMError
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.redteam import (
    GameTheoryReport,
    OracleReport,
    RedTeamReport,
    SecurityReport,
)
from blockchain_rd_lab.redteam.agents import (
    GameTheoryAgent,
    OracleAgent,
    RedTeamAgent,
    SecurityAgent,
    build_redteam_fixture,
    fixture_redteam_responses,
)
from blockchain_rd_lab.redteam.service import RedTeamService
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


def make_candidate(**overrides) -> Candidate:
    base = dict(
        name="Anchor-Coupled Supply Rule",
        category="monetary",
        description="Supply adjusts to a verified external anchor index.",
        core_mechanism="S_t1 = S_t * (1 + clip(alpha * dX_t / X_t, f, c)).",
        oracle_required=True,
    )
    base.update(overrides)
    return Candidate(**base)


def make_brief() -> CandidateBrief:
    return CandidateBrief.from_candidate(make_candidate())


def advance_to_simulating(db: LabDatabase, cand: Candidate) -> Candidate:
    cand.transition(CandidateStatus.RESEARCHING)
    cand.transition(CandidateStatus.PRIOR_ART_CHECKED)
    cand.transition(CandidateStatus.FORMALIZED)
    cand.transition(CandidateStatus.SIMULATING)
    db.save_candidate(cand)
    return cand


def queue_all_reports(provider: MockLLMProvider, brief: CandidateBrief, **kwargs) -> None:
    for response in fixture_redteam_responses([brief], **kwargs):
        provider.queue_response(response)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_fixture_reports_validate(self):
        brief = make_brief()
        reports = build_redteam_fixture(brief)
        gt = GameTheoryReport.model_validate(reports["game_theory"])
        sec = SecurityReport.model_validate(reports["security"])
        orc = OracleReport.model_validate(reports["oracle"])
        rt = RedTeamReport.model_validate(reports["red_team"])
        assert gt.game_theory_score == 5.5
        assert sec.hardest_attack_to_defend
        assert orc.manipulation_vectors
        assert rt.verdict == "vulnerable"

    def test_verdict_pattern_enforced(self):
        brief = make_brief()
        reports = build_redteam_fixture(brief)
        reports["red_team"]["verdict"] = "destroyed"
        with pytest.raises(Exception, match=r"verdict|pattern"):
            RedTeamReport.model_validate(reports["red_team"])

    def test_empty_attack_vectors_rejected(self):
        brief = make_brief()
        reports = build_redteam_fixture(brief)
        reports["game_theory"]["attack_vectors"] = []
        with pytest.raises(Exception, match=r"attack_vectors|min_length|list"):
            GameTheoryReport.model_validate(reports["game_theory"])

    def test_summary_too_short_rejected(self):
        brief = make_brief()
        reports = build_redteam_fixture(brief)
        reports["security"]["summary"] = "short"
        with pytest.raises(Exception, match=r"summary|string_too_short|min_length"):
            SecurityReport.model_validate(reports["security"])

    def test_attacker_role_pattern_enforced(self):
        brief = make_brief()
        reports = build_redteam_fixture(brief)
        reports["oracle"]["manipulation_vectors"][0]["attacker"] = "hedge fund"
        with pytest.raises(Exception, match=r"attacker|pattern"):
            OracleReport.model_validate(reports["oracle"])

    def test_fatal_fixture_marks_fatal(self):
        brief = make_brief()
        reports = build_redteam_fixture(brief, fatal=True)
        rt = RedTeamReport.model_validate(reports["red_team"])
        assert rt.verdict == "fatal"


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class TestAgents:
    def test_game_theory_agent_happy_path(self, memory_db):
        provider = MockLLMProvider()
        brief = make_brief()
        queue_all_reports(provider, brief)
        agent = GameTheoryAgent(provider, database=memory_db)
        report, record = agent.execute(brief)
        assert isinstance(report, GameTheoryReport)
        assert record.status == "success"
        assert record.agent_name == "game_theory"

    def test_red_team_agent_is_strongest_tier(self, memory_db):
        from blockchain_rd_lab.agents.base import ModelTier

        provider = MockLLMProvider()
        agent = RedTeamAgent(provider, database=memory_db)
        assert agent.model_tier is ModelTier.STRONGEST
        assert agent.temperature == 0.6

    def test_agent_wrong_payload_rejected(self, memory_db):
        provider = MockLLMProvider()
        agent = SecurityAgent(provider, database=memory_db)
        with pytest.raises(TypeError, match="CandidateBrief"):
            agent.build_prompt("not a brief")

    def test_agent_llm_error_recorded(self, memory_db):
        provider = MockLLMProvider()
        provider.queue_error(LLMError("provider down"))
        agent = OracleAgent(provider, database=memory_db)
        with pytest.raises(LLMError):
            agent.execute(make_brief())

    def test_prompts_encode_missions(self):
        from blockchain_rd_lab.redteam.agents import (
            GAME_THEORY_SYSTEM_PROMPT,
            ORACLE_SYSTEM_PROMPT,
            RED_TEAM_SYSTEM_PROMPT,
            SECURITY_SYSTEM_PROMPT,
        )

        assert "rational profit maximizer" in GAME_THEORY_SYSTEM_PROMPT
        assert "death-spiral" in GAME_THEORY_SYSTEM_PROMPT
        assert "governance attacks" in SECURITY_SYSTEM_PROMPT
        assert "revision policy" in ORACLE_SYSTEM_PROMPT
        assert "DESTROY THE IDEA" in RED_TEAM_SYSTEM_PROMPT
        assert "death spiral" in RED_TEAM_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Service: §20 fatal-flaw gate (deterministic code, not prompts)
# ---------------------------------------------------------------------------


class TestFatalFlawGate:
    def _run(self, memory_db, **fixture_kwargs):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        advance_to_simulating(memory_db, cand)
        brief = CandidateBrief.from_candidate(cand)
        provider = MockLLMProvider()
        queue_all_reports(provider, brief, **fixture_kwargs)
        service = RedTeamService(provider, memory_db)
        result = service.redteam_candidate(cand)
        return cand, memory_db.get_candidate(cand.id), result

    def test_vulnerable_verdict_survives_gate(self, memory_db):
        _, stored, result = self._run(memory_db, verdict="vulnerable")
        assert stored is not None
        assert stored.status is CandidateStatus.RED_TEAM
        assert result.rejected is False
        assert stored.has_confirmed_fatal_flaw is False
        # Dimension scores attached
        assert "game_theory" in stored.scores
        assert "security" in stored.scores
        assert "oracle_feasibility" in stored.scores

    def test_fatal_verdict_requires_profitable_attack_to_confirm(self, memory_db):
        # fatal verdict BUT fixture's strongest attack IS profitable by
        # default → confirmed. Use survives to flip the other branch first.
        _, stored, result = self._run(memory_db, verdict="fatal")
        assert stored is not None
        assert stored.status is CandidateStatus.REJECTED
        assert result.rejected is True
        assert stored.has_confirmed_fatal_flaw is True
        flaw = stored.fatal_flaws[-1]
        assert flaw.identified_by == "red_team"
        assert flaw.confirmed

    def test_fatal_verdict_nonprofitable_not_confirmed(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        advance_to_simulating(memory_db, cand)
        brief = CandidateBrief.from_candidate(cand)
        provider = MockLLMProvider()
        reports = build_redteam_fixture(brief, verdict="fatal")
        reports["red_team"]["strongest_attack_is_profitable"] = False
        for name in ("game_theory", "security", "oracle", "red_team"):
            provider.queue_response(json.dumps(reports[name]))
        service = RedTeamService(provider, memory_db)
        result = service.redteam_candidate(cand)
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        # Fatal verdict alone (unprofitable attack) does NOT reject: the
        # deterministic gate requires profitability (§20: confirmed flaws).
        assert stored.status is CandidateStatus.RED_TEAM
        assert result.rejected is False

    def test_agent_failure_leaves_status_unchanged(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        advance_to_simulating(memory_db, cand)
        provider = MockLLMProvider()  # empty → provider raises LLMError
        provider.queue_error(LLMError("down"))
        service = RedTeamService(provider, memory_db)
        result = service.redteam_candidate(cand)
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.SIMULATING  # untouched
        assert len(result.errors) == 4
        assert result.rejected is False


class TestServiceBatch:
    def test_redteam_all_isolation(self, memory_db, tmp_path):
        c1 = make_candidate()
        memory_db.save_candidate(c1)
        advance_to_simulating(memory_db, c1)
        c2 = make_candidate(name="Broken Oracle Feed")
        memory_db.save_candidate(c2)
        advance_to_simulating(memory_db, c2)

        brief1 = CandidateBrief.from_candidate(c1)
        provider = MockLLMProvider()
        # c1 gets full fixtures; c2's responses are exhausted, so the mock
        # provider falls back to digest garbage which fails schema
        # validation → LLMValidationError per agent (§2 fail-closed).
        queue_all_reports(provider, brief1)

        service = RedTeamService(provider, memory_db, artifacts_dir=tmp_path)
        summary = service.redteam_all()
        assert summary.attempted == 2
        assert summary.completed == 1  # only c1 got four valid reports
        assert summary.errors == 1  # c2 recorded per-agent validation errors
        s1 = memory_db.get_candidate(c1.id)
        s2 = memory_db.get_candidate(c2.id)
        assert s1 is not None and s1.status is CandidateStatus.RED_TEAM
        assert s2 is not None and s2.status is CandidateStatus.SIMULATING
        # Artifact written (§22/§29: failures visible, not hidden)
        assert (tmp_path / "redteam-latest.json").exists()
        payload = json.loads((tmp_path / "redteam-latest.json").read_text())
        assert payload["attempted"] == 2

    def test_reports_persisted_to_redteam_results(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        advance_to_simulating(memory_db, cand)
        brief = CandidateBrief.from_candidate(cand)
        provider = MockLLMProvider()
        queue_all_reports(provider, brief)
        service = RedTeamService(provider, memory_db)
        service.redteam_candidate(cand)

        rows = memory_db.list_redteam_results(cand.id)
        agents = {r["agent_name"] for r in rows}
        assert agents == {"game_theory", "security", "oracle", "red_team"}
        rt_row = next(r for r in rows if r["agent_name"] == "red_team")
        assert rt_row["verdict"] == "vulnerable"
        # Report JSON round-trips through the schema
        report = RedTeamReport.model_validate(json.loads(rt_row["report_json"]))
        assert report.verdict == "vulnerable"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestRedTeamCommand:
    def test_unknown_candidate(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["redteam", "cand-nope", "--mock-fixtures"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_requires_simulating_status(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        cand = make_candidate(name="Fresh Generated")
        db.save_candidate(cand)

        runner = CliRunner()
        result = runner.invoke(app, ["redteam", cand.id, "--mock-fixtures"])
        assert result.exit_code == 1
        assert "simulating" in result.output

    def test_no_simulating_candidates(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["redteam", "--mock-fixtures"])
        assert result.exit_code == 0
        assert "No SIMULATING" in result.output

    def test_batch_over_candidates(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        c = make_candidate(name="Batch Candidate")
        db.save_candidate(c)
        advance_to_simulating(db, c)

        runner = CliRunner()
        result = runner.invoke(app, ["redteam", "--mock-fixtures"])
        assert result.exit_code == 0
        assert "vulnerable" in result.output
        stored = db.get_candidate(c.id)
        assert stored is not None
        assert stored.status is CandidateStatus.RED_TEAM

    def test_dry_mock_fails_closed(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        c = make_candidate(name="Dry Mock Target")
        db.save_candidate(c)
        advance_to_simulating(db, c)

        runner = CliRunner()
        result = runner.invoke(app, ["redteam"])
        assert result.exit_code == 2
        assert "mock-fixtures" in result.output
