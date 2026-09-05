"""§34 loop tests: improve (RED_TEAM→IMPROVEMENT→RETEST) and retest
(RETEST→SIMULATING→RED_TEAM), with §2/§11/§35 discipline enforced.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.improvement import (
    AddressedAttack,
    ImprovementProposal,
)
from blockchain_rd_lab.improvement.agents import (
    ImprovementInput,
    build_improvement_fixture,
)
from blockchain_rd_lab.improvement.retest import RetestService
from blockchain_rd_lab.improvement.service import ImprovementService
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import CandidateStatus

# ---------------------------------------------------------------------------
# Test helpers: build a red-teamed candidate the improver can patch
# ---------------------------------------------------------------------------


def make_brief(cid: str = "cand-test") -> CandidateBrief:
    return CandidateBrief(
        candidate_id=cid,
        name="Test Mechanism",
        category="monetary",
        description="Supply follows an external anchor index.",
        core_mechanism="S_t1 = S_t * (1 + clip(alpha * dX_t / X_t, f, c)).",
    )


def store_formalized(db: LabDatabase, cand) -> None:
    """Bring a candidate from scratch to RED_TEAM status with reports."""
    from blockchain_rd_lab.formalization.agents import build_math_model_fixture
    from blockchain_rd_lab.redteam.agents import build_redteam_fixture

    db.save_candidate(cand)
    model = build_math_model_fixture(CandidateBrief.from_candidate(cand))
    db.save_math_model(
        candidate_id=cand.id,
        model_json=json.dumps(model),
        rationale="fixture formalization",
        version=1,
    )
    for target in (
        CandidateStatus.RESEARCHING,
        CandidateStatus.PRIOR_ART_CHECKED,
        CandidateStatus.FORMALIZED,
        CandidateStatus.SIMULATING,
    ):
        cand.transition(target)
        db.save_candidate(cand)
    # adversarial fixture reports (verdict=vulnerable, one profitable vector)
    brief = CandidateBrief.from_candidate(cand)
    reports = build_redteam_fixture(brief, verdict="vulnerable", fatal=False)
    for agent_name in ("game_theory", "security", "oracle", "red_team"):
        db.save_redteam_result(
            candidate_id=cand.id,
            agent_name=agent_name,
            report_json=json.dumps(reports[agent_name]),
            verdict="vulnerable",
        )
    cand.transition(CandidateStatus.RED_TEAM)
    db.save_candidate(cand)


def make_service(db, provider=None) -> ImprovementService:
    from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider

    return ImprovementService(provider or build_pipeline_provider(), db)


def make_candidate(cid: str = "cand-test"):
    from blockchain_rd_lab.schemas import Candidate

    return Candidate(
        id=cid,
        name="Test Mechanism",
        category="monetary",
        description="Supply adjusts to a verified external anchor index.",
        core_mechanism="S_t1 = S_t * (1 + clip(alpha * dX_t / X_t, f, c)).",
    )


# ---------------------------------------------------------------------------
# Improvement proposal schema (§2: proposals must be structured + honest)
# ---------------------------------------------------------------------------


class TestImprovementProposal:
    def test_proposal_requires_at_least_one_real_fix(self):
        with pytest.raises(ValidationError):
            ImprovementProposal.model_validate(
                {
                    "summary": "This proposal fixes nothing at all.",
                    "addressed_attacks": [
                        {
                            "agent_name": "red_team",
                            "vector_description": "anchor spike manipulation",
                            "fix_strategy": "we considered it and moved on",
                            "fixes_attack": False,
                        }
                    ],
                    "model": {"version": 2},
                }
            )

    def test_valid_proposal_validates(self):
        prop = ImprovementProposal.model_validate(
            {
                "summary": "Add a hard cap and EMA smoothing to the rule.",
                "addressed_attacks": [
                    {
                        "agent_name": "red_team",
                        "vector_description": "anchor spike manipulation",
                        "fix_strategy": "hard single-step cap bounds any move",
                        "fixes_attack": True,
                    }
                ],
                "model": {"version": 2},
            }
        )
        assert prop.addressed_attacks[0].fixes_attack is True

    def test_addressed_attack_bounds(self):
        with pytest.raises(ValidationError):
            AddressedAttack(
                agent_name="",
                vector_description="too short",
                fix_strategy="short",
            )


# ---------------------------------------------------------------------------
# Improvement fixture (offline §34)
# ---------------------------------------------------------------------------


class TestImprovementFixture:
    def test_fixture_patches_the_rule(self):
        from blockchain_rd_lab.formalization.agents import build_math_model_fixture

        brief = make_brief()
        base = build_math_model_fixture(brief)
        prop = build_improvement_fixture(
            brief, base, [{"agent": "red_team", "vector": "anchor spike"}]
        )
        model = MathModel.model_validate(prop["model"])
        assert model.version == 2
        assert not model.undeclared_symbols()
        assert not model.unused_symbols()
        # the S_t1 rule was REPLACED, not duplicated
        supply_rules = [
            e for e in model.equations if e.expression.strip().startswith("S_t1")
        ]
        assert len(supply_rules) == 1
        assert "c_max" in supply_rules[0].expression
        assert "X_smooth_t" in supply_rules[0].expression
        # §13 honesty preserved: the new open question is recorded
        assert any("multi-block" in q for q in model.open_questions)

    def test_fixture_model_executes_in_battery(self):
        from blockchain_rd_lab.formalization.agents import build_math_model_fixture
        from blockchain_rd_lab.simulation import (
            MechanismSimulation,
            ScenarioBattery,
        )

        brief = make_brief()
        base = build_math_model_fixture(brief)
        prop = build_improvement_fixture(
            brief, base, [{"agent": "red_team", "vector": "anchor spike"}]
        )
        model = MathModel.model_validate(prop["model"])
        battery = ScenarioBattery(MechanismSimulation(model), steps=30, seed=7)
        runs = battery.run()
        # Fixture patches must not break execution in ANY §15 scenario.
        assert runs, "battery produced no runs"
        for kind, run in runs.items():
            assert isinstance(run.metrics, dict), kind


# ---------------------------------------------------------------------------
# ImprovementService (§11 transitions + §35 isolation + §2 validation)
# ---------------------------------------------------------------------------


class TestImprovementService:
    def test_improve_candidate_transitions_to_retest(self, memory_db):
        cand = make_candidate()
        store_formalized(memory_db, cand)
        service = make_service(memory_db)
        outcome = service.improve_candidate(cand, offline=True)
        assert outcome.improved, outcome.errors
        assert outcome.new_version == 2
        assert outcome.attacks_addressed >= 1
        refreshed = memory_db.get_candidate(cand.id)
        assert refreshed is not None
        assert refreshed.status is CandidateStatus.RETEST

    def test_improve_requires_red_team_status(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)  # GENERATED
        service = make_service(memory_db)
        outcome = service.improve_candidate(cand, offline=True)
        assert not outcome.improved
        assert outcome.rejected_reason is not None
        assert "not red_team" in outcome.rejected_reason

    def test_improve_without_model_rejects_cleanly(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        for target in (
            CandidateStatus.RESEARCHING,
            CandidateStatus.PRIOR_ART_CHECKED,
            CandidateStatus.FORMALIZED,
            CandidateStatus.SIMULATING,
            CandidateStatus.RED_TEAM,
        ):
            cand.transition(target)
            memory_db.save_candidate(cand)
        service = make_service(memory_db)
        outcome = service.improve_candidate(cand, offline=True)
        assert not outcome.improved
        assert outcome.rejected_reason == "no formal model to patch"

    def test_invalid_patch_fails_closed(self, memory_db):
        """A patch that violates §13 integrity is rejected (§2)."""
        cand = make_candidate()
        store_formalized(memory_db, cand)

        class BadPatchProvider:
            name = "mock-bad"

            def complete_structured(self, messages, *, schema, **kwargs):
                return ImprovementProposal.model_validate(
                    {
                        "summary": "Patch that references undeclared symbols.",
                        "addressed_attacks": [
                            {
                                "agent_name": "red_team",
                                "vector_description": "anchor spike manipulation",
                                "fix_strategy": "use a mystery symbol to fix it",
                                "fixes_attack": True,
                            }
                        ],
                        "model": {
                            "candidate_id": cand.id,
                            "version": 2,
                            "variables": [
                                {
                                    "name": "supply",
                                    "symbol": "S_t",
                                    "role": "state",
                                    "units": "tokens",
                                    "description": "Supply.",
                                }
                            ],
                            "parameters": [],
                            "equations": [
                                {
                                    "name": "broken",
                                    "expression": "S_t1 = S_t * typo_symbol",
                                    "description": "Uses undeclared symbol.",
                                }
                            ],
                            "open_questions": ["Is the patch valid?"],
                            "rationale": "Deliberately invalid patch for tests.",
                        },
                    }
                )

        service = ImprovementService(BadPatchProvider(), memory_db)
        outcome = service.improve_candidate(cand, offline=False)
        assert not outcome.improved
        assert outcome.errors, "invalid patch must fail closed"
        refreshed = memory_db.get_candidate(cand.id)
        assert refreshed is not None
        # candidate stays at RED_TEAM — no §11 violation
        assert refreshed.status is CandidateStatus.RED_TEAM

    def test_improve_all_batch_and_isolation(self, memory_db):
        cand_a = make_candidate("cand-a")
        cand_b = make_candidate("cand-b")
        store_formalized(memory_db, cand_a)
        store_formalized(memory_db, cand_b)

        service = make_service(memory_db)
        summary = service.improve_all(limit=None, offline=True)
        assert summary.attempted == 2
        assert summary.improved == 2
        assert all(o.candidate_id for o in summary.per_candidate)


# ---------------------------------------------------------------------------
# RetestService (RETEST -> SIMULATING -> RED_TEAM; §20 gate re-evaluation)
# ---------------------------------------------------------------------------


class TestRetestService:
    def _improved(self, memory_db):
        cand = make_candidate()
        store_formalized(memory_db, cand)
        service = make_service(memory_db)
        outcome = service.improve_candidate(cand, offline=True)
        assert outcome.improved
        return memory_db.get_candidate(cand.id)

    def test_retest_full_loop(self, memory_db):
        cand = self._improved(memory_db)
        from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider

        service = RetestService(
            build_pipeline_provider(),
            memory_db,
            redteam_artifacts_dir=None,
        )
        outcome = service.retest_candidate(cand)
        assert outcome.resimulated, outcome.errors
        assert outcome.re_attacked, outcome.errors
        refreshed = memory_db.get_candidate(cand.id)
        assert refreshed is not None
        assert refreshed.status in (
            CandidateStatus.RED_TEAM,
            CandidateStatus.REJECTED,
        )

    def test_retest_requires_retest_status(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider

        service = RetestService(
            build_pipeline_provider(), memory_db, redteam_artifacts_dir=None
        )
        outcome = service.retest_candidate(cand)
        assert not outcome.resimulated
        assert any("not retest" in e for e in outcome.errors)

    def test_retest_all_batch(self, memory_db):
        self._improved(memory_db)
        from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider

        service = RetestService(
            build_pipeline_provider(),
            memory_db,
            redteam_artifacts_dir=None,
        )
        summary = service.retest_all(limit=None)
        assert summary.attempted >= 1
        assert summary.completed >= 1


# ---------------------------------------------------------------------------
# Pipeline integration (§34 stage order + resumability across the loop)
# ---------------------------------------------------------------------------


class TestPipelineLoop:
    def test_stage_list_includes_improve_and_retest(self):
        from blockchain_rd_lab.pipeline import PipelineService

        assert PipelineService.STAGES == (
            "discover",
            "research",
            "filter",
            "formalize",
            "simulate",
            "redteam",
            "improve",
            "retest",
            "score",
            "report",
        )

    def test_resume_after_improve_leaves_retest_pending(self, memory_db):
        """Interrupt after improve: candidates sit at RETEST; a later run
        re-runs retest (status-consumed) and proceeds (§35)."""
        from blockchain_rd_lab.pipeline import PipelineService
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        cand = make_candidate()
        store_formalized(memory_db, cand)
        service = PipelineService(
            build_pipeline_provider(),
            memory_db,
            repo_root=_tmp_root(),
            research_config=None,
        )
        s1 = service.run(count=2, target=2, finalists=2, stop_after="improve")
        assert s1.completed is False
        names = [s.stage for s in s1.stages]
        assert names[-1] == "improve"
        # candidate now at RETEST
        refreshed = memory_db.get_candidate(cand.id)
        assert refreshed is not None
        assert refreshed.status is CandidateStatus.RETEST

        # resume: retest consumes RETEST-status candidates
        s2 = PipelineService(
            build_pipeline_provider(),
            memory_db,
            repo_root=_tmp_root(),
            research_config=None,
        ).run(count=2, target=2, finalists=2)
        assert s2.completed is True
        stage_names = [s.stage for s in s2.stages]
        assert "retest" in stage_names and "report" in stage_names

    def test_improve_input_hint_in_prompt(self, memory_db):
        """The improver prompt embeds the current model and findings."""
        from blockchain_rd_lab.formalization.agents import build_math_model_fixture

        brief = make_brief()
        base = build_math_model_fixture(brief)
        payload = ImprovementInput(
            brief=brief,
            current_model=base,
            attack_findings=[{"agent": "red_team", "vector": "anchor spike"}],
        )
        from blockchain_rd_lab.improvement.agents import ImprovementAgent
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        agent = ImprovementAgent(build_pipeline_provider(), database=memory_db)
        messages = agent.build_prompt(payload)
        user = next(m for m in messages if m.role == "user")
        assert "CURRENT MODEL" in user.content
        assert "ADVERSARIAL FINDINGS" in user.content
        assert "anchor spike" in user.content


def _tmp_root():
    import tempfile
    from pathlib import Path

    d = Path(tempfile.mkdtemp(prefix="lab-pipeline-"))
    return d
