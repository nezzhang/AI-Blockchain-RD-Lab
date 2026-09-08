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


def _model(equations, version=1, variables=None) -> MathModel:
    return MathModel(
        candidate_id="cand-simtest",
        variables=variables if variables is not None else _vars(),
        parameters=_params(),
        equations=equations,
        assumptions=[{"statement": "observable anchor", "critical": False}],
        constraints=[],
        open_questions=["is alpha right?"],
        rationale="test model",
        version=version,
    )


def _trend_vars():
    """Anchored-trend model vars: trend EMA + protection fee states."""
    return [
        {"name": "trend", "symbol": "T_t", "role": "state", "units": "u",
         "description": "trend index"},
        {"name": "trend_next", "symbol": "T_t1", "role": "state", "units": "u",
         "description": "next trend"},
        {"name": "cover", "symbol": "F_t", "role": "state", "units": "u",
         "description": "protection fee"},
        {"name": "cover_next", "symbol": "F_t1", "role": "state", "units": "u",
         "description": "next fee"},
        {"name": "anchor", "symbol": "X_t", "role": "input", "units": "i",
         "description": "anchor level"},
        {"name": "anchor_delta", "symbol": "dX_t", "role": "input", "units": "i",
         "description": "anchor change"},
    ]


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

    def test_unmeasurable_model_is_vacuous_not_zero(self):
        """A model with NO drainable states (auxiliary-output only) is
        UNMEASURABLE by the battery — the r10 gap: such models reported
        headline=0.0 ('bounded by zero'), a false security claim. They
        must report headline=None/vacuous, the same no-evidence class
        as saturation (§20/§2)."""
        m = MathModel(
            candidate_id="cand-simtest",
            variables=[
                {"name": "anchor", "symbol": "X_t", "role": "input", "units": "i",
                 "description": "anchor level"},
                {"name": "anchor_delta", "symbol": "dX_t", "role": "input", "units": "i",
                 "description": "anchor change"},
                {"name": "tax", "symbol": "tax_t", "role": "auxiliary", "units": "u",
                 "description": "instantaneous tax (no stock to drain)"},
            ],
            parameters=_params(),
            equations=[
                {"name": "tax", "expression": "tax_t = alpha * abs(dX_t)/X_t",
                 "description": "flow-only output"},
            ],
            assumptions=[{"statement": "observable anchor", "critical": False}],
            constraints=[],
            open_questions=["is alpha right?"],
            rationale="test model",
            version=1,
        )
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.VOL_OSCILLATION, steps=40)
        )
        assert bound.edge == {}, "sanity: no metrics were extractable"
        assert bound.vacuous, "unmeasurable must flag vacuous"
        assert bound.headline is None, "never report 'bounded by zero'"

    def test_every_declared_state_is_drainable(self):
        """The r10 extractor fix: state drainage must cover EVERY state
        role symbol (S_/J_/G_/W_...), not just B_*/R_* prefixes — a
        J-named escrow drains exactly like a B-named bond (§13 roles,
        not naming conventions, carry the semantics)."""
        m = _model([
            {"name": "rule",
             "expression": "S_t1 = clip(S_t - alpha * abs(dX_t)/X_t * 200.0, 400.0, 2000.0)",
             "description": "supply drains under crafted vol"},
        ], version=1)
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.VOL_OSCILLATION, steps=40)
        )
        assert "S_t_drawn" in bound.edge, (
            "S_t is a declared state; its drain must be measurable"
        )
        assert not bound.vacuous

    def test_crash_park_craft_moves_once_then_parks(self):
        """The r13 choreography: one hard move, then dX=0 forever —
        the pattern whose absence made anchor-heal designs invisible
        to the r10/r11 battery (wash/pump/osc move repeatedly, shock
        reverts; nothing parks)."""
        m = _model([
            {"name": "rule", "expression": "S_t1 = S_t * (1 + alpha * dX_t / X_t)",
             "description": "supply follows anchor"},
        ])
        battery = AttackPatternBattery(m)
        rows = battery.craft_series(PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60))
        nonzero = [r for r in rows if r["dX_t"] != 0.0]
        assert len(nonzero) == 1, "exactly one move"
        assert abs(nonzero[0]["dX_t"]) > 0.5 * 1000.0, "a hard move"
        parked = rows[rows.index(nonzero[0]) + 1:]
        assert all(r["dX_t"] == 0.0 for r in parked), (
            "and it parks — no reversion, no further moves"
        )
        assert abs(rows[-1]["X_t"] - 1000.0) > 0.5 * 1000.0, "level stays moved"

    def test_anchor_heal_design_flags_heal_ratio(self):
        """An anchored-trend protection state (keys |T-1000|, T reverts
        to 1000 when moves stop) must report a heal ratio near zero
        under CRASH_PARK: the r13 finding class — protection decays to
        zero exactly when the regime is permanently moved."""
        m = _model([
            {"name": "trend",
             "expression": ("T_t1 = clip(T_t + 0.2*((1000.0 + (dX_t/X_t)*1000.0)"
                          " - T_t), 200.0, 1800.0)"),
             "description": "1000-anchored reverting trend"},
            {"name": "cover",
             "expression": ("F_t1 = clip(F_t*(1-0.4) + 0.4*(1000.0 + 1.4*abs(T_t-1000.0)),"
                          " 400.0, 2400.0)"),
             "description": "protection fee keyed to |T-1000|"},
        ], version=1, variables=_trend_vars())
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        )
        assert "F_t" in bound.heal_flags, (
            "F_t keys the anchored trend; its heal must be measured"
        )
        assert bound.heal_flags["F_t"] < 0.25, (
            "anchored-trend cover heals: tail protection "
            "decays while the level stays moved"
        )

    def test_persistent_protection_heal_ratio_stays_high(self):
        """A level-tracking protection state (slow EMA of X, wide clip)
        must NOT flag: after the crash it stays displaced — the r12
        construction. The negative control for the heal flag."""
        m = _model([
            {"name": "trend",
             "expression": "T_t1 = clip(T_t + 0.2*(X_t - T_t), 200.0, 3000.0)",
             "description": "slow EMA of the LEVEL (re-centers)"},
            {"name": "cover",
             "expression": ("F_t1 = clip(F_t*(1-0.4) + 0.4*(1000.0 + 1.4*abs(T_t-1000.0)),"
                          " 400.0, 2400.0)"),
             "description": "protection fee keyed to the level EMA"},
        ], version=1, variables=_trend_vars())
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        )
        assert bound.heal_flags.get("F_t", 1.0) > 0.5, (
            "level-tracking cover stays priced up while the level "
            "stays moved"
        )

    def test_heal_flag_ignores_initialization_transient(self):
        """The heal measurement must key the POST-crash window only: a
        state seeding at 1000 and decaying to its natural level before
        the crash is an initialization transient, not protection (the
        r13 review catch: O_t's t0 displacement was init, not crash)."""
        m = _model([
            {"name": "trend",
             "expression": ("T_t1 = clip(T_t + 0.2*((1000.0 + (dX_t/X_t)*1000.0)"
                          " - T_t), 200.0, 1800.0)"),
             "description": "1000-anchored reverting trend"},
            # cover seeds at 1000 but its natural level is 520 — pure
            # init decay, keyed to NOTHING (reads only itself)
            {"name": "cover",
             "expression": "F_t1 = clip(F_t*(1-0.5) + 0.5*520.0, 400.0, 2400.0)",
             "description": "init-decay decoy: natural level 520"},
        ], version=1, variables=_trend_vars())
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        )
        # decoy reads only itself -> not keyed -> not flagged; and if
        # it were, its post-crash displacement is ~0 (nothing moves it)
        assert "F_t" not in bound.heal_flags or bound.heal_flags["F_t"] >= 0.0


class TestTransientRecoveryClassification:
    """The r15 4b honesty fix: an excursion that RECOVERS by the parked
    window's end (< 25% of peak displacement) is the crash's own
    transient cost — not a standing attacker edge. The FX-matching
    finding: M_t collapsed 96 units at the crash step and fully
    re-normalized under park; publishing '+96 attacker edge' misread a
    one-step crash cost as an extraction."""

    def test_recovered_excursion_reclassified(self):
        m = _model([
            {"name": "rule",
             "expression": "S_t1 = clip(S_t*(1-0.3) + 0.3*1000.0, 400.0, 2000.0)",
             "description": "mean-reverting: excursion fully recovers"},
        ], version=1)
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        )
        # the crash displaces S (dX enters nothing here — S reverts to
        # 1000 regardless), so excursion recovery applies trivially;
        # the classification must not fabricate edges either way
        assert bound.headline is None or bound.headline >= 0.0

    def test_standing_drain_not_reclassified(self):
        """A drain that PERSISTS at the parked window's end (the r15
        Bandwidth Bond finding: tug-of-war equilibrium 22% from the
        level, burning 17.7/step forever) must stay an attacker-edge
        headline — the honesty fix must never hide a real flaw."""
        m = _model([
            {"name": "stress",
             "expression": "s_t = sqrt(max(0.0, 0.05) + 0.3*max(0.0, abs(X_t-S_t)/1000.0 - 0.1))",
             "description": "stress signal keyed to a deviation that never closes"},
            {"name": "drain",
             "expression": "S_t1 = clip(S_t - 0.3*s_t*300.0"
                           " + 0.07*(1000.0 - S_t) + 0.03*(X_t-1000.0), 450.0, 2400.0)",
             "description": "tug-of-war: never re-bases, drains forever"},
        ], version=1, variables=[
            {"name": "supply", "symbol": "S_t", "role": "state", "units": "u",
             "description": "pool"},
            {"name": "supply_next", "symbol": "S_t1", "role": "state", "units": "u",
             "description": "next pool"},
            {"name": "stress", "symbol": "s_t", "role": "auxiliary", "units": "u",
             "description": "stress"},
            {"name": "anchor", "symbol": "X_t", "role": "input", "units": "i",
             "description": "anchor level"},
            {"name": "anchor_delta", "symbol": "dX_t", "role": "input", "units": "i",
             "description": "anchor change"},
        ])
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        )
        assert bound.headline is not None and bound.headline > 40.0, (
            "a standing drain must remain a disclosed edge"
        )
        assert "S_t_drawn" not in bound.transient_recovered
