"""Round 19: v1 model + smoke gates for the wage-pool successor.

Gates (r12/r15/r18 discipline): 13/13 distinct finals, non-degenerate,
whale-distinguishable, pattern worst <=150, floor NOT pinned under
crash_park at ANY window (60/120/240 — the r19 audit's own probe:
the flaw this successor fixes only appears at longer windows), and
no window-flip >100 across the park-style patterns.

Run: .venv/bin/python scripts/r19_models.py
"""

from __future__ import annotations

from blockchain_rd_lab.formalization import MathModel

CID = "cand-412f176470fb"


def model_v1() -> MathModel:
    return MathModel(
        candidate_id=CID,
        variables=[
            {"name": "level", "symbol": "X_t", "role": "input", "units": "u",
             "description": "anchor level"},
            {"name": "delta", "symbol": "dX_t", "role": "input", "units": "u",
             "description": "level change"},
            {"name": "wage_pool", "symbol": "W_t", "role": "state", "units": "u",
             "description": "compute wage pool"},
            {"name": "wage_next", "symbol": "W_t1", "role": "state",
             "units": "u", "description": "next wage pool"},
            {"name": "regime_ema", "symbol": "T_w", "role": "state",
             "units": "u", "description": "slow regime EMA (single magnet)"},
            {"name": "regime_next", "symbol": "T_w1", "role": "state",
             "units": "u", "description": "next regime EMA"},
            {"name": "wage_flow", "symbol": "f_w", "role": "auxiliary",
             "units": "u", "description": "symmetrically capped wage flow"},
            {"name": "stress", "symbol": "S_w", "role": "state", "units": "u",
             "description": "delivery-stress memory (disclosure state)"},
            {"name": "stress_next", "symbol": "S_w1", "role": "state",
             "units": "u", "description": "next stress memory"},
        ],
        parameters=[
            {"name": "pool_tracking", "symbol": "kappa_w",
             "description": "pool tracking of the regime EMA",
             "min_value": 0.05, "max_value": 0.4, "default": 0.15},
            {"name": "regema_speed", "symbol": "kappa_t",
             "description": "regime EMA speed", "min_value": 0.05,
             "max_value": 0.3, "default": 0.12},
            {"name": "flow_cap", "symbol": "f_c", "description":
             "symmetric wage-flow cap", "min_value": 20.0,
             "max_value": 200.0, "default": 60.0},
        ],
        equations=[
            {"name": "regime_ema",
             "expression": "T_w1 = clip(T_w + kappa_t*clip(X_t - T_w,"
                           " -500.0, 500.0), 100.0, 9000.0)",
             "description": "slow re-centering EMA of the level with a "
                          "BOUNDED STEP (±500): the pool's single "
                          "magnet tracks any level scale (battery "
                          "extremes reach 700k — a value-clipped EMA "
                          "would saturate) while the per-step move "
                          "stays bounded; carries sustained moves, "
                          "washes oscillation"},
            {"name": "wage_flow",
             "expression": "f_w = clip(kappa_w*clip(T_w - W_t,"
                           " -3000.0, 3000.0), -f_c, f_c)",
             "description": "SYMMETRIC flow cap toward the regime "
                          "target — the same bound both directions "
                          "(the r18 symmetric-cap discipline)"},
            {"name": "stress",
             "expression": "S_w1 = clip(S_w*0.97 + 0.05*abs(dX_t)"
                           " + 0.02*S_w, 0.0, 300.0)",
             "description": "delivery-stress memory: accumulates "
                          "sustained |dX|, decays in quiet — carries "
                          "scenario identity; DISCLOSURE-ONLY (nothing "
                          "keys off it; the r18 U_z discipline)"},
            {"name": "wage_pool",
             "expression": "W_t1 = clip(W_t + f_w"
                           " + 6.0*abs(dX_t)/max(X_t,1.0), 250.0, 4000.0)",
             "description": "pool integrates the capped flow + a "
                          "delivery kicker (whale-trace); FLOOR 250 "
                          "sits BELOW the deepest battery crash "
                          "level 400 — the pool re-bases to the moved "
                          "regime instead of pinning above it (the "
                          "r15/r19 fix discipline)"},
        ],
        assumptions=[
            {"statement": "level observable on-chain", "critical": True},
            {"statement": "flows bounded both directions", "critical": True},
        ],
        constraints=[
            {"statement": "pool floor below the deepest battery crash level",
             "rationale": "a floor above the crash level re-creates "
                         "the standing pin through the back door "
                         "(r15 bandwidth lesson, re-measured r19)"},
        ],
        open_questions=["is the delivery kicker scale farmable at high frequency?"],
        rationale=(
            "The superseded predecessor's wage pool floor (600) sat "
            "above the -60% crash level (400): the symmetric flow cap "
            "was correct but the floor blocked re-basing, pinning the "
            "pool at 600 under the moved regime (400 standing at "
            "120/240-step windows, r19 measured). This model gives the "
            "pool a single magnet (a slow regime EMA), keeps the "
            "symmetric cap, and drops the floor to 250 — below the "
            "crash level — so the pool reaches the moved regime and "
            "the excursion is the re-basing itself."
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
    worst = 0.0
    for k in AttackPattern:
        r = b.run_pattern(PatternSpec(kind=k, steps=60))
        worst = max(worst, r.headline or 0)
        assert (r.headline or 0) <= 150, (k.value, r.headline)
    # the r19 window-robustness probe: park-style patterns at
    # 60/120/240 — no floor pin at ANY window, no classification flip
    for k in (AttackPattern.CRASH_PARK, AttackPattern.PUMP_UNWIND,
              AttackPattern.GRIND_HARVEST):
        heads = []
        for steps in (60, 120, 240):
            r = b.run_pattern(PatternSpec(kind=k, steps=steps))
            heads.append(r.headline or 0)
            hist = MechanismSimulation(m).run(
                b.craft_series(PatternSpec(kind=k, steps=steps))).history
            w_end = hist[-1]["W_t"]
            assert w_end > 250.0 + 1e-6, (
                f"{k.value}@{steps}: floor pin at {w_end}")
        flip = max(heads) - min(heads)
        assert flip <= 100.0, (k.value, heads)
    print(f"  smoke PASS: 13/13, worst {worst:.2f}, window-stable, "
          f"no floor pin")


def main() -> None:
    m = model_v1()
    smoke(m)
    print(f"v1 authored + smoke-gated ({CID})")


if __name__ == "__main__":
    main()
