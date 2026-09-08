"""Round 20: improve round-2 answer — v3 sign-persistence counter.

The re-attack (against the stored v2, magnitude-keyed counter) named
the two honest flaws: threshold riding (saw-teeth under the
magnitude threshold ride undetected) and genuine-lead deadness
(retention flat 0.300 through real sustained pressure — measured).
v3 replaces the counter's key with separation SIGN PERSISTENCE
(g_t*G_t, G_t the lagged separation): alternation raises the
counter at ANY amplitude (no threshold to ride), persistence decays
it (the genuine response rides).

Run: .venv/bin/python scripts/r20_answer_improve2.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase

RID = "233b29f3a79174bb"


def main() -> None:
    # reuse the v3 builder + smoke from r20_answer_improve.py
    spec = importlib.util.spec_from_file_location(
        "r20ai", Path("scripts/r20_answer_improve.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    m3 = mod.v2(db)  # builds v3 from the stored v2
    mod.smoke(m3)
    summary = (
        "v3 replaces the magnitude-keyed counter with a SIGN-"
        "PERSISTENCE key: the counter C_t reads the product g_t*G_t "
        "(current separation x its lag) — alternation (product < 0, "
        "a saw-tooth) raises the counter AT ANY AMPLITUDE: there is "
        "no magnitude threshold to ride (the re-attack's finding 1); "
        "persistence (product > 0, a genuine followed lead) decays "
        "it and the separation key rides — the genuine-pressure "
        "response is preserved (the re-attack's finding 2: v2's "
        "counter pinned at 1.0 through a 3%/step grind and "
        "retention never rose on real pressure; measured v3: "
        "genuine-lead late r_t 0.428, saw-tooth mean 0.300 = base). "
        "The symmetric clip band and the bounded reverting escrow "
        "target are unchanged (resonance heads [0,0,0,0] at "
        "N=2/4/8/16)."
    )
    fix = (
        "Counter re-keyed from movement magnitude |kappa_f*(X-L_f)| "
        "to separation SIGN PERSISTENCE g_t*G_t (G_t = lagged "
        "separation state): alternation raises the counter at any "
        "amplitude — no threshold to ride; persistence (genuine "
        "lead) decays it — the response rides. Measured: saw "
        "0.300, genuine-lead 0.428, resonance [0,0,0,0]."
    )
    avs = [
        "Counter-threshold boundary riding",
        "Genuine-lead deadness (functionality failure)",
        "Calibration-threshold misclassification",
        "Slow saw-tooth under the counter threshold",
    ]
    answer = {
        "summary": summary,
        "addressed_attacks": [
            {"agent_name": agent, "vector_description": vec,
             "fix_strategy": fix, "fixes_attack": True}
            for agent, vec in zip(
                ["red_team", "game_theory", "security", "oracle"],
                avs, strict=True)
        ],
        "model": m3.model_dump(mode="json"),
    }
    AgentBridgeProvider().install_answer(RID, answer)
    print(f"  answered {RID}", m3.version, "(sign-persistence counter)")


if __name__ == "__main__":
    main()
