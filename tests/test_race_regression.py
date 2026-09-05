"""§35 race regression: pending improvements must not be finalized.

Round 1 and round 2 of the real bridge runs both orphaned authored
improvement proposals: the improve stage pended on a bridge answer
(LLMError recorded per-candidate), the pipeline continued anyway, and
the score stage finalized the candidate on its UNFIXED model — the fix
sat answered-but-never-consumed while the candidate was promoted.

The fix: _stage_score holds RED_TEAM candidates whose improvement is
unresolved (fresh findings still exist → improve did not complete).
They stay RED_TEAM; the next resumed run consumes the answer (replay
is free) and scores them honestly.

These tests reproduce the race deterministically with a fail-closed
provider (pending bridge request) and verify the hold.
"""

from __future__ import annotations

import json

import pytest

from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.pipeline import PipelineService
from blockchain_rd_lab.schemas import Candidate, CandidateStatus
from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider


def _advance_to_red_team(cid: str) -> Candidate:
    cand = Candidate(
        id=cid,
        name="Race Victim Mechanism",
        category="stablecoins",
        description="A mechanism orphaned by a pending improvement.",
        core_mechanism="S_t1 = S_t * (1 + clip(alpha * dX_t / X_t, -0.02, 0.02)).",
    )
    for st in (
        CandidateStatus.RESEARCHING,
        CandidateStatus.PRIOR_ART_CHECKED,
        CandidateStatus.FORMALIZED,
        CandidateStatus.SIMULATING,
        CandidateStatus.RED_TEAM,
    ):
        cand.transition(st)
    return cand


def _model(cid: str) -> MathModel:
    return MathModel(
        candidate_id=cid,
        variables=[
            {"name": "S_t", "symbol": "S_t", "role": "state", "units": "u",
             "description": "supply"},
            {"name": "S_t1", "symbol": "S_t1", "role": "state", "units": "u",
             "description": "next supply"},
            {"name": "X_t", "symbol": "X_t", "role": "input", "units": "i",
             "description": "index"},
            {"name": "dX_t", "symbol": "dX_t", "role": "input", "units": "i",
             "description": "index change"},
        ],
        parameters=[
            {"name": "alpha", "symbol": "alpha", "description": "coupling",
             "min_value": 0.0, "max_value": 1.0, "default": 0.5},
        ],
        equations=[
            {"name": "supply", "expression": "S_t1 = S_t * (1 + alpha * dX_t)",
             "description": "supply follows anchor"},
        ],
        assumptions=[{"statement": "observable anchor", "critical": False}],
        constraints=[],
        open_questions=["is alpha right?"],
        rationale="race regression model",
    )


def _profitable_redteam() -> str:
    return json.dumps(
        {
            "verdict": "vulnerable",
            "strongest_attack": "whale drains the reserve via redemptions",
            "strongest_attack_is_profitable": True,
            "attack_vectors": [
                {
                    "vector": "redemption drain",
                    "description": "whale drains the reserve via redemptions",
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                    "evidence_level": "HYPOTHESIS",
                }
            ],
            "what_would_save_it": "a redemption taper",
            "evidence_level": "HYPOTHESIS",
        }
    )


@pytest.fixture
def race_db(memory_db):
    cid = "cand-race1"
    cand = _advance_to_red_team(cid)
    memory_db.save_candidate(cand)
    memory_db.save_math_model(cid, _model(cid).model_dump_json(), "v1", version=1)
    for agent in ("red_team", "game_theory"):
        memory_db.save_redteam_result(
            candidate_id=cid,
            agent_name=agent,
            report_json=_profitable_redteam(),
            verdict="vulnerable",
        )
    return memory_db


class TestPendingImprovementHoldsScoring:
    def test_pending_bridge_holds_candidate_at_red_team(self, race_db, tmp_path):
        """The exact round-2 race: improve pends → score must NOT finalize."""
        from blockchain_rd_lab.agents.bridge import AgentBridgeProvider

        provider = AgentBridgeProvider(bridge_dir=str(tmp_path / ".bridge"))
        pipe = PipelineService(provider, race_db, repo_root=tmp_path, research_config=None)
        summary = pipe.run(count=1, target=1, finalists=1)

        # The candidate must still be RED_TEAM — never scored/finalized.
        cand = race_db.get_candidate("cand-race1")
        assert cand is not None
        assert cand.status is CandidateStatus.RED_TEAM, (
            "a candidate with a pending improvement must not be finalized "
            "on its unfixed model (§35 honesty gate)"
        )
        assert cand.overall_score is None or cand.overall_score == 0.0

        # The score stage reported the hold.
        score = next(s for s in summary.stages if s.stage == "score")
        assert score.errors, "the held candidate must be reported"
        assert "held" in score.errors[0]
        assert not summary.completed or score.errors  # run may finish; hold recorded

    def test_resolved_improvement_scores_normally(self, race_db, tmp_path):
        """No pending findings → score proceeds as before (no regression)."""
        pipe = PipelineService(
            build_pipeline_provider(), race_db, repo_root=tmp_path, research_config=None
        )
        # Offline fixtures resolve the improvement; the mock provider
        # answers everything. The candidate should reach SCORED/FINALIST.
        pipe.run(count=1, target=1, finalists=1)
        cand = race_db.get_candidate("cand-race1")
        assert cand is not None
        assert cand.status in (
            CandidateStatus.SCORED,
            CandidateStatus.FINALIST,
        ), "resolved improvements must score normally"

    def test_improvement_blocked_detects_fresh_findings(self, race_db, tmp_path):
        """The gate itself: fresh findings + still RED_TEAM = blocked."""
        from blockchain_rd_lab.agents.bridge import AgentBridgeProvider

        provider = AgentBridgeProvider(bridge_dir=str(tmp_path / ".bridge"))
        pipe = PipelineService(provider, race_db, repo_root=tmp_path, research_config=None)
        blocked = pipe._improvement_blocked()
        assert "cand-race1" in blocked

    def test_blocked_set_empty_when_no_fresh_findings(self, memory_db, tmp_path):
        """Converged candidates (all findings addressed) are never held."""

        # Same history as the race fixture but WITH a v2 fix addressing
        # the attack → converged → not blocked.
        cid = "cand-race2"
        cand = _advance_to_red_team(cid)
        memory_db.save_candidate(cand)
        m = _model(cid)
        memory_db.save_math_model(cid, m.model_dump_json(), "v1", version=1)
        for agent in ("red_team", "game_theory"):
            memory_db.save_redteam_result(
                candidate_id=cid,
                agent_name=agent,
                report_json=_profitable_redteam(),
                verdict="vulnerable",
            )
        from blockchain_rd_lab.improvement.agents import (
            ImprovementProposal,
        )

        proposal = ImprovementProposal(
            candidate_id=cid,
            summary="taper the redemption flow so drains self-limit",
            addressed_attacks=[
                {
                    "agent_name": "red_team",
                    "vector_description": "whale drains the reserve via redemptions",
                    "fix_strategy": "redemption taper per block",
                    "fixes_attack": True,
                }
            ],
            model=m.model_copy(update={"version": 2}).model_dump(),
        )
        memory_db.save_math_model(
            cid,
            json.dumps(proposal.model),
            proposal.summary,
            version=2,
        )
        pipe = PipelineService(
            build_pipeline_provider(), memory_db, repo_root=tmp_path, research_config=None
        )
        assert pipe._improvement_blocked() == set()
