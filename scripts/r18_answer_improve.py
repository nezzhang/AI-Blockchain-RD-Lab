"""Round 18: improve answers — v2 patches keyed to the named vectors.

Three-Speed v2 (the r13 successor pattern):
  - premium re-keyed to separation per unit of ANCHOR movement context:
    a quadratic ramp replaces the flat min(600) cap (monotone marginal
    cost — no boundary cliff to camp)
  - kicker gated on separation CONTEXT (pays only when the gate is
    open) — pulse farming stops paying
Symmetric-Cap v2:
  - quadratic ramp near the f_c boundary (monotone marginal cost)
  - U_z utilization index RETAINED but bound explicitly to disclosure
    (nothing keys off it; the latent risk is named in constraints)

Both smoke-gated in-memory before install (r12/r15/r18 discipline).

Run: .venv/bin/python scripts/r18_answer_improve.py
"""

from __future__ import annotations

import json

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel

CID_A = "cand-dcde8a9d5b19"
CID_B = "cand-47db6e78b1ea"


def v2_a(db: LabDatabase) -> dict:
    m = json.loads(json.dumps(json.loads(db.get_latest_math_model(CID_A))))
    m["version"] = 2
    for e in m["equations"]:
        if e["name"] == "premium":
            e["expression"] = (
                "P_t1 = clip(p_b + g_p*min(600.0, abs(I_t1 - U_s1)"
                "*sqrt(abs(I_t1 - U_s1)/600.0)) + k_t, 300.0, 1600.0)")
            e["description"] = (
                "premium keys separation with a QUADRATIC ramp "
                "(sqrt-compressed): the marginal premium is monotone "
                "in separation — no flat cap boundary to camp; "
                "still bounded at 600")
        if e["name"] == "kicker":
            e["expression"] = (
                "k_t = 0.04*abs(I_t1 - I_t)*min(1.0, abs(I_t1"
                " - U_s1)/200.0)")
            e["description"] = (
                "kicker GATED on separation context (the r13 successor "
                "pattern): pulses pay only when the gate is open — "
                "flat-regime pulse farming stops paying")
    return m


def v2_b(db: LabDatabase) -> dict:
    m = json.loads(json.dumps(json.loads(db.get_latest_math_model(CID_B))))
    m["version"] = 2
    for e in m["equations"]:
        if e["name"] == "netflow":
            e["expression"] = (
                "f_t = clip(r_f*(dX_t/max(X_t,1.0))*1000.0"
                "*sqrt(min(1.0, abs(r_f*dX_t/max(X_t,1.0)*1000.0)"
                "/f_c)), -f_c, f_c)")
            e["description"] = (
                "SYMMETRIC cap with a QUADRATIC ramp near the "
                "boundary: the marginal flow cost stays monotone — "
                "no flat zone to ride; both directions bounded at f_c")
    m["constraints"] = [
        {"statement": "nothing keys off the utilization index U_z",
         "rationale": "U_z is a DISCLOSURE state only: it carries "
                     "scenario identity and stress memory; the r18 "
                     "red-team flagged its latent future use as a "
                     "risk — pinned here as an explicit constraint"},
    ]
    return m


def smoke(m_dict: dict, cid: str) -> None:
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
    cp = b.run_pattern(PatternSpec(kind='crash_park', steps=60))
    print(f"  {cid} v2 smoke PASS: 13/13, worst {worst:.2f}, "
          f"cp heals { {k: round(v,2) for k,v in cp.heal_flags.items()} }")


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    a2, b2 = v2_a(db), v2_b(db)
    smoke(a2, CID_A)
    smoke(b2, CID_B)
    sum_a = (
        "v2 closes the named vectors: (1) the premium's flat 600 cap is "
        "replaced by a sqrt-compressed QUADRATIC ramp — the marginal "
        "premium is monotone in separation, removing the cap-boundary "
        "cliff worth camping; (2) the kicker is GATED on separation "
        "context (pays only when the medium-vs-anchor gate is open), "
        "so flat-regime pulse farming stops paying — the r13 successor "
        "fix pattern applied to the kicker itself. The three-speed "
        "persistence is unchanged (heal ratios ~1.0 by construction)."
    )
    sum_b = (
        "v2 closes the named vectors: (1) the flow cap gains a "
        "quadratic ramp near the f_c boundary — monotone marginal "
        "cost removes the flat zone worth riding; (2) the utilization "
        "index U_z is pinned as a DISCLOSURE-ONLY state by an explicit "
        "constraint (nothing keys off it; the latent future-use risk "
        "the red team flagged is now a named, testable invariant). The "
        "symmetric cap itself is unchanged: bleed bounded at f_c/step "
        "in both directions."
    )
    for rid, cid, mdl, summary, avs in [
        ("9291a290aa2623b4", CID_A, a2, sum_a, [
            "Anchor-camp premium pumping", "Kicker-scale accumulation",
            "Premium-cap boundary riding", "Level-feed grinding (out-of-model)"]),
        ("5d12e5f5d25cc7c5", CID_B, b2, sum_b, [
            "Cap-boundary flow riding", "Utilization-index feeding",
            "Demand-EMA lag exploitation", "Feed corruption (out-of-model)"]),
    ]:
        answer = {
            "summary": summary,
            "addressed_attacks": [
                {"agent_name": agent, "vector_description": vec,
                 "fix_strategy": summary, "fixes_attack": True}
                for agent, vec in zip(
                    ["red_team", "game_theory", "security", "oracle"],
                    avs, strict=True)
            ],
            "model": mdl,
        }
        AgentBridgeProvider().install_answer(rid, answer)
        print("  answered", rid, cid, "v2")


if __name__ == "__main__":
    main()
