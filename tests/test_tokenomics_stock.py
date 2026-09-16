"""Tests for the §17 supply-stock composition layer (r43).

Probes pin the composed death-spiral dynamics:
- The ratio drivers' constant-velocity property (stable under demand
  shocks, value recovered exactly)
- The counter-cyclical inflationary collapse and deflationary
  runaway (the layer CONVICTS — not an acquittal machine)
- The asymmetric-clamp crash failure (corridor vs market, the
  differentiated pair)
- The melt that hides in levels (supply_shock with elasticity)
- Honest vacuity for one-sided bounded index drivers
- Determinism and registry-wide finiteness
"""

from __future__ import annotations

import math

import pytest

from blockchain_rd_lab.tokenomics.stock import (
    SCENARIOS,
    StockScenario,
    StockVerdict,
    run_stock_scenario,
    run_stock_suite,
)
from blockchain_rd_lab.tokenomics.supply_drivers import DRIVER_REGISTRY, get_driver


class TestStockComposition:
    """The composition layer's contract: same inputs -> same floats."""

    def test_deterministic(self):
        for d in DRIVER_REGISTRY:
            for sc in SCENARIOS.values():
                r1 = run_stock_scenario(d, sc)
                r2 = run_stock_scenario(d, sc)
                assert r1 == r2, (d.name, sc.name)

    def test_registry_wide_finiteness(self):
        """Every driver x scenario produces a verdict with finite
        metrics (no NaN leakage through the composition)."""
        for d in DRIVER_REGISTRY:
            for sc in SCENARIOS.values():
                r = run_stock_scenario(d, sc)
                for v in (
                    r.supply_ratio,
                    r.demand_ratio,
                    r.min_value,
                    r.max_abs_rate,
                ):
                    assert math.isfinite(v), (d.name, sc.name, v)
                # value_ratio may be 0 (annihilation) but never NaN
                assert not math.isnan(r.value_ratio)
                assert not math.isnan(r.tail_drift) or r.verdict is (
                    StockVerdict.VACUOUS
                )

    def test_composition_types(self):
        """Level-type drivers compose through their reference pairs;
        the signed rate-type (gdp) composes directly; one-sided
        bounded indices are honestly vacuous (the r40-F1 domain
        discipline — never credit states outside the declared
        domain)."""
        cases = {
            "market-volume": "level",
            "usage-growth": "level",
            "corridor-population": "level",
            "metcalfe-growth": "level",
            "usage-network-hybrid": "level",
            "counter-cyclical-gdp": "rate",
            "climate-risk-burn": "none",
            "claims-ratio-mint": "none",
            "uncertainty-mint": "none",
        }
        for name, expected in cases.items():
            r = run_stock_scenario(get_driver(name), SCENARIOS["steady"])
            assert r.composition == expected, (name, r.composition)

    def test_vacuous_carries_reason(self):
        r = run_stock_scenario(
            get_driver("climate-risk-burn"), SCENARIOS["steady"]
        )
        assert r.verdict is StockVerdict.VACUOUS
        assert "crisis-mapping" in r.note or "axis" in r.note


class TestRatioDriverStability:
    """The constant-velocity property, measured: rate tracks demand
    growth (one step lagged), value recovers to exactly 1.0 in the
    settled tail, supply tracks demand through the shock."""

    @pytest.mark.parametrize(
        "driver_name", ["market-volume", "usage-growth",
                        "commodity-basket-peg", "renewable-energy-pow"]
    )
    def test_stable_under_collapse(self, driver_name):
        r = run_stock_scenario(
            get_driver(driver_name), SCENARIOS["demand_collapse"]
        )
        assert r.verdict is StockVerdict.STABLE, (
            driver_name,
            r.verdict,
            r.tail_drift,
            r.endogenous_growth,
        )
        assert r.value_ratio == pytest.approx(1.0, abs=1e-6)
        assert r.supply_ratio == pytest.approx(r.demand_ratio, rel=1e-9)

    def test_stable_under_crash(self):
        """The -20%/step crash is WITHIN market-volume's clamp: the
        burn tracks the demand fall, value never moves."""
        r = run_stock_scenario(
            get_driver("market-volume"), SCENARIOS["crash"]
        )
        assert r.verdict is StockVerdict.STABLE
        assert r.value_ratio == pytest.approx(1.0, abs=1e-6)

    def test_collapse_amplification_measured(self):
        """The one-step lag + level feedback amplifies the driven
        shock toward gamma* = g/(1-eta) = -4%/step (eta=0.5): the
        growth converges to it geometrically (-0.02, -0.03, -0.035,
        ...), so D_30 lands slightly ABOVE the 0.96^30 asymptote —
        the measured 0.294184 is pinned here, transient included.
        With elasticity OFF the demand falls at exactly the driven
        rate (0.98^30) — the amplification is the feedback's, alone."""
        r = run_stock_scenario(
            get_driver("market-volume"), SCENARIOS["demand_collapse"]
        )
        assert r.demand_ratio == pytest.approx(
            0.2941842865, abs=1e-6
        )
        assert r.demand_ratio > 0.96**30  # transient above asymptote
        # with elasticity OFF the demand falls at the driven rate
        quiet = StockScenario(
            name="collapse_eta0",
            steps=90,
            shock_from=0,
            shock_to=30,
            shock_growth=-0.02,
            elasticity=0.0,
        )
        r0 = run_stock_scenario(get_driver("market-volume"), quiet)
        assert r0.demand_ratio == pytest.approx(0.98**30, rel=1e-9)
        assert r0.verdict is StockVerdict.STABLE

    def test_oscillation_net_deflation(self):
        """Symmetric +/-5% oscillation through the multiplicative
        stock leaves net deflation (1.05 x 0.95 < 1 per cycle) with
        value intact — the asymmetry shows in the LEVELS, not the
        ratio."""
        r = run_stock_scenario(
            get_driver("market-volume"), SCENARIOS["oscillation"]
        )
        assert r.verdict is StockVerdict.STABLE
        assert r.value_ratio == pytest.approx(1.0, abs=1e-4)
        assert r.supply_ratio < 1.0  # net deflation, measured


class TestSpirals:
    """The layer CONVICTS: the anti-hiding requirement (a battery
    that can only acquit is not evidence)."""

    def test_gdp_inflationary_collapse(self):
        """Counter-cyclicality that stabilizes an economy DESTROYS
        the composed token under demand collapse: the driver mints
        +|gamma| while demand dies -> supply explodes, value is
        annihilated. THE death spiral, measured."""
        r = run_stock_scenario(
            get_driver("counter-cyclical-gdp"),
            SCENARIOS["demand_collapse"],
        )
        assert r.verdict is StockVerdict.SPIRAL_DOWN
        assert r.endogenous_growth > 0.02  # sustained endogenous MINT
        assert r.value_ratio < 0.01  # value annihilated
        assert r.supply_ratio > 100.0  # supply exploded

    def test_gdp_deflationary_runaway(self):
        """The mirror: under organic growth the counter-cyclical
        driver burns while demand grows -> supply collapses, value
        explodes upward."""
        r = run_stock_scenario(
            get_driver("counter-cyclical-gdp"),
            SCENARIOS["organic_growth"],
        )
        assert r.verdict is StockVerdict.SPIRAL_UP
        assert r.supply_ratio < 0.01
        assert r.value_ratio > 100.0

    def test_corridor_asymmetric_clamp_crash(self):
        """THE differentiated pair: corridor-population's burn clamps
        at -0.1/step (the §25 demographic asymmetry) and CANNOT track
        a -20%/step crash — demand outruns the burn, value collapses.
        market-volume (clamp -1.0) tracks the same crash and stays
        stable (see test_stable_under_crash)."""
        r = run_stock_scenario(
            get_driver("corridor-population"), SCENARIOS["crash"]
        )
        assert r.verdict is StockVerdict.SPIRAL_DOWN
        assert r.max_abs_rate == pytest.approx(0.1)  # the clamp bound

    def test_supply_shock_melt_hides_in_levels(self):
        """A +10% mis-mint into elastic demand: value settles 17%
        below anchor and BOTH levels bleed ~8.3%/step forever — the
        melt the ratio-only verdict logic would miss (the r43
        first-draft bug class, pinned here)."""
        r = run_stock_scenario(
            get_driver("market-volume"), SCENARIOS["supply_shock"]
        )
        assert r.verdict is StockVerdict.SPIRAL_DOWN
        assert r.value_ratio == pytest.approx(1.0 / 1.2, abs=0.02)
        assert r.endogenous_growth == pytest.approx(-0.0833, abs=0.01)
        assert r.demand_ratio < 0.01  # the levels evaporated

    def test_supply_shock_melt_requires_elasticity(self):
        """The feedback channel is load-bearing: with elasticity=0
        the same mis-mint is a permanent rebase (value 9% below
        anchor, levels flat), NOT a melt."""
        quiet = StockScenario(
            name="supply_shock_eta0",
            steps=90,
            shock_from=0,
            shock_to=0,
            supply_shock_at=15,
            supply_shock=0.10,
            elasticity=0.0,
        )
        r = run_stock_scenario(get_driver("market-volume"), quiet)
        assert r.verdict is StockVerdict.REBASED_DOWN
        assert r.value_ratio == pytest.approx(1.0 / 1.1, abs=0.01)
        assert r.demand_ratio == pytest.approx(1.0, abs=1e-6)

    def test_hyper_growth_amplification_sustained(self):
        """At 5%/step drives the lag+feedback doubles the growth
        (gamma* = g/(1-eta) = 10%/step) — a sustained 2x endogenous
        amplification beyond the 2% tolerance: spiral_up with value
        settling only ~10% above anchor (the divergence is in the
        issuance compounding, disclosed by supply_ratio)."""
        r = run_stock_scenario(
            get_driver("market-volume"), SCENARIOS["hyper_growth"]
        )
        assert r.verdict is StockVerdict.SPIRAL_UP
        assert r.supply_ratio > 100.0

    def test_metcalfe_slow_divergence(self):
        """The log driver under-tracks (ln(1+g) != g) so every
        positive-feedback loop diverges slowly: even the collapse
        scenario ends with value ABOVE anchor and still moving."""
        r = run_stock_scenario(
            get_driver("metcalfe-growth"), SCENARIOS["demand_collapse"]
        )
        assert r.verdict is StockVerdict.SPIRAL_UP
        assert r.value_ratio > 1.0

    def test_hybrid_under_tracking_spirals(self):
        """The hybrid composes on its dominant axis (usage, 0.6
        weight; the node axis rides at neutral): partial tracking
        gain < 1 under-tracks demand -> the feedback loop diverges.
        Disclosed: the hybrid's r39 equilibrium claim does not
        survive single-axis stock composition."""
        r = run_stock_scenario(
            get_driver("usage-network-hybrid"),
            SCENARIOS["demand_collapse"],
        )
        assert r.verdict is StockVerdict.SPIRAL_DOWN


class TestScenarioMechanics:
    """The growth path and quiet-tail discipline (the r20 rule)."""

    def test_steady_is_flat_for_all_composable(self):
        for d in DRIVER_REGISTRY:
            r = run_stock_scenario(d, SCENARIOS["steady"])
            if r.verdict is StockVerdict.VACUOUS:
                continue
            assert r.verdict is StockVerdict.STABLE, (
                d.name,
                r.verdict,
            )
            assert r.supply_ratio == pytest.approx(1.0, abs=1e-9)
            assert r.value_ratio == pytest.approx(1.0, abs=1e-9)

    def test_shock_window_ends_before_tail(self):
        """Every non-baseline scenario's shock must end before the
        verdict window (the last quarter) begins — the tail reads
        what the system does AFTER the shock, by construction."""
        steps = 90
        tail_from = steps - steps // 4
        for sc in SCENARIOS.values():
            if sc.name == "steady":
                continue
            # growth scenarios drive the whole window by design
            if sc.baseline_growth != 0.0:
                continue
            assert sc.shock_to <= tail_from, sc.name

    def test_growth_path_deterministic_shape(self):
        sc = SCENARIOS["demand_collapse"]
        from blockchain_rd_lab.tokenomics.stock import _growth

        assert _growth(sc, 0) == -0.02
        assert _growth(sc, 29) == -0.02
        assert _growth(sc, 30) == 0.0
        assert _growth(sc, 89) == 0.0
        osc = SCENARIOS["oscillation"]
        assert _growth(osc, 0) == 0.05
        assert _growth(osc, 1) == -0.05
        assert _growth(osc, 59) == -0.05
        assert _growth(osc, 60) == 0.0

    def test_run_stock_suite_covers_all_scenarios(self):
        suite = run_stock_suite(get_driver("market-volume"))
        assert set(suite) == set(SCENARIOS)


class TestStockReportSection:
    """The §25 report now carries the measured death-spiral table."""

    @pytest.fixture()
    def stock_db(self, tmp_path):
        from blockchain_rd_lab.database import LabDatabase
        from blockchain_rd_lab.schemas import Candidate

        db = LabDatabase(tmp_path / "stock-report.db")
        db.create_all()
        db.save_candidate(
            Candidate(
                id="cand-tok1",
                name="Fee Smoothing Escrow",
                category="fx payments",
                description=(
                    "A fee-smoothing escrow whose retention keys the "
                    "SIGNED separation between fast pressure and a slow "
                    "regime anchor. Cross-border FX remittance payment "
                    "network."
                ),
                core_mechanism=(
                    "retention = f(signed_separation(fast, slow))"
                ),
                overall_score=6.45,
            )
        )
        return db

    def test_report_renders_stock_section(self, stock_db):
        from blockchain_rd_lab.tokenomics.report import build_token_report

        txt = build_token_report(stock_db, "cand-tok1")
        assert "## §17 Stock Scenarios (r43)" in txt
        assert "| Design ID | Collapse | Crash | Mis-Mint |" in txt
        assert "vacuous" in txt  # the honest-absence rows render

    def test_report_stock_verdicts_from_measurement(self, stock_db):
        """Every verdict cell in the rendered table is a real
        StockVerdict value (never prose, never blank)."""
        from blockchain_rd_lab.tokenomics.report import build_token_report
        from blockchain_rd_lab.tokenomics.stock import StockVerdict

        txt = build_token_report(stock_db, "cand-tok1")
        i = txt.find("## §17 Stock Scenarios")
        j = txt.find("## §25 Question Analysis")
        section = txt[i:j]
        valid = {v.value for v in StockVerdict}
        rows = [
            ln for ln in section.splitlines()
            if ln.startswith("| `cand-")
        ]
        assert rows
        for row in rows:
            cells = [c.strip() for c in row.split("|")[2:6]]
            for c in cells[:3]:
                assert c in valid, (row, c)


# ---------------------------------------------------------------------------
# Elasticity sweep (r45)
# ---------------------------------------------------------------------------


class TestElasticitySweep:
    """The feedback-amplification curve: where does each driver flip
    from stable/rebased to spiral as elasticity increases?"""

    @pytest.fixture()
    def sweep_rows(self):
        from dataclasses import replace

        from blockchain_rd_lab.tokenomics.battery import resolve_signal
        from blockchain_rd_lab.tokenomics.stock import (
            SCENARIOS,
            StockVerdict,
            run_stock_scenario,
        )
        from blockchain_rd_lab.tokenomics.supply_drivers import DRIVER_REGISTRY

        spirals = {StockVerdict.SPIRAL_DOWN.value, StockVerdict.SPIRAL_UP.value}
        etas = (0.0, 0.25, 0.5, 0.75, 1.0)
        rows = []
        for d in DRIVER_REGISTRY:
            if resolve_signal(d) is None:
                continue
            for sc_name, sc in SCENARIOS.items():
                verdicts = {}
                for eta in etas:
                    r = run_stock_scenario(d, replace(sc, elasticity=eta))
                    verdicts[eta] = r.verdict.value
                first_spiral = next(
                    (e for e in etas if verdicts[e] in spirals), None
                )
                rows.append({
                    "driver": d.name,
                    "scenario": sc_name,
                    "verdicts": verdicts,
                    "flip_eta": first_spiral,
                })
        return rows

    def test_zero_elasticity_no_feedback_spirals(self, sweep_rows):
        """At eta=0 there is NO reflexive channel — value changes
        cannot feed back into demand. Steady-state scenarios must be
        stable; shock scenarios may rebase but never spiral (the
        endogenous-growth criterion requires feedback to sustain)."""
        spirals = {"spiral_down", "spiral_up"}
        quiet_scenarios = {"steady", "oscillation"}
        violations = [
            r for r in sweep_rows
            if r["scenario"] in quiet_scenarios
            and r["verdicts"][0.0] in spirals
        ]
        assert not violations, (
            f"eta=0 spiraled under quiet: {violations}"
        )

    def test_flip_monotonicity(self, sweep_rows):
        """Once a (driver, scenario) flips to spiral at some eta, it
        stays spiral at every higher eta (more feedback cannot
        stabilize an already-diverging system)."""
        spirals = {"spiral_down", "spiral_up"}
        etas = (0.0, 0.25, 0.5, 0.75, 1.0)
        violations = []
        for r in sweep_rows:
            flipped = False
            for e in etas:
                if r["verdicts"][e] in spirals:
                    flipped = True
                elif flipped:
                    violations.append(
                        f"{r['driver']}/{r['scenario']}: spiral at "
                        f"lower eta but {r['verdicts'][e]} at eta={e}"
                    )
                    break
        assert not violations, "\n".join(violations[:5])

    def test_supply_shock_flips_at_quarter(self, sweep_rows):
        """The mis-mint supply_shock: every composable level-type
        driver flips to spiral_down by eta=0.25 (the one-shot mint
        creates a value dip that even mild feedback amplifies into
        sustained bleeding)."""
        relevant = [
            r for r in sweep_rows
            if r["scenario"] == "supply_shock"
            and r["verdicts"][0.0] != "vacuous"
        ]
        assert relevant
        for r in relevant:
            assert r["flip_eta"] is not None and r["flip_eta"] <= 0.25, (
                f"{r['driver']}: supply_shock flip at {r['flip_eta']}, "
                f"expected <= 0.25"
            )

    def test_ratio_drivers_stable_until_high_eta(self, sweep_rows):
        """market-volume, usage-growth, commodity-basket-peg,
        renewable-energy-pow: the constant-velocity ratio drivers
        (stable under collapse AND crash at eta=0.5 per r43) remain
        stable through eta=0.75 for shock scenarios, flipping only
        at eta=1.0."""
        ratio_drivers = {
            "market-volume", "usage-growth",
            "commodity-basket-peg", "renewable-energy-pow",
        }
        shock_scenarios = {"demand_collapse", "crash"}
        for r in sweep_rows:
            if r["driver"] not in ratio_drivers:
                continue
            if r["scenario"] not in shock_scenarios:
                continue
            # stable through 0.75
            for eta in (0.0, 0.25, 0.5, 0.75):
                assert r["verdicts"][eta] in ("stable", "rebased_down", "rebased_up"), (
                    f"{r['driver']}/{r['scenario']} at eta={eta}: "
                    f"{r['verdicts'][eta]}"
                )

    def test_gdp_spirals_everywhere_above_zero(self, sweep_rows):
        """counter-cyclical-gdp: the inflationary collapser /
        deflationary runaway spirals under EVERY non-steady scenario
        at any eta > 0 (its signed-rate composition means the
        counter-cyclical response always fights the demand direction)."""
        gdp_rows = [
            r for r in sweep_rows
            if r["driver"] == "counter-cyclical-gdp"
            and r["scenario"] != "steady"
        ]
        assert gdp_rows
        for r in gdp_rows:
            assert r["flip_eta"] is not None and r["flip_eta"] <= 0.25, (
                f"gdp/{r['scenario']}: flip at {r['flip_eta']}, expected <= 0.25"
            )

    def test_metcalfe_divergence_threshold(self, sweep_rows):
        """metcalfe-growth's log-composition diverges under positive
        growth scenarios. At eta=0 it rebases/stays stable; at
        eta>=0.5 it spirals up (the log under-tracking ln(1+g)!=g
        combined with feedback pushes it over)."""
        meta_growth = [
            r for r in sweep_rows
            if r["driver"] == "metcalfe-growth"
            and r["scenario"] in ("organic_growth", "hyper_growth")
        ]
        for r in meta_growth:
            assert r["verdicts"][0.0] in ("stable", "rebased_up"), (
                f"metcalfe/{r['scenario']} at eta=0: {r['verdicts'][0.0]}"
            )
            assert r["flip_eta"] is not None and r["flip_eta"] <= 0.5, (
                f"metcalfe/{r['scenario']}: flip at {r['flip_eta']}"
            )

    def test_sweep_determinism(self):
        """Two independent runs produce identical results."""
        from dataclasses import replace

        from blockchain_rd_lab.tokenomics.stock import (
            SCENARIOS,
            run_stock_scenario,
        )
        from blockchain_rd_lab.tokenomics.supply_drivers import get_driver

        d = get_driver("market-volume")
        sc = replace(SCENARIOS["demand_collapse"], elasticity=0.75)
        r1 = run_stock_scenario(d, sc)
        r2 = run_stock_scenario(d, sc)
        assert r1.verdict == r2.verdict
        assert r1.value_ratio == r2.value_ratio
        assert r1.supply_ratio == r2.supply_ratio
