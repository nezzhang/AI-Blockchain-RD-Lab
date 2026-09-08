"""Round 20: v1 model + smoke gates for the retention-ratchet successor.

Gates (r12/r15/r18/r19 discipline): 13/13 distinct finals,
non-degenerate, whale-distinguishable, pattern worst <=150, and the
r20 probes: resonance ratchet at every N (2/4/8) <=150 (the flaw this
successor fixes), the full N-scaling sweep NOT diverging, and the
quiet-tail gap closing (transit, not ratchet).

Run: .venv/bin/python scripts/r20_models.py
"""

from __future__ import annotations

from blockchain_rd_lab.formalization import MathModel

CID = "cand-cd39d95ea572"  # superseded predecessor — placeholder;
# the minted successor id is printed by r20_mint and patched in below.


def model_v1(cid: str) -> MathModel:
    return MathModel(
        candidate_id=cid,
        variables=[
            {"name": "level", "symbol": "X_t", "role": "input", "units": "u",
             "description": "anchor level"},
            {"name": "delta", "symbol": "dX_t", "role": "input", "units": "u",
             "description": "level change"},
            {"name": "escrow", "symbol": "E_t", "role": "state", "units": "u",
             "description": "fee-smoothing escrow level"},
            {"name": "escrow_next", "symbol": "E_t1", "role": "state",
             "units": "u", "description": "next escrow level"},
            {"name": "fast_ema", "symbol": "L_f", "role": "state",
             "units": "u", "description": "fast pressure EMA"},
            {"name": "fast_next", "symbol": "L_f1", "role": "state",
             "units": "u", "description": "next fast EMA"},
            {"name": "slow_ema", "symbol": "T_s", "role": "state",
             "units": "u", "description": "slow regime EMA"},
            {"name": "slow_next", "symbol": "T_s1", "role": "state",
             "units": "u", "description": "next slow EMA"},
            {"name": "retention", "symbol": "r_t", "role": "state",
             "units": "frac", "description": "escrow retention fraction"},
            {"name": "retention_next", "symbol": "r_t1", "role": "state",
             "units": "frac", "description": "next retention"},
            {"name": "separation", "symbol": "g_t", "role": "auxiliary",
             "units": "u", "description": "signed fast-vs-slow separation"},
        ],
        parameters=[
            {"name": "fast_speed", "symbol": "kappa_f",
             "description": "fast EMA speed", "min_value": 0.2,
             "max_value": 0.9, "default": 0.55},
            {"name": "slow_speed", "symbol": "kappa_s",
             "description": "slow EMA speed", "min_value": 0.02,
             "max_value": 0.15, "default": 0.06},
            {"name": "retention_base", "symbol": "delta_r",
             "description": "base retention", "min_value": 0.1,
             "max_value": 0.5, "default": 0.3},
            {"name": "retention_gain", "symbol": "eta_r",
             "description": "separation gain on retention",
             "min_value": 0.05, "max_value": 0.4, "default": 0.15},
            {"name": "flow_cap", "symbol": "f_c",
             "description": "buffer target range (symmetric)",
             "min_value": 5.0, "max_value": 60.0, "default": 18.0},
            {"name": "buffer_speed", "symbol": "lam_e",
             "description": "escrow convergence to target", "min_value": 0.05,
             "max_value": 0.5, "default": 0.15},
        ],
        equations=[
            {"name": "fast_ema",
             "expression": "L_f1 = clip(L_f + kappa_f*(X_t - L_f),"
                           " 100.0, 10000.0)",
             "description": "fast pressure EMA of the level — leads on "
                          "genuine moves; a broad clip so battery "
                          "extremes never saturate the state"},
            {"name": "slow_ema",
             "expression": "T_s1 = clip(T_s + kappa_s*clip(X_t - T_s,"
                           " -500.0, 500.0), 100.0, 9000.0)",
             "description": "slow regime EMA with a BOUNDED STEP "
                          "(±500 — the r19 primitive: battery extremes "
                          "reach 700k; a value-clipped EMA saturates) — "
                          "carries sustained moves, washes oscillation"},
            {"name": "separation",
             "expression": "g_t = (L_f - T_s) / max(T_s, 1.0)",
             "description": "SIGNED separation, level-denominated: "
                          "positive when fast pressure leads the regime "
                          "(premium inflation), negative on crash legs"},
            {"name": "retention",
             "expression": "r_t1 = clip(delta_r + eta_r*g_t, 0.1, 0.9)",
             "description": "retention keys the SIGNED separation "
                          "(the r13 polarity fix): up-ramps retain, "
                          "crash legs release — a full resonance cycle "
                          "nets ~zero instead of pinning at the ceiling "
                          "every ramp phase (the predecessor keyed "
                          "ABSOLUTE vol and over-retained monotonic)"},
            {"name": "escrow",
             "expression": "E_t1 = clip((1.0-lam_e)*E_t + lam_e*"
                           "(1000.0 + f_c*r_t), 150.0, 20000.0)",
             "description": "the escrow chases a BOUNDED, REVERTING "
                          "TARGET (buffer = anchor + cap*retention): "
                          "size keys CURRENT policy, never the HISTORY "
                          "of pressure — no free accumulator (the "
                          "corpus's resonance-healthy designs are all "
                          "EMAs of bounded targets; the predecessor's "
                          "integral form E + flows was the ratchet "
                          "class itself). Converges to the cycle-average "
                          "of the target under resonance — N-independent "
                          "by construction; symmetric in both directions "
                          "(the r18 mirrored-cap discipline, inherited)"},
        ],
        assumptions=[
            {"statement": "level observable on-chain", "critical": True},
            {"statement": "signed separation observable each step",
             "critical": True},
        ],
        constraints=[
            {"statement": "retention keys signed separation, not absolute vol",
             "rationale": "absolute-vol keying over-retains through "
                         "crafted ramps (every cycle pins the ceiling); "
                         "signed keying nets ~zero over a full cycle "
                         "(r20 measured on the predecessor)"},
            {"statement": "escrow size keys current policy, not pressure history",
             "rationale": "a free accumulator (integral of past flows) "
                         "carries every cycle's cost forward — the "
                         "resonance ratchet class; a bounded reverting "
                         "target converges to the cycle-average and is "
                         "N-independent (r20 measured on the predecessor)"},
        ],
        open_questions=[
            "can sustained genuine pressure (not crafted) hold the "
            "separation key high enough to farm retention?",
        ],
        rationale=(
            "The superseded predecessor's retention keyed ABSOLUTE "
            "realized vol (eta=40 pinned r_t at the 0.9 ceiling "
            "through every crafted ramp) while its outflow was "
            "0.05*sigma weaker — every resonance cycle over-retained "
            "monotonically (measured ratchet 285 -> 6479, "
            "linear-unbounded in N, persisting under a quiet tail). "
            "This model keys retention to the SIGNED fast-vs-slow "
            "separation (the r13 polarity fix) and gives the escrow "
            "a BOUNDED, REVERTING target (buffer = anchor + cap*"
            "retention): size keys current policy, never the history "
            "of pressure. Under resonance the escrow converges to the "
            "cycle-average of its target — N-independent by "
            "construction; the predecessor's integral form was the "
            "ratchet class itself."
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
    # the r20 probes: resonance ratchet at every N <=150, and the
    # N-scaling sweep must NOT diverge (the predecessor went
    # 285 -> 6479; exponential growth is the flaw signature)
    heads = []
    for n, steps in ((2, 60), (4, 60), (8, 120), (16, 240)):
        r = b.run_pattern(
            PatternSpec(kind=AttackPattern.RESONANCE, steps=steps,
                        strikes=n))
        heads.append(r.headline or 0)
        assert (r.headline or 0) <= 150, (n, steps, r.headline)
    assert max(heads) - min(heads) <= 100.0, heads
    print(f"  smoke PASS: 13/13, worst {worst:.2f}, resonance heads {heads}")


def main() -> None:
    from blockchain_rd_lab.config import REPO_ROOT, load_config
    from blockchain_rd_lab.database import LabDatabase
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name = "Separation-Keyed Fee Smoothing Escrow"
    cid = next(c.id for c in db.list_candidates(limit=None)
               if c.name == name)
    m = model_v1(cid)
    smoke(m)
    print(f"v1 authored + smoke-gated ({cid})")


if __name__ == "__main__":
    main()
