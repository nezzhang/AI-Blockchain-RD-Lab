"""Round 15: the v1 model for the Level-Recentered Bandwidth Bond Market.

Single-magnet construction: C_t follows a slow EMA of the level
(wide clip, no saturation); the stress signal s_t keys |X_t - C_t|
(which closes after any permanent shift as C re-bases); the slash
chi*s*300 fires only during the re-basing transient; A_t weights
0.5*E + 0.5*C so the allocation tracks the re-based pool.

Smoke gates (r13/r15 discipline): 13/13 distinct, non-degenerate,
whale-distinguishable, wash <=150, crash_park heal semantics — the
C_t excursion is REGIME TRACKING (the pool re-basing), and the
transient slash must BOUND (no standing burn at the parked window's
end: |X - C| deviation closes below the s_t threshold).

Run: .venv/bin/python scripts/r15_models.py
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
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

CID = "cand-6fea4a5332ca"


def model(db: LabDatabase) -> MathModel:
    return MathModel(
        candidate_id=CID,
        variables=[
            {"name": "bandwidth_level", "symbol": "X_t", "role": "input",
             "units": "unit", "description": "bandwidth level"},
            {"name": "bandwidth_delta", "symbol": "dX_t", "role": "input",
             "units": "unit", "description": "level change"},
            {"name": "collateral", "symbol": "C_t", "role": "state",
             "units": "unit", "description": "collateral pool (level EMA)"},
            {"name": "collateral_next", "symbol": "C_t1", "role": "state",
             "units": "unit", "description": "next collateral pool"},
            {"name": "stress", "symbol": "s_t", "role": "auxiliary",
             "units": "unit", "description": "transient stress signal"},
            {"name": "escrow_demand", "symbol": "E_t", "role": "state",
             "units": "unit", "description": "posted escrow demand"},
            {"name": "escrow_next", "symbol": "E_t1", "role": "state",
             "units": "unit", "description": "next escrow demand"},
            {"name": "relay_allocation", "symbol": "A_t", "role": "state",
             "units": "unit", "description": "relay allocation"},
            {"name": "relay_next", "symbol": "A_t1", "role": "state",
             "units": "unit", "description": "next relay allocation"},
        ],
        parameters=[
            {"name": "kappa_c", "symbol": "kappa_c", "description":
             "pool level-EMA coefficient (the single magnet)",
             "min_value": 0.05, "max_value": 0.4, "default": 0.18},
            {"name": "slash_chi", "symbol": "chi", "description":
             "transient stress slash rate", "min_value": 0.05,
             "max_value": 0.5, "default": 0.2},
            {"name": "delta_e", "symbol": "delta_e", "description":
             "escrow demand EMA", "min_value": 0.05, "max_value": 0.5,
             "default": 0.2},
        ],
        equations=[
            {"name": "collateral",
             "expression": "C_t1 = clip(C_t + kappa_c*(X_t - C_t)"
                           " - chi*s_t*300.0, 250.0, 3000.0)",
             "description": "SINGLE-MAGNET pool: slow EMA of the level; "
                          "the slash subtracts but the EMA always "
                          "pulls C toward X — the deviation closes "
                          "after any permanent shift (no anchor tug)"},
            {"name": "stress",
             "expression": "s_t = sqrt(max(0.0, abs(X_t - C_t)/max(X_t,1.0)"
                           " - 0.05))",
             "description": "transient stress: the pool-level deviation "
                          "ABOVE tolerance — fires during the re-basing "
                          "window, closes when C reaches the new level"},
            {"name": "escrow_demand",
             "expression": "E_t1 = clip(E_t*(1-delta_e) + delta_e*(1000.0"
                           " + 250.0*abs(dX_t)/max(X_t,1.0)), 500.0, 2200.0)",
             "description": "escrow demand follows volatility"},
            {"name": "relay_allocation",
             "expression": "A_t1 = clip(0.5*E_t1 + 0.5*C_t1"
                           " + 60.0*s_t*3.0, 400.0, 2000.0)",
             "description": "allocation weights escrow demand and the "
                          "re-based pool (tracks the level; no eternal "
                          "relative enrichment)"},
        ],
        assumptions=[
            {"statement": "bandwidth level observable on-chain",
             "critical": True},
            {"statement": "pool re-bases within the shift window",
             "critical": True},
        ],
        constraints=[
            {"statement": "pool clips bracket reachable levels (450..3000)",
             "rationale": "wide clip: no saturation under battery extremes"},
            {"statement": "slash bounded to the re-basing transient",
             "rationale": "the stress deviation closes as the pool re-bases"},
        ],
        open_questions=[
            "is kappa_c fast enough that the slash window is strictly "
            "shorter than the escrow cycle?",
        ],
        rationale=(
            "The predecessor's pool was caught between two magnets — "
            "1000-mean-reversion and level-tracking — so under a "
            "permanent shift it settled 22% from the level and the "
            "stress slash burned forever (r15 measured: C_t drawn "
            "179.24, standing 17.7/step, A/C doubling). This model "
            "gives the pool ONE magnet: a slow EMA of the level. The "
            "stress signal keys the pool-level deviation, which now "
            "closes after any shift as C re-bases — the slash is "
            "bounded to the re-basing transient, and the allocation "
            "tracks the re-based pool rather than being enriched by "
            "an eternal burn."
        ),
        version=1,
    )


def smoke(m: MathModel) -> None:
    sim = MechanismSimulation(m)
    base_cfg = scenario_config(ScenarioKind.BASE, steps=120)
    base = sim.run(AnchorSeriesGenerator(base_cfg).generate())
    whale_cfg = scenario_config(ScenarioKind.WHALE_ATTACK, steps=120)
    whale = sim.run(AnchorSeriesGenerator(whale_cfg).generate())
    runs = ScenarioBattery(sim, steps=120).run()
    degen = [k for k, r in runs.items() if r.degenerate]
    finals = {tuple(sorted(r.final_state.items())) for r in runs.values()}
    wash = AttackPatternBattery(m).run_pattern(
        PatternSpec(kind=AttackPattern.WASH_FLOW, steps=60))
    cp = AttackPatternBattery(m).run_pattern(
        PatternSpec(kind=AttackPattern.CRASH_PARK, steps=60))
    assert not degen, degen
    assert len(finals) == 13, f"only {len(finals)} distinct"
    assert base.final_state != whale.final_state
    assert not wash.vacuous and (wash.headline or 0) <= 150, wash.headline
    # the r15 gates: NO standing drain under park — the pool re-bases
    # (excursion classified as regime tracking) and the stress closes
    assert "C_t_drawn" in cp.regime_tracking, (
        f"pool excursion should classify as regime tracking: {cp.edge}"
    )
    # stress closes: run the long-window check directly
    hist = MechanismSimulation(m).run(
        AttackPatternBattery(m).craft_series(
            PatternSpec(kind=AttackPattern.CRASH_PARK, steps=240))).history
    late = [h["s_t"] for h in hist[-20:]]
    assert max(late) < 0.1, (
        f"stress must close after re-basing; late-window s_t {max(late):.3f}"
    )
    print(f"  smoke PASS: 13/13 distinct, wash {wash.headline:.2f}, "
          f"crash_park pool=regime-tracking, late s_t {max(late):.4f}")


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    m = model(db)
    smoke(m)
    print(f"v1 model authored + smoke-gated ({CID}; formalize answer "
          "carries it to the DB)")


if __name__ == "__main__":
    main()
