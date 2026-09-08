"""Round 16: red-team answers (4 schemas) — honest VULNERABLE.

Named vectors from the v1 semantics:
  - drift-paced farming: sustained small directional drift carries the
    reverting EMA (by design) — a patient mover can pace the drift to
    the EMA's carry speed and harvest the additive flow each step
    (small per-step, but positive and unbounded in time)
  - anchor-band camping: the additive flow's 0.001*(T-1000)*10 scale
    means the flow is tiny — but the MEAN-REVERSION -0.02*(S-1000)
    funds a standing drain whenever S sits off-anchor (the r15
    anchor-tug question at additive scale)

Run: .venv/bin/python scripts/r16_answer_redteam.py
"""

from __future__ import annotations

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.redteam import (
    AttackVector,
    GameTheoryReport,
    OracleReport,
    RedTeamReport,
    SecurityReport,
)

AV = AttackVector

game = GameTheoryReport(
    summary=(
        "The additive-flow construction removes the multiplicative "
        "ratchet the superseded cluster farmed (-94% -> 0.00 measured "
        "on vol_oscillation). The residual vectors are patience-shaped: "
        "the reverting EMA carries sustained drift BY DESIGN, so a "
        "patient mover pacing drift at the EMA carry speed harvests "
        "the additive flow indefinitely (small per step, positive, "
        "unbounded in time); and the stock's mean-reversion term is a "
        "standing drain whenever the stock sits off its anchor."
    ),
    attack_vectors=[
        AV(
            vector="Drift-paced additive-flow farming",
            description=(
                "Pace a small directional level drift at the EMA's "
                "carry speed; T departs 1000 and each step's bounded "
                "flow pays toward the moved target — patience turns "
                "the flow cap into a slow tap."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Anchor-band standing drain",
            description=(
                "The -0.02*(S-1000) mean-reversion is a standing drain "
                "on the stock whenever it sits off-anchor (whoever "
                "holds the counter-side of the flow collects)."
            ),
            attacker="liquidity_provider",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Multiplicative ratchet: closed (additive flows). Oscillation "
        "compounding: closed (reverting EMA washes it out). Residual: "
        "drift-paced tap (bounded per step) + off-anchor standing drain."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.0,
)

sec = SecurityReport(
    summary=(
        "All states clip-bounded (200..4000, bracketing battery "
        "extremes); flows additive and capped (f_cap); no multiplicative "
        "path exists. The kicker's 0.05 gain is below any farmable scale "
        "(the r11 kicker-shrink lesson)."
    ),
    attack_vectors=[
        AV(
            vector="Kicker-scale accumulation (bounded)",
            description=(
                "The instantaneous kicker pays on every |dX| pulse but "
                "at 0.05 gain — battery-measured wash edge 1.62 total."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "Drift-paced farming: indistinguishable from genuine "
        "demographic drift; only the flow cap bounds it."
    ),
    security_score=7.1,
)

orc = OracleReport(
    summary=(
        "Sole exogenous input is the population-linked level; every "
        "state transition is deterministic arithmetic."
    ),
    data_source_assessment="Level series only; deterministic gates.",
    manipulation_vectors=[
        AV(
            vector="Level-feed pacing (out-of-model)",
            description=(
                "A majority level feed could pace drift to farm the "
                "flow — feed diversification is infrastructure."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=False,
            requires_collusion=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    oracle_feasibility_score=7.2,
)

red = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Drift-paced additive-flow farming: the reverting EMA carries "
        "sustained drift by design; an attacker pacing the level's "
        "drift at the EMA carry speed harvests each step's bounded "
        "flow — small per step but positive and unbounded in time."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AV(
            vector="Drift-paced additive-flow farming",
            description="Pace drift; harvest the bounded flow each step.",
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Anchor-band standing drain",
            description="Off-anchor stock bleeds via mean reversion.",
            attacker="liquidity_provider",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Key the flow to the EMA's SEPARATION from a slower anchor "
        "(the r13 three-speed pattern: paces drift at carry speed "
        "flattens in the slow frame) and route the mean-reversion "
        "drain to a beneficiary account so it is a fee, not a bleed."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "1422fda632bf8d02": red,
        "420bf50336a22d46": orc,
        "a86c0271951948b4": game,
        "b02c104dab81f332": sec,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
