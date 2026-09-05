"""§33→§34 integration tests: knowledge-graph-backed improvement.

Two behaviors:
- prior_fixes: the improver prompt carries graph-derived records of how
  similar attacks were fixed on other candidates (§32 reuse).
- already-addressed: findings whose attacks the CURRENT model version
  already ADDRESSES (per §33 ADDRESSES edges) are filtered out — the
  convergence rule is deterministic code, not LLM judgment (§2).
"""

from __future__ import annotations

import json

from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.improvement.agents import (
    ImprovementAgent,
    ImprovementInput,
    PriorFix,
)
from blockchain_rd_lab.improvement.service import (
    ImprovementService,
    _matches_any,
    _tokens,
)
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import Candidate, CandidateStatus
from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider


def _mk_candidate(cid: str = "cand-g1") -> Candidate:
    cand = Candidate(
        id=cid,
        name="Graph Wired Mechanism",
        category="stablecoins",
        description="A mechanism whose improvements consult the graph.",
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


def _mk_model(cid: str) -> MathModel:
    return MathModel(
        candidate_id=cid,
        variables=[
            {"name": "S_t", "symbol": "S_t", "role": "state", "units": "units",
             "description": "Supply at t"},
            {"name": "S_t1", "symbol": "S_t1", "role": "state", "units": "units",
             "description": "Supply at t+1"},
            {"name": "X_t", "symbol": "X_t", "role": "input", "units": "index",
             "description": "Anchor index"},
            {"name": "dX_t", "symbol": "dX_t", "role": "input", "units": "index",
             "description": "Anchor change"},
        ],
        parameters=[
            {"name": "alpha", "symbol": "alpha", "description": "coupling",
             "min_value": 0.0, "max_value": 1.0, "default": 0.5},
        ],
        equations=[
            {"name": "supply", "expression": "S_t1 = S_t * (1 + alpha * dX_t)",
             "description": "supply follows anchor"},
        ],
        assumptions=[{"statement": "anchor observable", "critical": False}],
        constraints=[],
        open_questions=["is alpha right?"],
        rationale="test model for graph wiring",
    )


def _mk_attack_report(description: str, profitable: bool = True) -> dict:
    return {
        "verdict": "vulnerable",
        "strongest_attack": description,
        "strongest_attack_is_profitable": profitable,
        "attack_vectors": [
            {
                "vector": "test vector",
                "description": description,
                "attacker": "whale",
                "profitable_for_attacker": profitable,
                "requires_collusion": False,
                "evidence_level": "HYPOTHESIS",
            }
        ],
        "what_would_save_it": "a fix",
        "evidence_level": "HYPOTHESIS",
    }


def _store_fixed_history(db, cid: str, attack_text: str, fix_text: str) -> None:
    """One candidate with a v1→v2 improvement addressing `attack_text`."""
    cand = _mk_candidate(cid)
    db.save_candidate(cand)
    m = _mk_model(cid)
    db.save_math_model(cid, m.model_dump_json(), "v1", version=1)
    m2 = m.model_copy(update={"version": 2})
    db.save_math_model(cid, m2.model_dump_json(), fix_text, version=2)
    db.save_redteam_result(
        candidate_id=cid,
        agent_name="red_team",
        report_json=json.dumps(_mk_attack_report(attack_text)),
        verdict="vulnerable",
    )


# ---------------------------------------------------------------------------
# Token matching (the convergence detector)
# ---------------------------------------------------------------------------


class TestTokenMatching:
    def test_tokens_normalizes(self):
        t = _tokens("Whale drives R_t to the floor via redemptions!")
        assert "whale" in t and "floor" in t and "redemptions" in t
        assert "the" not in t and "to" not in t  # stopwords/short dropped

    def test_matches_same_attack(self):
        assert _matches_any(
            {"vector": "whale drives reserve to floor switching off defense"},
            [{"text": "whale drives the reserve ratio to its floor, disabling the defense"}],
        )

    def test_no_match_different_attack(self):
        assert not _matches_any(
            {"vector": "flash loan oracle price manipulation at dusk"},
            [{"text": "whale drains the reserve through redemptions"}],
        )

    def test_empty_finding_never_matches(self):
        assert not _matches_any({"vector": ""}, [{"text": "anything at all"}])


# ---------------------------------------------------------------------------
# Prompt wiring: prior fixes render (§32)
# ---------------------------------------------------------------------------


class TestPromptWiring:
    def test_prior_fixes_render_in_prompt(self):
        brief = CandidateBrief(
            candidate_id="c1", name="N", category="c", description="d",
            core_mechanism="m",
        )
        payload = ImprovementInput(
            brief=brief,
            current_model={"version": 1},
            attack_findings=[{"agent": "red_team", "vector": "v"}],
            prior_fixes=[
                PriorFix(
                    candidate_id="cand-other",
                    attack="oracle manipulation at composition time",
                    fix_summary="switched to internal TWAP pricing",
                    model_version=2,
                )
            ],
        )
        agent = ImprovementAgent(build_pipeline_provider())
        prompt = agent.build_prompt(payload)
        user = prompt[-1].content
        assert "PRIOR FIXES" in user
        assert "cand-other v2" in user
        assert "internal TWAP pricing" in user
        assert "do not re-patch" in user

    def test_no_prior_fixes_section_when_empty(self):
        brief = CandidateBrief(
            candidate_id="c1", name="N", category="c", description="d",
            core_mechanism="m",
        )
        payload = ImprovementInput(
            brief=brief,
            current_model={"version": 1},
            attack_findings=[{"agent": "red_team", "vector": "v"}],
        )
        agent = ImprovementAgent(build_pipeline_provider())
        assert "PRIOR FIXES" not in agent.build_prompt(payload)[-1].content


# ---------------------------------------------------------------------------
# Service: already-addressed convergence + prior-fix context
# ---------------------------------------------------------------------------


class TestConvergence:
    def test_addressed_attacks_from_graph(self, memory_db):
        cid = "cand-conv1"
        _store_fixed_history(
            memory_db,
            cid,
            "whale drives the reserve to its floor disabling defense",
            "burn-rate taper keeps the defense active under outflow",
        )
        svc = ImprovementService(build_pipeline_provider(), memory_db)
        addressed = svc._addressed_attacks(cid, version=2)
        assert addressed, "the v2 fix claim should mark its attack addressed"
        assert svc._addressed_attacks(cid, version=1) == []

    def test_already_addressed_finding_is_filtered(self, memory_db):
        """A finding matching a v2-addressed attack does not re-patch."""
        from blockchain_rd_lab.improvement.service import _fixable_findings

        cid = "cand-conv2"
        _store_fixed_history(
            memory_db,
            cid,
            "whale pushes the reserve ratio to its floor switching off the corrector",
            "taper on burn rate keeps layer two active under redemption pressure",
        )
        svc = ImprovementService(build_pipeline_provider(), memory_db)
        reports = memory_db.list_redteam_results(candidate_id=cid)
        findings = _fixable_findings(reports)
        assert findings, "the profitable finding must be present"
        addressed = svc._addressed_attacks(cid, version=2)
        fresh = [f for f in findings if not _matches_any(f, addressed)]
        assert fresh == [], "the same attack must be filtered at v2"

    def test_improve_stops_when_all_addressed(self, memory_db):
        """Convergence: nothing left to patch → honest rejected_reason."""
        cid = "cand-conv3"
        _store_fixed_history(
            memory_db,
            cid,
            "whale drives the reserve to the floor and the defense rests",
            "burn-rate taper: layer two stays active under sustained outflow",
        )
        # candidate must be RED_TEAM with v2 as latest
        cand = memory_db.get_candidate(cid)
        assert cand is not None and cand.status is CandidateStatus.RED_TEAM
        svc = ImprovementService(build_pipeline_provider(), memory_db)
        outcome = svc.improve_candidate(cand, offline=True)
        assert not outcome.improved
        assert "already addressed" in (outcome.rejected_reason or "")

    def test_prior_fixes_from_other_candidates_only(self, memory_db):
        """Own history is excluded (handled by addressed filter); others included."""
        _store_fixed_history(
            memory_db,
            "cand-convA",
            "oracle manipulation at composition time",
            "internal TWAP pricing removes the external lever",
        )
        _store_fixed_history(
            memory_db,
            "cand-convB",
            "unrelated attack on this one",
            "unrelated fix",
        )
        svc = ImprovementService(build_pipeline_provider(), memory_db)
        priors = svc._prior_fixes("cand-convA")
        ids = {p.candidate_id for p in priors}
        assert "cand-convA" not in ids
        assert "cand-convB" in ids
        assert all(p.fix_summary for p in priors)
        assert len(priors) <= 5  # bounded context
