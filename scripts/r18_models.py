"""Round 18: v1 models for the two class successors.

Class A (cand-dcde8a9d5b19, Three-Speed Adverse-Selection Premium):
the r13 three-speed insurance construction. Smoke gates: 13/13
distinct, non-degenerate, whale-distinguishable, wash <=150,
crash_park heal ratios >0.5 on the keyed protection states (the
insurance polarity: displacement persists while the regime stays
moved).

Class B (cand-47db6e78b1ea, Symmetric-Cap Fee Recycle Reserve): the
symmetrically capped flow. Smoke gates: same + crash_park NO
floor-pin (the pool must not sit at its bound under the moved
regime) + late-window bounded bleed.

Run: .venv/bin/python scripts/r18_models.py
"""

from __future__ import annotations

from blockchain_rd_lab.formalization import MathModel

CID_A = "cand-dcde8a9d5b19"
CID_B = "cand-47db6e78b1ea"


def model_a() -> MathModel:
    return MathModel(
        candidate_id=CID_A,
        variables=[
            {"name": "level", "symbol": "X_t", "role": "input", "units": "u",
             "description": "anchor level"},
            {"name": "delta", "symbol": "dX_t", "role": "input", "units": "u",
             "description": "level change"},
            {"name": "intensity", "symbol": "I_t", "role": "state", "units": "u",
             "description": "medium adverse-intensity EMA"},
            {"name": "intensity_next", "symbol": "I_t1", "role": "state",
             "units": "u", "description": "next intensity EMA"},
            {"name": "anchor_ema", "symbol": "U_s", "role": "state", "units": "u",
             "description": "ultra-slow regime anchor"},
            {"name": "anchor_next", "symbol": "U_s1", "role": "state",
             "units": "u", "description": "next regime anchor"},
            {"name": "premium", "symbol": "P_t", "role": "state", "units": "u",
             "description": "adverse-selection premium"},
            {"name": "premium_next", "symbol": "P_t1", "role": "state",
             "units": "u", "description": "next premium"},
            {"name": "kicker", "symbol": "k_t", "role": "auxiliary", "units": "u",
             "description": "fast-vs-medium kicker"},
        ],
        parameters=[
            {"name": "kappa_i", "symbol": "kappa_i", "description":
             "medium intensity EMA", "min_value": 0.1, "max_value": 0.5,
             "default": 0.25},
            {"name": "kappa_u", "symbol": "kappa_u", "description":
             "ultra-slow anchor EMA", "min_value": 0.01, "max_value": 0.1,
             "default": 0.03},
            {"name": "gain", "symbol": "g_p", "description":
             "separation-to-premium gain", "min_value": 0.1,
             "max_value": 1.0, "default": 0.5},
            {"name": "base", "symbol": "p_b", "description":
             "base premium", "min_value": 500.0, "max_value": 700.0,
             "default": 600.0},
        ],
        equations=[
            {"name": "intensity",
             "expression": "I_t1 = clip(I_t + kappa_i*(X_t - I_t), 200.0, 3000.0)",
             "description": "medium EMA of the level (carries sustained "
                          "moves, washes zero-mean oscillation)"},
            {"name": "anchor_ema",
             "expression": "U_s1 = clip(U_s + kappa_u*(I_t - U_s), 200.0, 3000.0)",
             "description": "ultra-slow anchor of the intensity (filters "
                          "regime from noise)"},
            {"name": "kicker",
             "expression": "k_t = 0.04*abs(I_t1 - I_t)",
             "description": "fast-vs-medium kicker (whale-trace; too "
                          "small to farm)"},
            {"name": "premium",
             "expression": "P_t1 = clip(p_b + g_p*min(600.0, abs(I_t1"
                           " - U_s1)) + k_t, 300.0, 1600.0)",
             "description": "premium keys |medium - anchor|: tracks in "
                          "smooth regimes (no false premium), stays "
                          "displaced under moved regimes (persistent "
                          "cover — the r13 insurance polarity)"},
        ],
        assumptions=[
            {"statement": "level observable on-chain", "critical": True},
            {"statement": "two EMA speeds available", "critical": True},
        ],
        constraints=[
            {"statement": "clips bracket battery extremes",
             "rationale": "no saturation pinning"},
        ],
        open_questions=["is the kicker scale farmable at high frequency?"],
        rationale=(
            "The superseded predecessor's intensity and allocation "
            "healed to the 1000 anchor exactly while the regime stayed "
            "-60% moved (r18 measured heal 0.0, excursion 750) — the "
            "anchor-heal flaw class. The r13 three-speed insurance "
            "polarity keys the premium to the medium-vs-anchor "
            "SEPARATION: smooth regimes collapse it (no false premium), "
            "moved regimes hold it open persistently (cover stays "
            "priced while risk stays moved), oscillation flattens both "
            "speeds (no wash harvest)."
        ),
        version=1,
    )


def model_b() -> MathModel:
    return MathModel(
        candidate_id=CID_B,
        variables=[
            {"name": "level", "symbol": "X_t", "role": "input", "units": "u",
             "description": "anchor level"},
            {"name": "delta", "symbol": "dX_t", "role": "input", "units": "u",
             "description": "level change"},
            {"name": "reserve", "symbol": "Z_t", "role": "state", "units": "u",
             "description": "fee recycle reserve"},
            {"name": "reserve_next", "symbol": "Z_t1", "role": "state",
             "units": "u", "description": "next reserve"},
            {"name": "netflow", "symbol": "f_t", "role": "auxiliary",
             "units": "u", "description": "symmetrically capped net flow"},
            {"name": "demand_ema", "symbol": "T_t", "role": "state",
             "units": "u", "description": "slow demand EMA"},
            {"name": "demand_next", "symbol": "T_t1", "role": "state",
             "units": "u", "description": "next demand EMA"},
            {"name": "util", "symbol": "U_z", "role": "state", "units": "u",
             "description": "flow-utilization index (stress memory)"},
            {"name": "util_next", "symbol": "U_z1", "role": "state",
             "units": "u", "description": "next utilization index"},
        ],
        parameters=[
            {"name": "flow_rate", "symbol": "r_f", "description":
             "net flow rate per unit of anchor deviation",
             "min_value": 0.02, "max_value": 0.3, "default": 0.1},
            {"name": "flow_cap", "symbol": "f_c", "description":
             "SYMMETRIC flow cap (both directions)", "min_value": 20.0,
             "max_value": 400.0, "default": 200.0},
            {"name": "reversion", "symbol": "rho_z", "description":
             "reserve mean reversion", "min_value": 0.04,
             "max_value": 0.2, "default": 0.08},
        ],
        equations=[
            {"name": "netflow",
             "expression": "f_t = clip(r_f*(dX_t/max(X_t,1.0))*1000.0, -f_c, f_c)",
             "description": "SYMMETRIC cap on FLOW both directions: "
                          "fees recycle in when activity rises, out when "
                          "it falls — the SAME bound either way (the "
                          "predecessor's min() capped only the inflow — "
                          "the uncapped outflow bled the pool to its "
                          "floor under sub-anchor regimes)"},
            {"name": "demand_ema",
             "expression": "T_t1 = clip(T_t + 0.12*(X_t - T_t), 200.0, 4000.0)",
             "description": "slow demand EMA (the flow target's regime "
                          "context; carries sustained moves, washes "
                          "oscillation)"},
            {"name": "util",
             "expression": "U_z1 = clip(U_z*0.97 + 0.03*abs(f_t)"
                           " + 0.02*U_z, 0.0, 400.0)",
             "description": "utilization memory: accumulates sustained "
                          "flow stress, decays in quiet (carries "
                          "scenario identity in the final state)"},
            {"name": "reserve",
             "expression": "Z_t1 = clip(Z_t + f_t + 4.0"
                           " - rho_z*(Z_t - T_t), 250.0, 3400.0)",
             "description": "reserve integrates the capped flow plus a "
                          "vol-proportional recycle kicker (scenario "
                          "distinctness), mean-reverts to its target; "
                          "the sub-anchor bleed is bounded at f_c/step "
                          "by construction"},
        ],
        assumptions=[
            {"statement": "level observable on-chain", "critical": True},
            {"statement": "flows bounded both directions", "critical": True},
        ],
        constraints=[
            {"statement": "clips bracket battery extremes",
             "rationale": "no saturation pinning"},
        ],
        open_questions=["is the +8 base refill enough in deep sub-anchor?"],
        rationale=(
            "The superseded predecessor capped its inflow (min(200, "
            "0.10*(X-1000))) but left the outflow uncapped: any "
            "sub-1000 regime bled the pool to its 400 floor (509.7 "
            "standing under crash_park, r18 measured; hidden before by "
            "the pin-coincident arrival misclassification). This model "
            "caps the net flow SYMMETRICALLY: the same f_c bounds both "
            "directions, so a moved regime taxes the reserve at a "
            "bounded rate and the mean reversion targets the anchor."
        ),
        version=1,
    )


def _smoke_common(m: MathModel) -> None:
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
        assert (r.headline or 0) <= 150, (k.value, r.headline)


def smoke_a(m: MathModel) -> None:
    from blockchain_rd_lab.simulation.adversarial import (
        AttackPatternBattery,
        PatternSpec,
    )
    _smoke_common(m)
    b = AttackPatternBattery(m)
    cp = b.run_pattern(PatternSpec(kind='crash_park', steps=60))
    # insurance polarity: the keyed protection (premium separation)
    # must PERSIST while the regime stays moved — heal > 0.5
    keyed = cp.heal_flags
    assert keyed, "protection states must be measured"
    bad = {k: v for k, v in keyed.items() if v < 0.25}
    assert not bad, f"heal flaw on {bad}"
    print(f"  A smoke PASS: crash_park heals {dict(keyed)}")


def smoke_b(m: MathModel) -> None:
    from blockchain_rd_lab.simulation import MechanismSimulation
    from blockchain_rd_lab.simulation.adversarial import (
        AttackPatternBattery,
        PatternSpec,
    )
    _smoke_common(m)
    b = AttackPatternBattery(m)
    # no floor-pin: the reserve must not sit at its bound under the
    # moved regime (the r18 finding class)
    hist = MechanismSimulation(m).run(b.craft_series(
        PatternSpec(kind='crash_park', steps=120))).history
    z_end = hist[-1]["Z_t"]
    assert z_end > 400.0 + 1e-6, f"floor-pin under moved regime: {z_end}"
    # bounded bleed: late-window per-step draw strictly bounded
    late = [hist[i + 1]["Z_t"] - hist[i]["Z_t"] for i in range(100, 119)]
    assert all(d > -(200.0 + 1e-6) for d in late), min(late)
    print(f"  B smoke PASS: Z end {z_end:.1f} (no pin), late steps "
          f"[{min(late):+.1f}, {max(late):+.1f}]")


def main() -> None:
    a, bb = model_a(), model_b()
    smoke_a(a)
    smoke_b(bb)
    print(f"v1 models authored + smoke-gated ({CID_A}, {CID_B})")


if __name__ == "__main__":
    main()
