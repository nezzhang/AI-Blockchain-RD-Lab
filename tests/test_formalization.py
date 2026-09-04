"""Phase 3 formalization tests: model schema, integrity checks, service, CLI."""

from __future__ import annotations

import json

import pydantic
import pytest

from blockchain_rd_lab.agents import LLMError, MockLLMProvider
from blockchain_rd_lab.formalization import (
    MathModel,
    ModelEquation,
    ModelParameter,
    model_from_dict,
)
from blockchain_rd_lab.formalization.agents import (
    MechanismDesignerAgent,
    build_math_model_fixture,
)
from blockchain_rd_lab.formalization.service import FormalizationService
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


def make_candidate(**overrides) -> Candidate:
    base = dict(
        name="Carbon-Weighted Gas Fees",
        category="energy",
        description="Gas priced by verified carbon intensity of validator energy mix.",
        core_mechanism="GasPrice = base * (1 + beta * carbon_intensity_t).",
        problem="Blockchains ignore energy externalities",
    )
    base.update(overrides)
    return Candidate(**base)


VALID_MODEL = dict(
    candidate_id="cand-x",
    variables=[
        {
            "name": "supply",
            "symbol": "S_t",
            "role": "state",
            "units": "tokens",
            "description": "Supply at step t.",
        },
        {
            "name": "supply_next",
            "symbol": "S_t1",
            "role": "output",
            "units": "tokens",
            "description": "Supply at step t+1.",
        },
    ],
    parameters=[
        {
            "name": "coupling",
            "symbol": "alpha",
            "description": "Coupling strength.",
            "min_value": 0.0,
            "max_value": 2.0,
            "default": 1.0,
        },
    ],
    equations=[
        {
            "name": "update",
            "expression": "S_t1 = S_t * (1 + alpha * 0.01)",
            "description": "Grow supply.",
        },
    ],
    assumptions=[{"statement": "Reports arrive on schedule.", "critical": True}],
    constraints=[
        {"statement": "Supply stays positive.", "kind": "invariant"},
        {"statement": "Oracle stall freezes supply.", "kind": "failure_condition"},
    ],
    open_questions=["What alpha keeps volatility in band?"],
    rationale="A faithful minimal formalization of the mechanism.",
)


class TestModelEquation:
    def test_valid(self):
        eq = ModelEquation(name="u", expression="S_t1 = S_t * (1 + g_t)")
        assert eq.expression == "S_t1 = S_t * (1 + g_t)"

    def test_rejects_unicode_math(self):
        with pytest.raises(pydantic.ValidationError):
            ModelEquation(name="u", expression="S_t1 = S_t × 1.5")  # noqa: RUF001

    def test_rejects_double_equals(self):
        with pytest.raises(pydantic.ValidationError):
            ModelEquation(name="u", expression="S_t1 == 5")

    def test_rejects_two_assignments(self):
        with pytest.raises(pydantic.ValidationError):
            ModelEquation(name="u", expression="a = b = c")

    def test_rejects_unbalanced_parens(self):
        with pytest.raises(pydantic.ValidationError):
            ModelEquation(name="u", expression="f(x = g(x)")
        with pytest.raises(pydantic.ValidationError):
            ModelEquation(name="u", expression="f(x) = g(x))")


class TestModelParameter:
    def test_range_and_default(self):
        p = ModelParameter(
            name="alpha", symbol="a", description="coupling", min_value=0.0,
            max_value=2.0, default=1.0,
        )
        assert p.min_value < p.max_value

    def test_default_outside_range_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            ModelParameter(
                name="alpha", symbol="a", description="coupling",
                min_value=0.0, max_value=1.0, default=1.5,
            )

    def test_inverted_range_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            ModelParameter(
                name="alpha", symbol="a", description="coupling",
                min_value=2.0, max_value=1.0, default=1.5,
            )


class TestMathModelIntegrity:
    def test_valid_model(self):
        m = MathModel.model_validate(VALID_MODEL)
        assert m.undeclared_symbols() == set()
        assert m.unused_symbols() == set()

    def test_undeclared_symbol_rejected(self):
        bad = json.loads(json.dumps(VALID_MODEL))
        bad["equations"][0]["expression"] = "S_t1 = S_t * (1 + beta * 0.01)"
        with pytest.raises(pydantic.ValidationError, match="undeclared"):
            MathModel.model_validate(bad)

    def test_function_whitelist_not_undeclared(self):
        m = MathModel.model_validate(VALID_MODEL)
        m = m.model_copy(update={
            "equations": [
                ModelEquation(
                    name="g",
                    expression="g_t = clip(alpha, 0, 1)",
                    description="clip",
                )
            ]
        })
        assert "clip" not in m.undeclared_symbols()

    def test_open_questions_required(self):
        bad = json.loads(json.dumps(VALID_MODEL))
        bad["open_questions"] = []
        with pytest.raises(pydantic.ValidationError):
            MathModel.model_validate(bad)

    def test_variables_required_nonempty(self):
        bad = json.loads(json.dumps(VALID_MODEL))
        bad["variables"] = []
        with pytest.raises(pydantic.ValidationError):
            MathModel.model_validate(bad)

    def test_fixture_model_passes(self):
        cand = make_candidate()
        brief = CandidateBrief.from_candidate(cand)
        m = model_from_dict(build_math_model_fixture(brief))
        assert m.undeclared_symbols() == set()
        assert len(m.open_questions) >= 3  # §13 checklist


class TestMechanismDesignerAgent:
    def test_execute_via_mock(self, memory_db):
        cand = make_candidate()
        brief = CandidateBrief.from_candidate(cand)
        p = MockLLMProvider()
        p.queue_response(json.dumps(build_math_model_fixture(brief)))
        agent = MechanismDesignerAgent(p, database=memory_db)
        out, record = agent.execute(brief)
        assert isinstance(out, MathModel)
        assert record.status == "success"

    def test_agent_failure_isolated(self, memory_db):
        cand = make_candidate()
        brief = CandidateBrief.from_candidate(cand)
        p = MockLLMProvider()
        p.queue_response("<<<garbage>>>")
        agent = MechanismDesignerAgent(p, database=memory_db)
        with pytest.raises(LLMError):
            agent.execute(brief)

    def test_wrong_payload_type(self):
        agent = MechanismDesignerAgent(MockLLMProvider())
        with pytest.raises(TypeError):
            agent.build_prompt("not-a-brief")

    def test_prompt_mentions_never_assume(self):
        cand = make_candidate()
        brief = CandidateBrief.from_candidate(cand)
        msgs = MechanismDesignerAgent(MockLLMProvider()).build_prompt(brief)
        assert "NEVER assume the first equation is correct" in msgs[0].content
        assert "open_questions" in msgs[0].content


class TestFormalizationService:
    def _service(self, memory_db) -> FormalizationService:
        return FormalizationService(MockLLMProvider(), memory_db)

    def test_formalize_candidate_happy_path(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        # Move to PRIOR_ART_CHECKED first (§11)
        cand.transition(CandidateStatus.RESEARCHING)
        cand.transition(CandidateStatus.PRIOR_ART_CHECKED)
        memory_db.save_candidate(cand)

        brief = CandidateBrief.from_candidate(cand)
        p = MockLLMProvider()
        p.queue_response(json.dumps(build_math_model_fixture(brief)))
        service = FormalizationService(p, memory_db)
        result = service.formalize_candidate(cand)

        assert result.formalized is True
        assert result.model is not None
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.FORMALIZED
        assert memory_db.latest_model_version(cand.id) == 1
        dump = memory_db.get_latest_math_model(cand.id)
        assert dump is not None
        model = model_from_dict(json.loads(dump))
        assert model.candidate_id == cand.id

    def test_versions_increment(self, memory_db):
        cand = make_candidate()
        cand.transition(CandidateStatus.RESEARCHING)
        cand.transition(CandidateStatus.PRIOR_ART_CHECKED)
        memory_db.save_candidate(cand)
        service = self._service(memory_db)

        r1 = service._formalize_one_fixture(cand)
        r2 = service._formalize_one_fixture(cand)
        assert r1.formalized and r2.formalized
        assert memory_db.latest_model_version(cand.id) == 2

    def test_formalize_all_failure_isolated(self, memory_db):
        c1 = make_candidate()
        c1.transition(CandidateStatus.RESEARCHING)
        c1.transition(CandidateStatus.PRIOR_ART_CHECKED)
        memory_db.save_candidate(c1)
        c2 = make_candidate(name="Second")
        c2.transition(CandidateStatus.RESEARCHING)
        c2.transition(CandidateStatus.PRIOR_ART_CHECKED)
        memory_db.save_candidate(c2)

        # c1's designer call fails; c2 succeeds.
        p = MockLLMProvider()
        p.queue_response("<<<garbage>>>")
        brief2 = CandidateBrief.from_candidate(c2)
        p.queue_response(json.dumps(build_math_model_fixture(brief2)))

        service = FormalizationService(p, memory_db)
        summary = service.formalize_all()
        assert summary.attempted == 2
        assert summary.formalized == 1
        assert summary.failed == 1
        assert c2.id in summary.model_versions
        assert c1.id in summary.errors

        stored1 = memory_db.get_candidate(c1.id)
        assert stored1 is not None
        assert stored1.status is CandidateStatus.PRIOR_ART_CHECKED  # left in place

    def test_fixture_path_offline(self, memory_db, tmp_path):
        cand = make_candidate()
        cand.transition(CandidateStatus.RESEARCHING)
        cand.transition(CandidateStatus.PRIOR_ART_CHECKED)
        memory_db.save_candidate(cand)
        service = self._service(memory_db)
        summary = service.formalize_all_fixtures(artifacts_dir=tmp_path / "art")
        assert summary.formalized == 1
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.FORMALIZED
        assert (tmp_path / "art" / "formalization-latest.json").is_file()


class TestDatabaseModels:
    def test_save_and_list(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        brief = CandidateBrief.from_candidate(cand)
        model = model_from_dict(build_math_model_fixture(brief))
        dump = json.dumps(model.model_dump(mode="json"))
        memory_db.save_math_model(cand.id, dump, model.rationale, version=1)
        memory_db.save_math_model(cand.id, dump, model.rationale, version=2)
        assert memory_db.latest_model_version(cand.id) == 2
        rows = memory_db.list_math_models(cand.id)
        assert len(rows) == 2
        assert memory_db.get_latest_math_model(cand.id) is not None

    def test_latest_version_none_if_absent(self, memory_db):
        assert memory_db.latest_model_version("cand-nothere") == 0
        assert memory_db.get_latest_math_model("cand-nothere") is None
