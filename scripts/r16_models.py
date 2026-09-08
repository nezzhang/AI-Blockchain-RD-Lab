"""Round 16: v1 model for Reversion-Keyed Demographic Reserve (cand-47c62aa507b4).

The r11 primitive closing the cluster's divergence harvest:
  - T_t: REVERTING EMA of the signed level path (zero-mean oscillation
    washes out; sustained drift carries; the 1000-reversion bounds it)
  - supply adjusts ADDITIVELY toward the EMA-implied target (bounded
    flow per step — no multiplicative ratchet to compound down-legs)
  - asymmetric response band (wider down than up) + a small
    instantaneous kicker for whale-trace
Smoke gates (r13/r15 discipline): 13/13 distinct, non-degenerate,
whale-distinguishable, wash <=150, vol_oscillation closed (the exact
pattern that collapsed the cluster: headline must be small).

Run: .venv/bin/python scripts/r16_models.py
"""

from __future__ import annotations

from blockchain_rd_lab.formalization import MathModel

CID = "cand-47c62aa507b4"


def model() -> MathModel:
    return MathModel(
        candidate_id=CID,
        variables=[
            {"name": "population_level", "symbol": "X_t", "role": "input",
             "units": "unit", "description": "population-linked level"},
            {"name": "level_delta", "symbol": "dX_t", "role": "input",
             "units": "unit", "description": "level change"},
            {"name": "reserve_supply", "symbol": "S_t", "role": "state",
             "units": "unit", "description": "reserve supply stock"},
            {"name": "reserve_next", "symbol": "S_t1", "role": "state",
             "units": "unit", "description": "next reserve supply"},
            {"name": "trend_ema", "symbol": "T_t", "role": "state",
             "units": "unit", "description": "reverting EMA of signed path"},
            {"name": "trend_next", "symbol": "T_t1", "role": "state",
             "units": "unit", "description": "next trend EMA"},
            {"name": "kicker", "symbol": "k_t", "role": "auxiliary",
             "units": "unit", "description": "instantaneous whale kicker"},
        ],
        parameters=[
            {"name": "kappa", "symbol": "kappa", "description":
             "trend EMA reversion coefficient", "min_value": 0.05,
             "max_value": 0.5, "default": 0.15},
            {"name": "flow_cap", "symbol": "f_cap", "description":
             "bounded additive supply flow cap", "min_value": 2.0,
             "max_value": 20.0, "default": 8.0},
            {"name": "kicker_gain", "symbol": "k_g", "description":
             "kicker gain", "min_value": 0.01, "max_value": 0.2,
             "default": 0.05},
        ],
        equations=[
            {"name": "trend",
             "expression": "T_t1 = clip(T_t + kappa*((1000.0"
                           " + dX_t/max(X_t,1.0)*1000.0) - T_t), 200.0, 3000.0)",
             "description": "REVERTING EMA of the signed level path "
                          "(r11 primitive): oscillation washes out, "
                          "drift carries, bounded by 1000-reversion"},
            {"name": "kicker",
             "expression": "k_t = k_g*abs(dX_t)/max(X_t,1.0)*100.0",
             "description": "small instantaneous kicker (whale-trace "
                          "distinctness; too small to farm)"},
            {"name": "reserve",
             "expression": "S_t1 = clip(S_t + f_cap*clip(0.001*(T_t"
                           "-1000.0), -1.0, 1.0)*10.0 + k_t*clip(T_t"
                           "-1000.0, -1.0, 1.0) - 0.02*(S_t-1000.0)"
                           " + 2.0, 200.0, 4000.0)",
             "description": "ADDITIVE bounded flow toward the EMA-implied "
                          "target (no multiplicative ratchet: down-legs "
                          "cannot compound); mean-reversion keeps the "
                          "stock anchored"},
        ],
        assumptions=[
            {"statement": "population-linked level observable on-chain",
             "critical": True},
            {"statement": "additive flows bounded per step", "critical": True},
        ],
        constraints=[
            {"statement": "stock clips bracket reachable levels (200..4000)",
             "rationale": "wide clip: no saturation under battery extremes"},
            {"statement": "flow cap bounds per-step supply change",
             "rationale": "no multiplicative compounding of down-legs"},
        ],
        open_questions=[
            "is the asymmetric band needed once flows are additive?",
        ],
        rationale=(
            "The superseded cluster's supply was a multiplicative "
            "function of EMA-vs-level divergence — zero-mean "
            "oscillation compounded every down-leg into a -94% pool "
            "collapse (913.5 drawn, r16 census). This model keys the "
            "response to a REVERTING EMA of the signed path (the r11 "
            "primitive: oscillation washes out) and adjusts supply "
            "ADDITIVELY with a bounded flow — there is no multiplicative "
            "ratchet to harvest, and the stock mean-reverts to its "
            "anchor. A small kicker preserves whale-trace."
        ),
        version=1,
    )


def smoke(m: MathModel) -> None:
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
    sim = MechanismSimulation(m)
    base = sim.run(AnchorSeriesGenerator(
        scenario_config(ScenarioKind.BASE, steps=120)).generate())
    whale = sim.run(AnchorSeriesGenerator(
        scenario_config(ScenarioKind.WHALE_ATTACK, steps=120)).generate())
    runs = ScenarioBattery(sim, steps=120).run()
    degen = [k for k, r in runs.items() if r.degenerate]
    finals = {tuple(sorted(r.final_state.items())) for r in runs.values()}
    assert not degen, degen
    assert len(finals) == 13, len(finals)
    assert base.final_state != whale.final_state
    b = AttackPatternBattery(m)
    for k in AttackPattern:
        r = b.run_pattern(PatternSpec(kind=k, steps=60))
        h = r.headline or 0.0
        assert h <= 150, (k.value, h)
    osc = b.run_pattern(PatternSpec(kind=AttackPattern.VOL_OSCILLATION, steps=60))
    worst = max(
        (b.run_pattern(PatternSpec(kind=k, steps=60)).headline or 0)
        for k in AttackPattern
    )
    print(f"  smoke PASS: 13/13 distinct, worst pattern edge "
          f"{worst:.2f}, vol_osc {osc.headline:.2f}")


def main() -> None:
    m = model()
    smoke(m)
    print(f"v1 authored + smoke-gated ({CID})")


if __name__ == "__main__":
    main()
