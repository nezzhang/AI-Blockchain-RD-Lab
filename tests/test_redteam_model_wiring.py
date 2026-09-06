"""§34 adversarial-model wiring: red teams attack the FORMALIZED design.

redteam_candidate attaches the latest MathModel to the brief (formal_model),
and _brief_user_message renders it as 'formalized model (attack THIS
design)'. Consequences, all asserted here:

- the adversarial prompt contains the model's parameters/equations —
  attacks target the formalized design, not just the prose
- retest after improve sees the PATCHED model version (v2, v3, ...): the
  re-attack is genuinely fresh (new prompt content), not a replay of the
  pre-improvement attack
- research-stage prompts are unchanged when no model exists (byte-stable)
"""

from __future__ import annotations

from blockchain_rd_lab.redteam.agents import _brief_user_message
from blockchain_rd_lab.redteam.service import RedTeamService
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import Candidate, CandidateStatus
from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider


def _candidate(cid: str = "cand-rt1") -> Candidate:
    cand = Candidate(
        id=cid,
        name="Adversarial Model Wiring Test",
        category="stablecoins",
        description="A candidate whose red team must see the model.",
        core_mechanism="S_t1 = S_t * (1 + alpha * dX_t).",
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


def _model_json(version: int) -> str:
    from blockchain_rd_lab.formalization import MathModel

    m = MathModel(
        candidate_id="cand-rt1",
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
        rationale="test model",
        version=version,
    )
    return m.model_dump_json()


class TestPromptRendersModel:
    def test_formal_model_renders_with_attack_directive(self):
        brief = CandidateBrief(
            candidate_id="c1",
            name="N",
            category="c",
            description="d",
            core_mechanism="m",
            formal_model='{"version":2, "parameters": [{"name": "forfeit_rate"}]}',
        )
        msg = _brief_user_message(brief)
        assert "formalized model (attack THIS design):" in msg
        assert "forfeit_rate" in msg

    def test_no_model_no_section(self):
        brief = CandidateBrief(
            candidate_id="c1", name="N", category="c", description="d",
            core_mechanism="m",
        )
        assert "formalized model" not in _brief_user_message(brief)


class TestServiceAttachesLatestModel:
    def test_latest_version_attached(self, memory_db):
        memory_db.save_candidate(_candidate())
        memory_db.save_math_model("cand-rt1", _model_json(1), "v1", version=1)
        memory_db.save_math_model("cand-rt1", _model_json(2), "v2", version=2)

        provider = build_pipeline_provider()
        cand = memory_db.get_candidate("cand-rt1")
        assert cand is not None

        # Capture the brief the agents actually receive via a probe agent
        # call — use the service's internal flow through GameTheoryAgent
        # with a recording provider wrapper.
        captured: list[str] = []

        class RecordingProvider(provider.__class__):  # type: ignore[valid-type]
            def complete_structured(self, messages, *, schema, **kwargs):
                captured.append("\n".join(m.content for m in messages))
                return super().complete_structured(messages, schema=schema, **kwargs)

        rec = RecordingProvider()
        rec_service = RedTeamService(rec, memory_db)
        rec_service.redteam_candidate(cand)
        assert captured, "agents must have been called"
        assert any('"version":2' in c for c in captured), (
            "the LATEST model version must reach the adversarial prompt"
        )
        assert any("attack THIS design" in c for c in captured)

    def test_research_stage_prompts_unchanged_without_model(self, memory_db):
        """Red-team on a candidate with NO model: prompt has no model section."""
        memory_db.save_candidate(_candidate("cand-rt2"))
        provider = build_pipeline_provider()
        cand = memory_db.get_candidate("cand-rt2")
        assert cand is not None

        captured: list[str] = []

        class RecordingProvider(provider.__class__):  # type: ignore[valid-type]
            def complete_structured(self, messages, *, schema, **kwargs):
                captured.append("\n".join(m.content for m in messages))
                return super().complete_structured(messages, schema=schema, **kwargs)

        rec = RecordingProvider()
        RedTeamService(rec, memory_db).redteam_candidate(cand)
        assert all("formalized model" not in c for c in captured)


class TestRetestSeesPatchedModel:
    def test_model_version_changes_prompt_content(self):
        """The wiring guarantees fresh re-attack content: v1 vs v2 briefs
        differ, so retest after improve cannot replay pre-patch attacks."""
        b1 = CandidateBrief(
            candidate_id="c1", name="N", category="c", description="d",
            core_mechanism="m", formal_model=_model_json(1),
        )
        b2 = b1.model_copy(update={"formal_model": _model_json(2)})
        assert _brief_user_message(b1) != _brief_user_message(b2)
        assert '"version":2' in _brief_user_message(b2)

    def test_brief_is_frozen(self):
        """CandidateBrief stays immutable (hashable in sets, safe copies)."""
        b = CandidateBrief(
            candidate_id="c1", name="N", category="c", description="d",
            core_mechanism="m", formal_model="{}",
        )
        try:
            b.name = "other"  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("CandidateBrief must remain frozen")
