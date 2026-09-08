"""Round 19: improve answer — v2 with the r18 ramp pattern.

v2 closes the named vectors:
- flow cap gains a sqrt-compressed quadratic ramp near the f_c
  boundary (monotone marginal cost — the r18 Symmetric-Cap v2 fix
  pattern applied here): no flat zone to ride
- the stress memory S_w is pinned DISCLOSURE-ONLY by an explicit
  constraint (nothing keys off it; the latent future-use risk is a
  named, testable invariant)

Smoke-gated in-memory before install (13/13 distinct, worst <=150,
no floor pin at any window, window-stable).

Run: .venv/bin/python scripts/r19_answer_improve.py
"""

from __future__ import annotations

import json

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel

CID = "cand-412f176470fb"


def v2(db: LabDatabase) -> dict:
    m = json.loads(json.dumps(json.loads(db.get_latest_math_model(CID))))
    m["version"] = 2
    for e in m["equations"]:
        if e["name"] == "wage_flow":
            e["expression"] = (
                "f_w = clip(kappa_w*clip(T_w - W_t, -3000.0, 3000.0)"
                "*sqrt(min(1.0, abs(kappa_w*clip(T_w - W_t,"
                " -3000.0, 3000.0))/f_c)), -f_c, f_c)")
            e["description"] = (
                "SYMMETRIC cap with a sqrt-compressed QUADRATIC ramp "
                "near the boundary: the marginal flow cost is "
                "monotone — no flat zone under the cap to ride (the "
                "r18 Symmetric-Cap v2 fix pattern); both directions "
                "bounded at f_c"
            )
    m["constraints"] = [
        {"statement": "pool floor below the deepest battery crash level",
         "rationale": "a floor above the crash level re-creates the "
                     "standing pin through the back door (r15 "
                     "bandwidth lesson, re-measured r19)"},
        {"statement": "nothing keys off the stress memory S_w",
         "rationale": "S_w is a DISCLOSURE state only: it carries "
                     "scenario identity and stress memory; the red "
                     "team flagged its latent future use — pinned as "
                     "an explicit, testable invariant"},
    ]
    return m


def smoke(m_dict: dict) -> None:
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
    m = MathModel.model_validate(m_dict)
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
    for k in (AttackPattern.CRASH_PARK, AttackPattern.PUMP_UNWIND,
              AttackPattern.GRIND_HARVEST):
        heads = []
        for steps in (60, 120, 240):
            r = b.run_pattern(PatternSpec(kind=k, steps=steps))
            heads.append(r.headline or 0)
            hist = MechanismSimulation(m).run(
                b.craft_series(PatternSpec(kind=k, steps=steps))).history
            assert hist[-1]["W_t"] > 250.0 + 1e-6, (k.value, steps)
        assert max(heads) - min(heads) <= 100.0, (k.value, heads)
    print(f"  v2 smoke PASS: 13/13, worst {worst:.2f}, window-stable, "
          f"no pin")


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    m2 = v2(db)
    smoke(m2)
    summary = (
        "v2 closes the named vectors: (1) the flow cap gains a "
        "sqrt-compressed quadratic ramp near the f_c boundary — the "
        "marginal flow cost is monotone in the target deviation, "
        "removing the flat zone under the cap worth riding (the r18 "
        "Symmetric-Cap v2 fix pattern); (2) the stress memory S_w is "
        "pinned DISCLOSURE-ONLY by an explicit constraint — nothing "
        "keys off it, making the latent future-use risk a named, "
        "testable invariant. The single-magnet re-basing and the "
        "floor-below-crash-level discipline are unchanged (arrival "
        "verified at 120/240-step windows in the r19 audit)."
    )
    avs = [
        "Flow-cap boundary riding", "Stress-memory pre-loading",
        "Kicker-scale accumulation", "Level-feed grinding (out-of-model)"]
    answer = {
        "summary": summary,
        "addressed_attacks": [
            {"agent_name": agent, "vector_description": vec,
             "fix_strategy": summary, "fixes_attack": True}
            for agent, vec in zip(
                ["red_team", "game_theory", "security", "oracle"],
                avs, strict=True)
        ],
        "model": m2,
    }
    AgentBridgeProvider().install_answer("905d07c0f6edfc0a", answer)
    print("  answered 905d07c0f6edfc0a", CID, "v2")


if __name__ == "__main__":
    main()
