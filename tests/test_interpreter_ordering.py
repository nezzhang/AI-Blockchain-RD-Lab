"""§14 interpreter ordering: equations evaluate by DEPENDENCY, not declaration.

Found live in round 5: the Tranche-Segmented Stack model declared
`pi_j_t` (computed in equation 8) before `junior_balance` (equation 4,
which reads it) — declaration-order evaluation died at step 0 with
"symbol 'pi_j_t' has no value in this step" even though the model was
semantically sound. The interpreter now topologically sorts equations
(stable: declaration order among independents; cycle = compile-time
SimulationError, not a step-0 runtime miss).
"""

from __future__ import annotations

import pytest

from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.simulation.interpreter import SimulationError


def _model(equations: list[tuple[str, str, str]]) -> MathModel:
    return MathModel(
        candidate_id="cand-order",
        variables=[
            {"name": "a_t", "symbol": "a_t", "role": "state", "units": "u",
             "description": "state a"},
            {"name": "b_t", "symbol": "b_t", "role": "state", "units": "u",
             "description": "state b"},
            {"name": "a_t1", "symbol": "a_t1", "role": "state", "units": "u",
             "description": "next-step a"},
            {"name": "b_t1", "symbol": "b_t1", "role": "state", "units": "u",
             "description": "next-step b"},
            {"name": "x_t", "symbol": "x_t", "role": "input", "units": "u",
             "description": "input"},
        ],
        parameters=[
            {"name": "k", "symbol": "k", "description": "coupling",
             "min_value": 0.0, "max_value": 1.0, "default": 0.5},
        ],
        equations=[
            {"name": n, "expression": e, "description": d}
            for n, e, d in equations
        ],
        assumptions=[{"statement": "test assumption here", "critical": False}],
        constraints=[],
        open_questions=["ordering?"],
        rationale="test model for ordering",
    )


class TestDependencyOrder:
    def test_out_of_order_equations_evaluate(self):
        """The round-5 failure mode: consumer declared BEFORE producer."""
        m = _model([
            ("consumer", "b_t = a_t1 * k", "reads a_t1 declared later"),
            ("producer", "a_t1 = 3", "computes a_t1"),
        ])
        res = _run(m)
        assert res["a_t1"] == 3.0
        assert res["b_t"] == 1.5

    def test_declared_order_still_works(self):
        m = _model([
            ("producer", "a_t1 = 3", "computes first"),
            ("consumer", "b_t = a_t1 * k", "reads a_t1"),
        ])
        res = _run(m)
        assert res["b_t"] == 1.5

    def test_chain_of_dependencies(self):
        """A→B→C chain declared fully reversed."""
        m = _model([
            ("c", "b_t = a_t1 * k", "reads a_t1"),
            ("a", "a_t1 = x_t * 2", "reads input"),
        ])
        res = _run(m, extra={"x_t": 1.0})
        assert res["a_t1"] == 2.0
        assert res["b_t"] == 1.0

    def test_independent_order_preserved(self):
        """Stable sort: independents keep declaration order (both write
        distinct LHS; check via multi-assign semantics — last-in-declaration
        wins on same LHS)."""
        m = _model([
            ("first", "a_t1 = 1", "first writer"),
            ("second", "a_t1 = 2", "second writer wins"),
        ])
        res = _run(m)
        assert res["a_t1"] == 2.0, "declaration-order overwrite semantics kept"

    def test_cycle_rejected_at_compile(self):
        from blockchain_rd_lab.simulation.interpreter import EquationInterpreter

        m = _model([
            ("a", "a_t1 = b_t1 * k", "reads b_t1"),
            ("b", "b_t1 = a_t1 * k", "reads a_t1 — cycle"),
        ])
        with pytest.raises(SimulationError, match="dependency cycle"):
            EquationInterpreter(m)

    def test_self_reference_is_a_cycle(self):
        from blockchain_rd_lab.simulation.interpreter import EquationInterpreter

        m = _model([
            ("self", "a_t1 = a_t1 * 0.5", "reads its own LHS"),
        ])
        with pytest.raises(SimulationError, match="dependency cycle"):
            EquationInterpreter(m)


def _run(m: MathModel, extra: dict | None = None) -> dict[str, float]:
    from blockchain_rd_lab.simulation.interpreter import EquationInterpreter

    interp = EquationInterpreter(m)
    symbols = {"a_t": 0.0, "b_t": 0.0, "k": 0.5, **(extra or {})}
    return interp.evaluate(symbols)
