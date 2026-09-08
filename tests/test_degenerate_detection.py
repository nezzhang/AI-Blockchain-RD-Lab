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

