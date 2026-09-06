"""§14/§15 simulation correctness: degenerate-run detection + state feedback.

The adversarial pattern battery (§20 residual bounding) exposed two
defects the §15 suite had been grading models through:

1. BROKEN STATE FEEDBACK — when a model declares BOTH S_t and S_t1 as
   states (the §13 convention bridge-authored models use), the roll
   step wrote the computed value to S_t1 but never back into S_t, so
   every model ran flat at its initial state. The battery "passed" a
   decade of frozen trajectories.

2. VACUOUS EVIDENCE — a model whose clip bounds are incompatible with
   the battery's input scale (X_t ~1000 read as a shock intensity ~O(1))
   saturates in step 0: every scenario produces the SAME pinned
   trajectory. "13/13 clean" over identical runs is not evidence.

These tests pin both behaviors: the feedback loop must close for
stepped-state models, and degenerate runs must be flagged so the §15
verdict cannot count them as clean.
"""

from __future__ import annotations

from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.simulation import (
    AnchorSeriesGenerator,
    MechanismSimulation,
    ScenarioBattery,
    ScenarioKind,
    scenario_config,
)
from blockchain_rd_lab.simulation.adversarial import (
    AttackPattern,
    AttackPatternBattery,
    PatternSpec,
)


def _vars():
    return [
        {"name": "supply", "symbol": "S_t", "role": "state", "units": "u",
         "description": "supply"},
        {"name": "supply_next", "symbol": "S_t1", "role": "state", "units": "u",
         "description": "next supply"},
        {"name": "anchor", "symbol": "X_t", "role": "input", "units": "i",
         "description": "anchor level"},
        {"name": "anchor_delta", "symbol": "dX_t", "role": "input", "units": "i",
         "description": "anchor change"},
    ]


def _params():
    return [
        {"name": "coupling", "symbol": "alpha", "description": "coupling",
         "min_value": 0.0, "max_value": 1.0, "default": 0.5},
    ]


def _model(equations, version=1) -> MathModel:
    return MathModel(
        candidate_id="cand-simtest",
        variables=_vars(),
        parameters=_params(),
        equations=equations,
        assumptions=[{"statement": "observable anchor", "critical": False}],
        constraints=[],
        open_questions=["is alpha right?"],
        rationale="test model",
        version=version,
    )


def _series(steps=6):
    cfg = scenario_config(ScenarioKind.BASE, steps=steps)
    return AnchorSeriesGenerator(cfg).generate()


class TestStateFeedback:
    """S_t1-as-state models must actually feed back (§14 defect)."""

    def test_stepped_state_feeds_back_into_base(self):
        """G_t1 declared as a state and written by an equation must roll
        into G_t — the run must MOVE, not freeze at 1000."""
        m = _model([
            {"name": "rule", "expression": "S_t1 = S_t * (1 + alpha * dX_t / X_t)",
             "description": "supply follows anchor"},
        ])
        run = MechanismSimulation(m).run(_series())
        path = [row["S_t"] for row in run.history]
        assert any(abs(x - path[0]) > 1e-9 for x in path), (
            "the state never left its initial value — feedback loop broken"
        )

    def test_run_moves_under_shocks(self):
        """A whale-attack series must move the state differently from base."""
        m = _model([
            {"name": "rule", "expression": "S_t1 = S_t * (1 + alpha * dX_t / X_t)",
             "description": "supply follows anchor"},
        ])
        base = MechanismSimulation(m).run(_series(30))
        whale_cfg = scenario_config(ScenarioKind.WHALE_ATTACK, steps=30)
        whale = AnchorSeriesGenerator(whale_cfg).generate()
        attacked = MechanismSimulation(m).run(whale)
        assert base.final_state["S_t"] != attacked.final_state["S_t"]


class TestDegenerateDetection:
    """Pinned/frozen trajectories are flagged, not graded clean."""

    def test_saturated_model_flagged_degenerate(self):
        """A model whose clip bounds can't hold the battery's scale pins
        every state — the run must be flagged degenerate (§2: vacuous
        evidence must not count as clean)."""
        # X_t (~1000) read as a shock intensity into a 0..3 clip
        m = _model([
            {"name": "rule",
             "expression": "S_t1 = clip(S_t * (1 + alpha * X_t), 0, 3)",
             "description": "saturating rule"},
        ])
        run = MechanismSimulation(m).run(_series())
        assert run.degenerate, "saturated trajectory must be flagged"

    def test_healthy_model_not_flagged(self):
        m = _model([
            {"name": "rule", "expression": "S_t1 = S_t * (1 + alpha * dX_t / X_t)",
             "description": "supply follows anchor"},
        ])
        run = MechanismSimulation(m).run(_series())
        assert not run.degenerate

    def test_frozen_state_flagged(self):
        """A rule that never moves the state is equally evidence-free."""
        m = _model([
            {"name": "rule", "expression": "S_t1 = S_t", "description": "identity"},
        ])
        run = MechanismSimulation(m).run(_series())
        assert run.degenerate

    def test_battery_flags_vacuous_model(self):
        """The §15 battery surfaces degeneracy per scenario."""
        m = _model([
            {"name": "rule",
             "expression": "S_t1 = clip(S_t * (1 + alpha * X_t), 0, 3)",
             "description": "saturating rule"},
        ])
        runs = ScenarioBattery(MechanismSimulation(m), steps=30).run()
        assert all(r.degenerate for r in runs.values())


class TestAdversarialPatternBattery:
    """§20 residual bounding: named attack patterns vs matched base."""

    def test_oscillation_pattern_craft(self):
        """The oscillation series alternates shock / quiet steps."""
        m = _model([
            {"name": "rule", "expression": "S_t1 = S_t * (1 + alpha * dX_t / X_t)",
             "description": "supply follows anchor"},
        ])
        battery = AttackPatternBattery(m)
        rows = battery.craft_series(PatternSpec(kind=AttackPattern.VOL_OSCILLATION))
        shocks = [r for r in rows if r["dX_t"] != 0.0]
        quiets = [r for r in rows if r["dX_t"] == 0.0]
        assert shocks and quiets, "oscillation must alternate"

    def test_bound_reports_edge(self):
        """A healthy model under oscillation reports a real bound."""
        m = _model([
            {"name": "rule", "expression": "S_t1 = S_t * (1 + alpha * dX_t / X_t)",
             "description": "supply follows anchor"},
        ])
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.VOL_OSCILLATION, steps=40)
        )
        assert not bound.vacuous
        assert bound.failures == []

    def test_vacuous_bound_is_none_not_zero(self):
        """A saturated model reports headline=None (vacuous), NOT 0.0 —
        'the attack is bounded by zero' would be a false security claim
        about a model that exercises no dynamics (§12)."""
        m = _model([
            {"name": "rule",
             "expression": "S_t1 = clip(S_t * (1 + alpha * X_t), 0, 3)",
             "description": "saturating rule"},
        ])
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.VOL_OSCILLATION, steps=40)
        )
        assert bound.vacuous
        assert bound.headline is None, (
            "vacuous runs must not report a numeric bound"
        )

    def test_all_patterns_deterministic(self):
        """Same model + spec → byte-identical bounds (§21)."""
        m = _model([
            {"name": "rule", "expression": "S_t1 = S_t * (1 + alpha * dX_t / X_t)",
             "description": "supply follows anchor"},
        ])
        b1 = AttackPatternBattery(m).run_all(steps=30)
        b2 = AttackPatternBattery(m).run_all(steps=30)
        assert [x.model_dump() for x in b1] == [x.model_dump() for x in b2]
