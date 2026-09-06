"""§34 improve-stage simulatability gate: patches must RUN before storing.

Found live in round 5 (twice): a patched model can pass every §13
structural check (declarations complete, one '=' per equation,
whitelisted functions) and still be unsimulatable at runtime — a
declared input the battery series never feeds, a dependency cycle, a
missing initial value. RETEST then fails at step 0 and the candidate
goes FAILED — TERMINAL under §11 — on a resubmittable error. The gate
runs one deterministic base-scenario step at improve time: failures
stay at RED_TEAM (improver resubmits), successes store as before.
"""

from __future__ import annotations

import json

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.improvement.service import ImprovementService
from blockchain_rd_lab.schemas import Candidate, CandidateStatus
from blockchain_rd_lab.testing.pipeline_fixtures import build_pipeline_provider


def _candidate(cid: str = "cand-smoke") -> Candidate:
    cand = Candidate(
        id=cid,
        name="Smoke Gate Test",
        category="stablecoins",
        description="A candidate whose improvement must be simulatable.",
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


def _model_json(cid: str, version: int = 1) -> str:
    m = MathModel(
        candidate_id=cid,
        variables=[
            {"name": "S_t", "symbol": "S_t", "role": "state", "units": "u",
             "description": "supply"},
            {"name": "S_t1", "symbol": "S_t1", "role": "state", "units": "u",
             "description": "next supply"},
            {"name": "X_t", "symbol": "X_t", "role": "input", "units": "i",
             "description": "anchor"},
            {"name": "dX_t", "symbol": "dX_t", "role": "input", "units": "i",
             "description": "anchor change"},
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
        rationale="test model rationale",
        version=version,
    )
    return m.model_dump_json()


def _improve_setup(memory_db: LabDatabase, cid: str) -> ImprovementService:
    """Candidate at RED_TEAM with a model, a profitable finding, v2 pending."""
    cand = _candidate(cid)
    memory_db.save_candidate(cand)
    memory_db.save_math_model(cid, _model_json(cid, 1), "v1", version=1)
    # A profitable red-team finding so the improver is invoked.
    from blockchain_rd_lab.redteam import AttackVector, RedTeamReport

    report = RedTeamReport(
        verdict="vulnerable",
        strongest_attack="Whale pumps the supply equation via the anchor.",
        strongest_attack_is_profitable=True,
        attack_vectors=[
            AttackVector(
                vector="anchor pump",
                description="A whale pumps dX_t to inflate supply.",
                attacker="whale",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )
        ],
        what_would_save_it="Damp the anchor response and cap it.",
        evidence_level="INFERENCE",
    )
    memory_db.save_redteam_result(cid, "red_team", report.model_dump_json())
    return ImprovementService(provider=build_pipeline_provider(), database=memory_db)


class TestSmokeGate:
    def test_simulatable_patch_stores(self, memory_db):
        """Happy path: a runnable v2 stores and advances to RETEST."""
        service = _improve_setup(memory_db, "cand-ok")
        out = service.improve_candidate(memory_db.get_candidate("cand-ok"))
        assert out.improved, out.rejected_reason
        c = memory_db.get_candidate("cand-ok")
        assert c.status is CandidateStatus.RETEST
        assert memory_db.latest_model_version("cand-ok") >= 2

    def test_unfed_input_rejected_not_stored(self, memory_db):
        """The round-5 failure: a declared input the battery never feeds.
        The gate must reject BEFORE storing — candidate stays RED_TEAM."""
        from blockchain_rd_lab.formalization import ModelEquation, ModelVariable

        cid = "cand-unfed"
        cand = _candidate(cid)
        memory_db.save_candidate(cand)
        memory_db.save_math_model(cid, _model_json(cid, 1), "v1", version=1)
        from blockchain_rd_lab.redteam import AttackVector, RedTeamReport

        memory_db.save_redteam_result(
            cid, "red_team",
            RedTeamReport(
                verdict="vulnerable",
                strongest_attack="Whale pumps the anchor into supply.",
                strongest_attack_is_profitable=True,
                attack_vectors=[AttackVector(
                    vector="anchor pump",
                    description="Whale pumps dX_t; supply inflates.",
                    attacker="whale", profitable_for_attacker=True,
                    requires_collusion=False, evidence_level="INFERENCE",
                )],
                what_would_save_it="Net out whale flow from the anchor.",
                evidence_level="INFERENCE",
            ).model_dump_json(),
        )

        class UnfedProvider(build_pipeline_provider().__class__):
            """Serves a v2 declaring an input the battery never feeds."""

            def __init__(self):
                super().__init__()
                self._served = False

            def complete_structured(self, messages, *, schema, **kwargs):
                name = getattr(schema, "__name__", "")
                if name == "ImprovementProposal" and not self._served:
                    self._served = True
                    import json as _json
                    base = json.loads(_model_json(cid, 1))
                    base["version"] = 2
                    base["variables"].append(ModelVariable(
                        name="W_t", symbol="W_t", role="input", units="u",
                        description="whale flow the battery never feeds",
                    ).model_dump())
                    base["equations"] = [ModelEquation(
                        name="supply",
                        expression="S_t1 = S_t * (1 + alpha * dX_t) - W_t",
                        description="whale flow subtracts",
                    ).model_dump()]
                    payload = {
                        "candidate_id": cid,
                        "summary": "net whale flow out of supply",
                        "addressed_attacks": [{
                            "agent_name": "red_team",
                            "vector_description": "Whale pumps the anchor.",
                            "fix_strategy": "subtract whale flow",
                            "fixes_attack": True,
                        }],
                        "model": base,
                    }
                    from blockchain_rd_lab.agents.base import parse_json_as
                    return parse_json_as(
                        _json.dumps(payload), schema, source="unfed-test")
                return super().complete_structured(messages, schema=schema, **kwargs)

        service = ImprovementService(provider=UnfedProvider(), database=memory_db)
        out = service.improve_candidate(memory_db.get_candidate(cid))
        assert not out.improved
        assert "not simulatable" in (out.errors[0] if out.errors else "")
        c = memory_db.get_candidate(cid)
        assert c.status is CandidateStatus.RED_TEAM, "gate keeps it resubmittable"
        assert memory_db.latest_model_version(cid) == 1, "v2 not stored"

    def test_dependency_cycle_rejected_at_improve(self, memory_db):
        """A cyclic patch (compile-time §14 error) must fail at the gate,
        not at RETEST's terminal step 0."""
        from blockchain_rd_lab.formalization import ModelEquation

        cid = "cand-cycle"
        cand = _candidate(cid)
        memory_db.save_candidate(cand)
        memory_db.save_math_model(cid, _model_json(cid, 1), "v1", version=1)
        from blockchain_rd_lab.redteam import AttackVector, RedTeamReport

        memory_db.save_redteam_result(
            cid, "red_team",
            RedTeamReport(
                verdict="vulnerable",
                strongest_attack="Whale pumps the anchor into supply.",
                strongest_attack_is_profitable=True,
                attack_vectors=[AttackVector(
                    vector="anchor pump",
                    description="Whale pumps dX_t; supply inflates.",
                    attacker="whale", profitable_for_attacker=True,
                    requires_collusion=False, evidence_level="INFERENCE",
                )],
                what_would_save_it="Break the reflexivity loop.",
                evidence_level="INFERENCE",
            ).model_dump_json(),
        )

        class CycleProvider(build_pipeline_provider().__class__):
            def __init__(self):
                super().__init__()
                self._served = False

            def complete_structured(self, messages, *, schema, **kwargs):
                name = getattr(schema, "__name__", "")
                if name == "ImprovementProposal" and not self._served:
                    self._served = True
                    import json as _json
                    base = json.loads(_model_json(cid, 1))
                    base["version"] = 2
                    base["equations"] = [
                        ModelEquation(
                            name="supply",
                            expression="S_t1 = S_t1 * 0.5 + S_t",
                            description="self-referencing cycle",
                        ).model_dump(),
                    ]
                    payload = {
                        "candidate_id": cid,
                        "summary": "cycle the supply equation",
                        "addressed_attacks": [{
                            "agent_name": "red_team",
                            "vector_description": "Whale pumps the anchor.",
                            "fix_strategy": "cycle",
                            "fixes_attack": True,
                        }],
                        "model": base,
                    }
                    from blockchain_rd_lab.agents.base import parse_json_as
                    return parse_json_as(
                        _json.dumps(payload), schema, source="cycle-test")
                return super().complete_structured(messages, schema=schema, **kwargs)

        service = ImprovementService(provider=CycleProvider(), database=memory_db)
        out = service.improve_candidate(memory_db.get_candidate(cid))
        assert not out.improved
        c = memory_db.get_candidate(cid)
        assert c.status is CandidateStatus.RED_TEAM
        assert memory_db.latest_model_version(cid) == 1
