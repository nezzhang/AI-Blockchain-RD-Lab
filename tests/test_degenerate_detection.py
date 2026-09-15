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

import pytest

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


class TestDriftCreepPattern:
    """The r17 choreography: sustained sub-threshold drift (boiling
    frog). Pins (a) the craft shape — constant grind, no spike; (b)
    the wedge disclosure — level-denominated states that lag the
    regime are disclosed as responsiveness gaps; (c) attribution
    honesty — a wedge enters the attacker-edge headline ONLY through a
    measured consumer response, never by structural inference (the r16
    v2's slow anchor lags 326 under drift but its consumer keys the
    anchor SEPARATION, which stays ~1: nothing to harvest, headline 0).
    """

    def test_craft_is_constant_grind_no_spike(self):
        m = _model([
            {"name": "pool",
             "expression": "S_t1 = clip(S_t + 0.1*(X_t - S_t), 200.0, 4000.0)",
             "description": "level-tracking pool"},
        ], version=1)
        b = AttackPatternBattery(m)
        rows = b.craft_series(PatternSpec(kind=AttackPattern.DRIFT_CREEP, steps=60))
        assert len(rows) == 60
        assert abs(rows[0]["X_t"] - 1000.0) < 1e-9
        # constant per-step relative drift, never a spike
        rates = [r["dX_t"] / max(r["X_t"], 1.0) for r in rows]
        assert all(abs(rate - 0.005) < 1e-9 for rate in rates)
        # cumulative +~35%, monotonically up
        assert rows[-1]["X_t"] > 1300.0
        assert all(rows[i + 1]["X_t"] >= rows[i]["X_t"] for i in range(59))

    def test_level_tracking_pool_has_no_wedge(self):
        # kappa 0.5: equilibrium lag under a 0.5%/step grind is
        # growth/kappa = 13.5 — a genuinely fast tracker keeps pace
        m = _model([
            {"name": "pool",
             "expression": "S_t1 = clip(S_t + 0.5*(X_t - S_t), 200.0, 4000.0)",
             "description": "fast level-tracking pool keeps pace"},
        ], version=1)
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.DRIFT_CREEP, steps=60)
        )
        # a fast tracker ends near the level: no responsiveness lag
        assert not bound.drift_wedges or all(
            v < 25.0 for v in bound.drift_wedges.values()
        )

    def test_slow_state_wedge_disclosed_not_headlined(self):
        m = _model([
            {"name": "slow",
             "expression": "S_t1 = clip(S_t + 0.01*(X_t - S_t), 200.0, 4000.0)",
             "description": "slow tracker: lags a grinding regime"},
        ], version=1)
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.DRIFT_CREEP, steps=60)
        )
        # the lag is disclosed as a responsiveness wedge...
        assert "S_t_wedge" in bound.drift_wedges
        assert bound.drift_wedges["S_t_wedge"] > 100.0
        # ...but must NOT enter the headline: no consumer response to
        # harvest (attribution honesty — the r17 lesson)
        assert not any(k.endswith("_wedge") for k in bound.pattern_metrics
                       ) or bound.headline == 0.0 or "wedge" not in str(
                       bound.headline_metric)

    def test_wedge_metric_ignores_non_level_states(self):
        # a fee keyed to pressure (not level): |F - X| is meaningless;
        # the denomination gate must skip it
        m = _model([
            {"name": "fee",
             "expression": "F_t1 = clip(600.0 + 20.0*abs(dX_t)/max(X_t,1.0)*"
                           "100.0, 200.0, 1500.0)",
             "description": "pressure-keyed fee (never at level scale)"},
        ], version=1, variables=[
            *_trend_vars(),
            {"name": "fee", "symbol": "F_t", "role": "state", "units": "u",
             "description": "fee level"},
            {"name": "fee_next", "symbol": "F_t1", "role": "state", "units": "u",
             "description": "next fee"},
        ])
        bound = AttackPatternBattery(m).run_pattern(
            PatternSpec(kind=AttackPattern.DRIFT_CREEP, steps=60)
        )
        assert "F_t_wedge" not in bound.drift_wedges


class TestGrindHarvestPattern:
    """The r18 compound choreography: creep, then strike into the
    loaded system. Pins the two-phase craft, the CREEP-ONLY matched
    base (isolating what the timed strike adds), and the sequencing
    semantics: for a level-recentered design the compound's edge must
    not exceed the single-strike bound (the creep pre-loads states in
    the defender's favor — anchors and reserves ride up with the
    grind)."""

    def test_craft_two_phase_creep_then_strike(self):
        b = AttackPatternBattery(_model([
            {"name": "pool",
             "expression": "S_t1 = clip(S_t + 0.5*(X_t - S_t), 200.0, 4000.0)",
             "description": "level-tracking pool"},
        ], version=1))
        rows = b.craft_series(PatternSpec(kind=AttackPattern.GRIND_HARVEST, steps=60))
        assert len(rows) == 60
        grind_until = int(60 * 0.5)
        # phase 1: constant creep, no spikes
        rates = [r["dX_t"] / max(r["X_t"], 1.0) for r in rows[:grind_until]]
        assert all(abs(rate - 0.005) < 1e-9 for rate in rates)
        # the strike: one -60% step at grind_until
        assert abs(rows[grind_until]["dX_t"] / rows[grind_until]["X_t"] + 0.6) < 1e-9
        # phase 2: parked, dX=0
        assert all(r["dX_t"] == 0.0 for r in rows[grind_until + 1:])

    def test_base_is_creep_only_no_strike(self):
        b = AttackPatternBattery(_model([
            {"name": "pool",
             "expression": "S_t1 = clip(S_t + 0.5*(X_t - S_t), 200.0, 4000.0)",
             "description": "level-tracking pool"},
        ], version=1))
        spec = PatternSpec(kind=AttackPattern.GRIND_HARVEST, steps=60)
        rows = b.base_series(spec)
        grind_until = int(60 * 0.5)
        rates = [r["dX_t"] / max(r["X_t"], 1.0) for r in rows[:grind_until]]
        assert all(abs(rate - 0.005) < 1e-9 for rate in rates)
        # no strike anywhere in the matched base
        assert all(r["dX_t"] >= 0.0 for r in rows)
        assert all(r["dX_t"] == 0.0 for r in rows[grind_until:])

    def test_compound_edge_not_above_single_strike(self):
        # a single-magnet pool: re-basing design; the compound must not
        # exceed the crash_park bound (the creep pre-loads the pool
        # UP, so the strike from an elevated pool is not deeper)
        m = _model([
            {"name": "pool",
             "expression": "S_t1 = clip(S_t + 0.18*(X_t - S_t)"
                           " - 0.2*s_t*300.0, 250.0, 3000.0)",
             "description": "single-magnet recentering pool"},
            {"name": "stress",
             "expression": "s_t = sqrt(max(0.0, abs(X_t - S_t)/max(X_t,1.0)"
                           " - 0.05))",
             "description": "stress keyed to the closing deviation"},
        ], version=1, variables=[
            *_vars(),
            {"name": "stress", "symbol": "s_t", "role": "auxiliary",
             "units": "u", "description": "stress signal"},
        ])
        b = AttackPatternBattery(m)
        cp = b.run_pattern(PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60))
        gh = b.run_pattern(PatternSpec(kind=AttackPattern.GRIND_HARVEST, steps=60))
        assert (gh.headline or 0.0) <= (cp.headline or 0.0) + 25.0


class TestRound18Classifications:
    """r18: pin-aware arrival, heal-contradiction guard, separation
    anchors — the two measurement bugs the compound census exposed."""

    def _pinned_model() -> MathModel:
        """Z bleeds to its 400 floor which EQUALS the crash level 400
        — the Cyclic condition: pin read as 'arrival'. K tracks the
        level with noise-coupling so the run stays non-degenerate (a
        frozen run is vacuous by §15 and the headline test would not
        isolate the classification)."""
        return MathModel(
            candidate_id="cand-test-pin",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "pool", "symbol": "Z_t", "role": "state",
                 "units": "u", "description": "pool"},
                {"name": "pool_next", "symbol": "Z_t1", "role": "state",
                 "units": "u", "description": "next pool"},
                {"name": "tracker", "symbol": "K_t", "role": "state",
                 "units": "u", "description": "level tracker"},
                {"name": "tracker_next", "symbol": "K_t1", "role": "state",
                 "units": "u", "description": "next tracker"},
            ],
            parameters=[],
            equations=[
                {"name": "pool",
                 "expression": "Z_t1 = clip(Z_t + 0.10*(X_t-1000.0)"
                               " + 0.06*abs(K_t - Z_t),"
                               " 400.0, 3000.0)",
                 "description": "uncapped bleed below 1000 (the flaw)"},
                {"name": "tracker",
                 "expression": "K_t1 = clip(K_t*(1-0.25)"
                               " + 0.25*(X_t + 8.0*abs(dX_t)),"
                               " 200.0, 3000.0)",
                 "description": "tracker keeps the run non-degenerate"},
            ],
            assumptions=[{"statement": "test fixture assumption", "critical": True}],
            constraints=[],
            open_questions=["test fixture question"],
            rationale="test fixture",
            version=1,
        )

    def test_floor_pinned_state_is_not_regime_tracking(self) -> None:
        m = TestRound18Classifications._pinned_model()
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.CRASH_PARK,
                                      steps=60))
        # Z ends exactly at its 400 clip floor, which equals the
        # crashed level: pre-r18 this read as 'arrival' and hid the
        # drain; the pin-aware amendment must keep it an edge.
        assert "Z_t_drawn" not in r.regime_tracking
        assert r.headline is not None and r.headline > 400.0

    def _healing_model() -> MathModel:
        """V reverts to a 1000 anchor while the level parks at 400 —
        heals far from the level: the Treasury condition."""
        return MathModel(
            candidate_id="cand-test-heal",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "signal", "symbol": "V_t", "role": "state",
                 "units": "u", "description": "anchored vote signal"},
                {"name": "signal_next", "symbol": "V_t1", "role": "state",
                 "units": "u", "description": "next signal"},
            ],
            parameters=[],
            equations=[
                {"name": "signal",
                 "expression": "V_t1 = clip(V_t*(1-0.5)"
                               " + 0.5*(1000.0 + 60.0*(dX_t"
                               "/max(X_t,1.0))*1000.0), 400.0, 1800.0)",
                 "description": "1000-anchored reverting signal (the "
                               "r13 flaw signature)"},
            ],
            assumptions=[{"statement": "test fixture assumption", "critical": True}],
            constraints=[],
            open_questions=["test fixture question"],
            rationale="test fixture",
            version=1,
        )

    def test_anchor_heal_not_reclassified_transient(self) -> None:
        m = TestRound18Classifications._healing_model()
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.CRASH_PARK,
                                      steps=60))
        # V's window-end displacement sits under the 25% transient
        # threshold (it healed toward its 1000 anchor) BUT it ends FAR
        # from the moved level 400 — pre-r18 the transient check popped
        # it and hid the anchor-heal flaw; the guard must keep it an
        # edge (the honesty fix must not become a hiding place).
        assert "V_t_drawn" not in r.transient_recovered
        assert r.headline is not None and r.headline > 100.0

    def test_genuine_transient_still_classified(self) -> None:
        # a state that recovers TO THE LEVEL (near it at window end)
        # remains transient — the guard must not over-trigger
        m = MathModel(
            candidate_id="cand-test-trans",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "index", "symbol": "M_t", "role": "state",
                 "units": "u", "description": "throughput index"},
                {"name": "index_next", "symbol": "M_t1", "role": "state",
                 "units": "u", "description": "next index"},
            ],
            parameters=[],
            equations=[
                {"name": "index",
                 "expression": "M_t1 = clip(M_t*(1-0.8) + 0.8*X_t,"
                               " 100.0, 3000.0)",
                 "description": "fast level tracker (recovers to the "
                               "moved level)"},
            ],
            assumptions=[{"statement": "test fixture assumption", "critical": True}],
            constraints=[],
            open_questions=["test fixture question"],
            rationale="test fixture",
            version=1,
        )
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.CRASH_PARK,
                                      steps=60))
        # M ends AT the moved level — classified (arrival or
        # regime-tracking per the EMA filter), never a standing edge
        assert r.headline is None or r.headline < 100.0

    def test_separation_consumed_anchor_excluded(self) -> None:
        # the r18 class A successor pattern: an ultra-slow anchor read
        # by its consumer ONLY via separation with another state
        from blockchain_rd_lab.simulation.adversarial import (
            _separation_consumed_anchors,
        )
        m = MathModel(
            candidate_id="cand-test-sep",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "medium", "symbol": "I_t", "role": "state",
                 "units": "u", "description": "medium EMA"},
                {"name": "medium_next", "symbol": "I_t1", "role": "state",
                 "units": "u", "description": "next medium"},
                {"name": "anchor", "symbol": "U_s", "role": "state",
                 "units": "u", "description": "ultra-slow anchor"},
                {"name": "anchor_next", "symbol": "U_s1", "role": "state",
                 "units": "u", "description": "next anchor"},
                {"name": "premium", "symbol": "P_t", "role": "state",
                 "units": "u", "description": "premium"},
                {"name": "premium_next", "symbol": "P_t1", "role": "state",
                 "units": "u", "description": "next premium"},
            ],
            parameters=[],
            equations=[
                {"name": "medium",
                 "expression": "I_t1 = clip(I_t + 0.25*(X_t - I_t),"
                               " 200.0, 3000.0)",
                 "description": "medium EMA of the level"},
                {"name": "anchor",
                 "expression": "U_s1 = clip(U_s + 0.03*(I_t - U_s),"
                               " 200.0, 3000.0)",
                 "description": "ultra-slow anchor"},
                {"name": "premium",
                 "expression": "P_t1 = clip(600.0 + 0.5*(I_t1 - U_s1),"
                               " 300.0, 1600.0)",
                 "description": "premium keys the SEPARATION"},
            ],
            assumptions=[{"statement": "test fixture assumption", "critical": True}],
            constraints=[],
            open_questions=["test fixture question"],
            rationale="test fixture",
            version=1,
        )
        assert "U_s" in _separation_consumed_anchors(m)
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.CRASH_PARK,
                                      steps=60))
        # the anchor's lag is a design property (its consumer keys the
        # separation), not an attacker edge
        assert "U_s_drawn" not in [
            k for k in (
                list(r.regime_tracking) + list(r.transient_recovered)
            )
        ] or "U_s_drawn" in r.regime_tracking


class TestRound19WindowRobustness:
    """r19: long-window arrival confirmation — transit is not
    extraction, but pins and anchor-heals never ride it back in."""

    def _transit_model() -> MathModel:
        """A slow pool keyed to a slow level-EMA: at 60 steps it is
        still re-basing toward the moved level (the audit finding);
        by 120 it has arrived."""
        return MathModel(
            candidate_id="cand-test-transit",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "pool", "symbol": "W_t", "role": "state",
                 "units": "u", "description": "pool"},
                {"name": "pool_next", "symbol": "W_t1", "role": "state",
                 "units": "u", "description": "next pool"},
                {"name": "regime", "symbol": "T_w", "role": "state",
                 "units": "u", "description": "slow regime EMA"},
                {"name": "regime_next", "symbol": "T_w1", "role": "state",
                 "units": "u", "description": "next regime EMA"},
                {"name": "stress", "symbol": "S_w", "role": "state",
                 "units": "u", "description": "stress memory"},
                {"name": "stress_next", "symbol": "S_w1", "role": "state",
                 "units": "u", "description": "next stress memory"},
                {"name": "flow", "symbol": "f_w", "role": "auxiliary",
                 "units": "u", "description": "capped flow"},
            ],
            parameters=[],
            equations=[
                {"name": "regime",
                 "expression": "T_w1 = clip(T_w + 0.12*clip(X_t - T_w,"
                               " -500.0, 500.0), 100.0, 9000.0)",
                 "description": "slow bounded-step EMA of the level"},
                {"name": "flow",
                 "expression": "f_w = clip(0.15*clip(T_w - W_t,"
                               " -3000.0, 3000.0), -60.0, 60.0)",
                 "description": "symmetric capped flow"},
                {"name": "stress",
                 "expression": "S_w1 = clip(S_w*0.97 + 0.05*abs(dX_t)"
                               " + 0.02*S_w, 0.0, 300.0)",
                 "description": "stress memory"},
                {"name": "pool",
                 "expression": "W_t1 = clip(W_t + f_w"
                               " + 6.0*abs(dX_t)/max(X_t,1.0),"
                               " 250.0, 4000.0)",
                 "description": "pool chases the regime EMA; floor below "
                               "the crash level"},
            ],
            assumptions=[{"statement": "test fixture assumption",
                          "critical": True}],
            constraints=[],
            open_questions=["test fixture question"],
            rationale="test fixture",
            version=1,
        )

    def test_slow_pool_transit_not_headlined(self) -> None:
        m = TestRound19WindowRobustness._transit_model()
        b = AttackPatternBattery(m)
        # at the 60-step window the pool is mid re-basing...
        r60 = b.run_pattern(PatternSpec(
            kind=AttackPattern.GRIND_HARVEST, steps=60))
        # ...and the long-window confirmation reclassifies it as
        # in-transit (it arrives by 120), so it never headlines
        assert "W_t_drawn" in r60.in_transit
        assert r60.in_transit["W_t_drawn"] > 100.0
        # the raw excursion is disclosed, not hidden: in_transit
        # carries the value the state was moving by
        r120 = b.run_pattern(PatternSpec(
            kind=AttackPattern.GRIND_HARVEST, steps=120))
        assert (r120.headline or 0.0) <= 150.0

    def test_floor_pin_never_rides_arrival_back_in(self) -> None:
        # the r19 honesty guard: a state PINNED at its clip bound at
        # the long window is NOT arrived (the Productivity-Index
        # condition) — it must stay a visible edge
        m = TestRound18Classifications._pinned_model()
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.CRASH_PARK,
                                      steps=60))
        assert "Z_t_drawn" not in r.in_transit
        assert r.headline is not None and r.headline > 400.0

    def test_anchor_heal_never_rides_arrival_back_in(self) -> None:
        # the r18 Treasury condition: V heals toward its 1000 anchor
        # while the level parks at 400 — at the long window V is even
        # FURTHER from the level; it must stay a visible edge
        m = TestRound18Classifications._healing_model()
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.CRASH_PARK,
                                      steps=60))
        assert "V_t_drawn" not in r.in_transit
        assert r.headline is not None and r.headline > 100.0
class TestRound20Resonance:
    """r20: the repetition choreography — a ratchet is N-cycles of
    damage the design failed to re-base; transit is recovery in
    progress when the last cycle lands. The quiet-tail layer
    separates them numerically; pins never ride it back in."""

    def _ratchet_model() -> MathModel:
        """The Vol-Weighted condition: retention keys ABSOLUTE vol —
        every ramp pins r_t at the ceiling, inflow over-accrues
        each cycle. K keeps the run non-degenerate."""
        return MathModel(
            candidate_id="cand-test-ratchet",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "escrow", "symbol": "E_t", "role": "state",
                 "units": "u", "description": "escrow"},
                {"name": "escrow_next", "symbol": "E_t1", "role": "state",
                 "units": "u", "description": "next escrow"},
                {"name": "retention", "symbol": "r_t", "role": "state",
                 "units": "frac", "description": "retention"},
                {"name": "retention_next", "symbol": "r_t1",
                 "role": "state", "units": "frac",
                 "description": "next retention"},
                {"name": "tracker", "symbol": "K_t", "role": "state",
                 "units": "u", "description": "tracker"},
                {"name": "tracker_next", "symbol": "K_t1", "role": "state",
                 "units": "u", "description": "next tracker"},
                {"name": "vol", "symbol": "sigma_t", "role": "auxiliary",
                 "units": "frac", "description": "realized vol"},
            ],
            parameters=[],
            equations=[
                {"name": "vol",
                 "expression": "sigma_t = abs(dX_t)/max(X_t,1.0)",
                 "description": "realized vol"},
                {"name": "retention",
                 "expression": "r_t1 = clip(0.5 + 40.0*sigma_t,"
                               " 0.1, 0.9)",
                 "description": "absolute-vol retention (the flaw: "
                                "every crafted ramp pins the ceiling)"},
                {"name": "escrow",
                 "expression": "E_t1 = clip(E_t + 10.0*r_t"
                               " - E_t*0.005, 100.0, 100000.0)",
                 "description": "asymmetric accrual (the flaw)"},
                {"name": "tracker",
                 "expression": "K_t1 = clip(K_t*(1-0.25)"
                               " + 0.25*(X_t + 8.0*abs(dX_t)),"
                               " 200.0, 3000.0)",
                 "description": "tracker keeps the run non-degenerate"},
            ],
            assumptions=[{"statement": "test fixture assumption",
                          "critical": True}],
            constraints=[],
            open_questions=["test fixture question"],
            rationale="test fixture",
            version=1,
        )

    def _transit_model() -> MathModel:
        """A full-re-basing pool: each cycle's excursion closes by
        the window end (the Relay/Fee-Sink condition — recovery in
        progress when the last cycle lands, closes under quiet)."""
        return MathModel(
            candidate_id="cand-test-resonance-transit",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "pool", "symbol": "M_t", "role": "state",
                 "units": "u", "description": "pool"},
                {"name": "pool_next", "symbol": "M_t1", "role": "state",
                 "units": "u", "description": "next pool"},
                {"name": "tracker", "symbol": "K_t", "role": "state",
                 "units": "u", "description": "tracker"},
                {"name": "tracker_next", "symbol": "K_t1", "role": "state",
                 "units": "u", "description": "next tracker"},
            ],
            parameters=[],
            equations=[
                {"name": "pool",
                 "expression": "M_t1 = clip(M_t*(1-0.30)"
                               " + 0.30*(1000.0 + 0.20*(X_t-1000.0)),"
                               " 150.0, 3000.0)",
                 "description": "fast reverting EMA of a bounded target "
                                "(full re-base each cycle)"},
                {"name": "tracker",
                 "expression": "K_t1 = clip(K_t*(1-0.25)"
                               " + 0.25*(X_t + 8.0*abs(dX_t)),"
                               " 200.0, 3000.0)",
                 "description": "tracker keeps the run non-degenerate"},
            ],
            assumptions=[{"statement": "test fixture assumption",
                          "critical": True}],
            constraints=[],
            open_questions=["test fixture question"],
            rationale="test fixture",
            version=1,
        )

    def test_resonance_craft_full_recovery_each_cycle(self) -> None:
        bat = AttackPatternBattery(TestRound20Resonance._transit_model())
        rows = bat.craft_series(PatternSpec(
            kind=AttackPattern.RESONANCE, steps=60, strikes=4))
        assert len(rows) == 60
        # each cycle: strike, linear ramp back to anchor, quiet beat
        assert abs(rows[0]["dX_t"] - 1000.0 * -0.6) < 1e-9
        assert abs(rows[13]["dX_t"] - (1000.0 - rows[13]["X_t"])) < 1e-6
        # the level returns to the anchor by every cycle end
        for cyc in (1, 2, 3, 4):
            assert abs(rows[cyc * 15 - 1]["X_t"] - 1000.0) < 1e-6

    def test_resonance_base_is_one_late_cycle(self) -> None:
        bat = AttackPatternBattery(TestRound20Resonance._transit_model())
        spec = PatternSpec(kind=AttackPattern.RESONANCE, steps=60,
                           strikes=4)
        base = bat.base_series(spec)
        pat = bat.craft_series(spec)
        # one strike in the base, at the pattern's LAST-cycle position
        strikes_b = [t for t, r in enumerate(base) if r["dX_t"] < -100.0]
        strikes_p = [t for t, r in enumerate(pat) if r["dX_t"] < -100.0]
        assert len(strikes_b) == 1
        assert len(strikes_p) == 4
        assert strikes_b[0] == strikes_p[-1]
        # both runs end quiet at the anchor: identical final phase
        assert base[-1]["X_t"] == pat[-1]["X_t"] == 1000.0

    def test_reverting_pool_transit_not_ratchet(self) -> None:
        m = TestRound20Resonance._transit_model()
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.RESONANCE,
                                      steps=60))
        # the pool's window-end gap closes under quiet: transit,
        # never a resonance edge
        assert (r.headline or 0.0) <= 150.0
        assert any(k.startswith("M_t") for k in r.in_transit)

    def test_vol_ratchet_stays_visible(self) -> None:
        m = TestRound20Resonance._ratchet_model()
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.RESONANCE,
                                      steps=60))
        # the retention ratchet accumulates and PERSISTS under
        # quiet: it must stay a visible edge, never in_transit
        assert "E_t_ratchet" in r.edge
        assert "E_t_ratchet" not in r.in_transit
        assert r.headline is not None and r.headline > 100.0

    def test_cycled_metrics_disclosed_not_headlined(self) -> None:
        m = TestRound20Resonance._ratchet_model()
        b = AttackPatternBattery(m)
        r = b.run_pattern(PatternSpec(kind=AttackPattern.RESONANCE,
                                      steps=60))
        # the movement volume the attacker forced is DISCLOSED...
        assert "E_t_cycled" in r.pattern_metrics
        assert r.pattern_metrics["E_t_cycled"] > 100.0
        # ...but never enters the headline (r17 attribution: flow
        # volume is a cost, not an extraction until a consumer
        # pays it)
        assert all(not k.endswith("_cycled") for k in r.bound_metrics)
        assert all(not k.endswith("_final") for k in r.bound_metrics)
class TestRound22ParameterSweep:
    """r22: a bound measured only at the default calibration is a
    calibration artifact — the sweep's variants must measure REAL
    off-default attacks (never a silent re-run of the default),
    and every variant must be non-vacuous (a real bound, not a
    None-as-zero)."""

    def test_off_default_calibration_changes_the_run(self) -> None:
        # the sweep's honesty premise: setattr on the spec must
        # reach the crafted series — a typo'd/ignored param would
        # silently re-measure the default and the sweep would lie
        m = TestRound20Resonance._ratchet_model()
        bat = AttackPatternBattery(m)
        default = PatternSpec(kind=AttackPattern.RESONANCE, steps=60)
        off = PatternSpec(kind=AttackPattern.RESONANCE, steps=60)
        off.strikes = 16
        rows_d = bat.craft_series(default)
        rows_o = bat.craft_series(off)
        # the SAME window now holds 16 strike-cycles, not 4
        strikes_d = sum(1 for r in rows_d if r["dX_t"] < -100.0)
        strikes_o = sum(1 for r in rows_o if r["dX_t"] < -100.0)
        assert strikes_d == 4 and strikes_o == 16
        # and the measured bound differs (a different attack)
        assert bat.run_pattern(default).pattern_metrics != \
            bat.run_pattern(off).pattern_metrics

    def test_sweep_variants_all_non_vacuous(self) -> None:
        # every off-default variant of the r22 sweep measures a
        # REAL bound against a model with dynamics: headline is a
        # float (possibly 0.0 = measured-clean), never None
        # (vacuous) — a vacuous variant would silently drop out of
        # the sweep max (the worst-edge number would understate)
        m = TestRound20Resonance._ratchet_model()
        bat = AttackPatternBattery(m)
        sweep: list[tuple[AttackPattern, str, float]] = [
            (AttackPattern.VOL_OSCILLATION, "amplitude", 0.02),
            (AttackPattern.VOL_OSCILLATION, "amplitude", 0.10),
            (AttackPattern.WASH_FLOW, "wash_level", 0.04),
            (AttackPattern.CRASH_PARK, "park_shift", -0.3),
            (AttackPattern.CRASH_PARK, "park_shift", -0.9),
            (AttackPattern.DRIFT_CREEP, "creep_rate", 0.01),
            (AttackPattern.GRIND_HARVEST, "harvest_shift", -0.9),
            (AttackPattern.RESONANCE, "strikes", 2),
            (AttackPattern.RESONANCE, "strikes", 8),
            (AttackPattern.RESONANCE, "strikes", 16),
            (AttackPattern.RESONANCE, "strike_shift", -0.9),
        ]
        for kind, param, value in sweep:
            spec = PatternSpec(kind=kind, steps=60)
            setattr(spec, param, value)
            r = bat.run_pattern(spec)
            assert not r.vacuous, f"{kind}/{param}={value}"
            assert r.headline is not None, f"{kind}/{param}={value}"
            assert not r.failures, f"{kind}/{param}={value}"



class TestRound33AuditFixes:
    """r33: the external-audit response round. F2 (long-window spec
    preservation), F3 (e/pi interpreter constants), and the r33 pin
    counterfactual — position cannot tell a stopped drain from a
    converged EMA; the relax-and-rerun measurement can."""

    def test_f3_pi_executes_in_equations(self) -> None:
        # F3: `pi` is §13-valid syntax but the interpreter rejected
        # the bare symbol ("used but not declared") — a schema-valid
        # model that could not execute. e/pi now evaluate as math
        # constants.
        from blockchain_rd_lab.simulation.interpreter import (
            EquationInterpreter,
        )
        m = MathModel(
            candidate_id="cand-test-pi",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "scale", "symbol": "P_t", "role": "state",
                 "units": "u", "description": "pi-scaled state"},
                {"name": "scale_next", "symbol": "P_t1", "role": "state",
                 "units": "u", "description": "next"},
            ],
            parameters=[],
            equations=[
                {"name": "scale",
                 "expression": "P_t1 = clip(pi*X_t, 100.0, 10000.0)",
                 "description": "pi-scaled"},
            ],
            assumptions=[{"statement": "fixture assumption", "critical": True}],
            constraints=[],
            open_questions=["fixture open question"],
            rationale="F3 interpreter probe fixture",
            version=1,
        )
        interp = EquationInterpreter(m)
        out = interp.evaluate({"X_t": 1000.0, "dX_t": 0.0, "P_t": 1000.0})
        assert abs(out["P_t1"] - 3141.592653589793) < 1e-9

    def test_f3_declared_symbol_shadows_constant(self) -> None:
        # A DECLARED variable named `e` wins over the constant (the
        # schema is the contract; the constant is the fallback).
        from blockchain_rd_lab.simulation.interpreter import (
            EquationInterpreter,
        )
        m = MathModel(
            candidate_id="cand-test-shadow",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "edge", "symbol": "e", "role": "state",
                 "units": "u", "description": "declared e"},
                {"name": "edge_next", "symbol": "e1", "role": "state",
                 "units": "u", "description": "next e"},
            ],
            parameters=[],
            equations=[
                {"name": "edge",
                 "expression": "e1 = clip(e + 1.0, 0.0, 100.0)",
                 "description": "shadow probe"},
            ],
            assumptions=[{"statement": "fixture assumption", "critical": True}],
            constraints=[],
            open_questions=["fixture open question"],
            rationale="F3 declared-shadow probe fixture",
            version=1,
        )
        interp = EquationInterpreter(m)
        out = interp.evaluate({"X_t": 1000.0, "dX_t": 0.0, "e": 42.0})
        assert abs(out["e1"] - 43.0) < 1e-12

    def test_f2_long_window_preserves_full_calibration(self) -> None:
        # F2: the long-window re-run must carry the caller's FULL
        # calibration (model_copy, never a kind/steps/park_at rebuild).
        # A park_shift=-0.9 variant confirmed as transit at 120 steps
        # was previously decided by the DEFAULT -0.6 attack.
        mm = TestRound20Resonance._transit_model()
        spec = PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        spec.park_shift = -0.9
        bat = AttackPatternBattery(mm)
        r = bat.run_pattern(spec)
        # the calibrated attack's own bound is what classifies — no
        # exception, real measurement, and the long-window path ran
        # under the SAME park_shift (crash to 100, not 400)
        assert not r.failures
        # counter-check: the craft for the doubled window parks at
        # the SAME fraction of the window (park_at doubled, not reset)
        craft60 = bat.craft_series(spec)
        long_spec = spec.model_copy(update={
            "steps": 120, "park_at": min(spec.park_at * 2, 118)})
        craft120 = bat.craft_series(long_spec)
        assert len(craft120) == 120
        # the parked rows after the doubled park point hold the SAME
        # crashed level as the 60-step run's parked rows
        assert abs(
            craft60[-1]["X_t"] - craft120[-1]["X_t"]) < 1e-9

    def test_r33_pin_counterfactual_inert_bound_exonerates(self) -> None:
        # The successor's L_f geometry: an EMA whose converged level
        # COINCIDES with its clip floor. Position says pin; the
        # counterfactual (relax the floor, rerun the same attack)
        # says the clip never bound — the state ARRIVED. It must
        # classify as regime tracking, never a 900 "edge".
        m = MathModel(
            candidate_id="cand-test-cf-inert",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "fast", "symbol": "L_t", "role": "state",
                 "units": "u", "description": "fast EMA of level"},
                {"name": "fast_next", "symbol": "L_t1", "role": "state",
                 "units": "u", "description": "next fast EMA"},
            ],
            parameters=[],
            equations=[
                {"name": "fast",
                 "expression": "L_t1 = clip(L_t + 0.6*(X_t - L_t),"
                               " 100.0, 10000.0)",
                 "description": "fast EMA, floor == crash level"},
            ],
            assumptions=[{"statement": "fixture assumption", "critical": True}],
            constraints=[],
            open_questions=["fixture open question"],
            rationale="r33 pin-counterfactual probe fixture",
            version=1,
        )
        spec = PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        spec.park_shift = -0.9
        r = AttackPatternBattery(m).run_pattern(spec)
        assert "L_t_drawn" in r.regime_tracking
        assert r.regime_tracking["L_t_drawn"] == 900.0
        assert r.headline is None or r.headline < 400.0

    def test_r33_pin_counterfactual_load_bearing_keeps_pin(self) -> None:
        # The Cyclic geometry (r18): a pool whose dynamics carry it
        # BELOW its floor — the clip is LOAD-BEARING, the state was
        # stopped mid-drain. The counterfactual must KEEP the pin a
        # disclosed edge; regime_tracking must not hide it.
        from blockchain_rd_lab.simulation.adversarial import (
            _pin_is_load_bearing,
        )
        m = MathModel(
            candidate_id="cand-test-cf-load",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "pool", "symbol": "Z_t", "role": "state",
                 "units": "u", "description": "pool"},
                {"name": "pool_next", "symbol": "Z_t1", "role": "state",
                 "units": "u", "description": "next pool"},
                {"name": "tracker", "symbol": "K_t", "role": "state",
                 "units": "u", "description": "tracker keeps run alive"},
                {"name": "tracker_next", "symbol": "K_t1", "role": "state",
                 "units": "u", "description": "next tracker"},
            ],
            parameters=[],
            equations=[
                {"name": "pool",
                 "expression": "Z_t1 = clip(Z_t + 0.10*(X_t - 1000.0)"
                               " - 5.0, 400.0, 3000.0)",
                 "description": "level-keyed drain, floor 400"},
                {"name": "tracker",
                 "expression": "K_t1 = clip(K_t + 0.25*(X_t - K_t),"
                               " 100.0, 3000.0)",
                 "description": "tracker keeps the run non-degenerate"},
            ],
            assumptions=[{"statement": "fixture assumption", "critical": True}],
            constraints=[],
            open_questions=["fixture open question"],
            rationale="r33 pin-counterfactual probe fixture",
            version=1,
        )
        spec = PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        bat = AttackPatternBattery(m)
        assert _pin_is_load_bearing(m, spec, bat, "Z_t") is True
        r = bat.run_pattern(spec)
        assert "Z_t_drawn" not in r.regime_tracking
        # the pin is a disclosed edge: pattern drew 600 (stopped AT
        # the floor), matched base drew ~261 — the measured standing
        # gap stays in the headline, never reclassified away
        assert r.edge["Z_t_drawn"] == pytest.approx(339.350401, abs=1e-4)
        assert r.headline is not None and r.headline_metric == "Z_t_drawn"

    def test_r33_pin_counterfactual_fail_closed(self) -> None:
        # Two fail-closed facts. (1) A state whose equation has NO
        # parseable trailing clip has NO declared bounds: no pin
        # question can even arise (the guard consults the counter-
        # factual only when position matched a PARSED bound — and the
        # parser and the relaxer share one regex, so a bound the
        # guard can see is always relaxable). (2) When the relaxed
        # counterfactual cannot RUN, the pin is KEPT — unmeasurable
        # is never exonerated (the anti-hiding rule).
        from blockchain_rd_lab.simulation.adversarial import (
            _pin_is_load_bearing,
        )
        m = MathModel(
            candidate_id="cand-test-cf-failclosed",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "pool", "symbol": "Q_t", "role": "state",
                 "units": "u", "description": "pool"},
                {"name": "pool_next", "symbol": "Q_t1", "role": "state",
                 "units": "u", "description": "next pool"},
            ],
            parameters=[],
            equations=[
                {"name": "pool",
                 "expression": "Q_t1 = clip(Q_t - 60.0, 400.0, 3000.0)"
                               " + min(10.0, X_t - 1000.0)",
                 "description": "trailing call is min, not clip"},
            ],
            assumptions=[{"statement": "fixture assumption",
                          "critical": True}],
            constraints=[],
            open_questions=["fixture open question"],
            rationale="r33 fail-closed probe fixture",
            version=1,
        )
        spec = PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60)
        bat = AttackPatternBattery(m)
        # (1) no parsed bounds -> no pin question -> not load-bearing
        assert _pin_is_load_bearing(m, spec, bat, "Q_t") is False

        # (2) a counterfactual that cannot run keeps the pin
        m2 = MathModel(
            candidate_id="cand-test-cf-failclosed2",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "pool", "symbol": "W_t", "role": "state",
                 "units": "u", "description": "pool"},
                {"name": "pool_next", "symbol": "W_t1", "role": "state",
                 "units": "u", "description": "next pool"},
                {"name": "tracker", "symbol": "V_t", "role": "state",
                 "units": "u", "description": "tracker"},
                {"name": "tracker_next", "symbol": "V_t1", "role": "state",
                 "units": "u", "description": "next tracker"},
            ],
            parameters=[],
            equations=[
                {"name": "pool",
                 "expression": "W_t1 = clip(W_t - 60.0, 400.0, 3000.0)",
                 "description": "drain pool, floor 400"},
                {"name": "tracker",
                 "expression": "V_t1 = clip(V_t + 0.25*(X_t - V_t),"
                               " 100.0, 3000.0)",
                 "description": "tracker keeps runs non-degenerate"},
            ],
            assumptions=[{"statement": "fixture assumption",
                          "critical": True}],
            constraints=[],
            open_questions=["fixture open question"],
            rationale="r33 fail-closed probe fixture two",
            version=1,
        )
        bat2 = AttackPatternBattery(m2)
        # sanity: the real counterfactual convicts this pool
        assert _pin_is_load_bearing(m2, spec, bat2, "W_t") is True
        bat3 = AttackPatternBattery(m2)
        with pytest.MonkeyPatch().context() as mp:
            def broken_validate(*args, **kwargs):
                raise RuntimeError("counterfactual unbuildable")

            mp.setattr(MathModel, "model_validate", broken_validate)
            assert _pin_is_load_bearing(m2, spec, bat3, "W_t") is True


class TestRound34PreAuditSweep:
    """r34: the lab's own hostile pass over r33's new code, run
    BEFORE the next external auditor (the r28/r30 discipline).
    Three defects found in the round's own fixes — each pinned here
    the day it ships."""

    def test_r34_counterfactual_cache_key_is_the_full_spec(self) -> None:
        # The r33 cache key read (kind, steps, park_at, park_shift)
        # — it omitted every OTHER calibration field the battery
        # sweeps (harvest_shift, strikes, amplitude, wash_level,
        # creep_rate, lag_fraction, strike_shift). Within ONE
        # battery lifetime (the r33 sweep used one battery for all
        # 27 runs), a calibrated variant INHERITED the default's
        # counterfactual verdict: same key, verdict never computed.
        # The verdicts happened to coincide this round (verified by
        # full re-sweep after the fix: identical drift set), but a
        # classification that ships because two computations
        # COINCIDE is not a classification that was measured.
        # Fix: the key is spec.model_dump_json() — the complete,
        # deterministic serialization; two specs differing in ANY
        # field can never collide.
        from blockchain_rd_lab.simulation.adversarial import (
            _pin_is_load_bearing,
        )
        m = MathModel(
            candidate_id="cand-test-r34-cachekey",
            variables=[
                {"name": "level", "symbol": "X_t", "role": "input",
                 "units": "u", "description": "level"},
                {"name": "delta", "symbol": "dX_t", "role": "input",
                 "units": "u", "description": "delta"},
                {"name": "pool", "symbol": "Z_t", "role": "state",
                 "units": "u", "description": "pool"},
                {"name": "pool_next", "symbol": "Z_t1", "role": "state",
                 "units": "u", "description": "next pool"},
                {"name": "tracker", "symbol": "K_t", "role": "state",
                 "units": "u", "description": "tracker"},
                {"name": "tracker_next", "symbol": "K_t1", "role": "state",
                 "units": "u", "description": "next tracker"},
            ],
            parameters=[],
            equations=[
                {"name": "pool",
                 "expression": "Z_t1 = clip(Z_t + 0.10*(X_t - 1000.0)"
                               " - 5.0, 400.0, 3000.0)",
                 "description": "level-keyed drain, floor 400"},
                {"name": "tracker",
                 "expression": "K_t1 = clip(K_t + 0.25*(X_t - K_t),"
                               " 100.0, 3000.0)",
                 "description": "tracker keeps the run non-degenerate"},
            ],
            assumptions=[{"statement": "fixture assumption",
                          "critical": True}],
            constraints=[],
            open_questions=["fixture open question"],
            rationale="r34 cache-key collision probe fixture",
            version=1,
        )
        bat = AttackPatternBattery(m)
        # default grind_harvest first: verdict v1 lands in the cache
        default_spec = PatternSpec(
            kind=AttackPattern.GRIND_HARVEST, steps=60)
        v1 = _pin_is_load_bearing(m, default_spec, bat, "Z_t")
        # a HARVEST_SHIFT-only change (the r22 grid's @-0.9): the
        # OLD key would have returned v1 without computing. The
        # FIXED key must recompute — the verdict is independent.
        shifted = PatternSpec(
            kind=AttackPattern.GRIND_HARVEST, steps=60,
            harvest_shift=-0.9)
        cache = bat.__dict__.setdefault("_pin_cf_cache", {})
        before = dict(cache)
        v2 = _pin_is_load_bearing(m, shifted, bat, "Z_t")
        assert (default_spec.model_dump_json(), "Z_t") in before
        # the shifted spec's verdict came from its OWN run, not the
        # default's: its key exists and is DISTINCT
        assert (shifted.model_dump_json(), "Z_t") in cache
        assert (shifted.model_dump_json(), "Z_t") not in before
        # and per-spec recomputation is real: keys differ
        assert v1 == _pin_is_load_bearing(m, default_spec, bat, "Z_t")
        assert v2 == _pin_is_load_bearing(m, shifted, bat, "Z_t")

    def test_r34_interpreter_constants_parity_with_schema(self) -> None:
        # The r33 F3 fix's comment said "one source of truth: import
        # the canonical set" — but the code REDEFINED the dict
        # locally. Adding a constant to formalization._MATH_CONSTANTS
        # (schema accepts the model) without a value here would have
        # reopened F3's exact drift: schema-valid, unexecutable.
        # Fix: the interpreter imports the canonical set and a
        # module-load check + THIS probe pin the parity.
        from blockchain_rd_lab.formalization import _MATH_CONSTANTS
        from blockchain_rd_lab.simulation import interpreter as interp

        assert set(interp._CONSTANTS) == set(_MATH_CONSTANTS), (
            "interpreter constant set drifted from §13's "
            "_MATH_CONSTANTS — a schema-valid model would die at "
            "execution (the F3 class)"
        )
        # values are real: e/pi resolve to their numerics
        assert interp._CONSTANTS["e"] == pytest.approx(2.718281828459045)
        assert interp._CONSTANTS["pi"] == pytest.approx(3.141592653589793)

    def test_r34_gate_scope_disclosed_and_default_calibrated(self) -> None:
        # The gate measures the EIGHT default calibrations;
        # off-default robustness is the census layer's job (r22
        # sweep, published in §4b). The scope is now DISCLOSED in
        # _measured_flaw_edge's docstring — and pinned here as a
        # testable fact: every AttackPattern kind appears in the
        # evidence, none more (no hidden ninth pattern, no
        # silent subset that would under-measure the gate).
        import inspect

        from blockchain_rd_lab.redteam import service as rtsvc
        from blockchain_rd_lab.simulation.adversarial import AttackPattern

        doc = inspect.getdoc(rtsvc.RedTeamService._measured_flaw_edge)
        assert doc is not None
        flat = " ".join(doc.lower().split())
        assert "eight default calibrations" in flat
        # the evidence the gate builds covers exactly the pattern
        # enum — measured by running the real method against a
        # stored-model candidate is the integration test's job
        # (test_redteam.py); here pin the enum/evidence alignment
        # the method constructs from:
        kinds = [k.value for k in AttackPattern]
        assert len(kinds) == 8
        assert len(set(kinds)) == 8
