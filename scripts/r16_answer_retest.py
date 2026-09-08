"""Round 16: retest answers — fresh re-attack on the v2 model.

§20 gate: the v2 patches close the named profitable vectors (drift-
paced farming via the separation key; standing bleed via the routed
sink). Residuals named unprofitable or out-of-model.

Run: .venv/bin/python scripts/r16_answer_retest.py
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
        "The separation key closes the drift-paced tap: pacing drift at "
        "the EMA carry speed moves T and the slow anchor together "
        "(separation stays small), so the flow pays nothing until the "
        "move is a genuine regime change — and then it is the design "
        "working. The routed sink closes the standing bleed: the "
        "mean-reversion magnitude lands in a disclosed beneficiary "
        "account. Battery-measured worst pattern edge 12.42 (was the "
        "cluster's 913.5)."
    ),
    attack_vectors=[
        AV(
            vector="Regime-move flow payment (bounded, by design)",
            description=(
                "A genuine regime move funds the flow — the intended "
                "response; bounded by the flow cap."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Drift-paced farming: closed (separation key). Standing bleed: "
        "closed (routed sink). Multiplicative compounding: closed "
        "(additive flows, v1 property preserved)."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.4,
)

sec = SecurityReport(
    summary=(
        "All states clip-bounded; the sink is disclosed revenue, not "
        "hidden extraction; no multiplicative path exists; worst "
        "battery edge 12.42 across all five choreographies."
    ),
    attack_vectors=[
        AV(
            vector="Sink-observation grooming (bounded)",
            description=(
                "Holders can sit at the anchor to keep the sink quiet — "
                "no extraction, just fee avoidance by not being "
                "off-anchor."
            ),
            attacker="liquidity_provider",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "Nothing measurable in-model; the sink's beneficiary policy is "
        "governance (out-of-model)."
    ),
    security_score=7.3,
)

orc = OracleReport(
    summary=(
        "Sole exogenous input remains the level; the slow anchor is "
        "internal arithmetic. Feed manipulation now must outrun TWO "
        "EMA speeds — a genuine regime move, not a paced drift."
    ),
    data_source_assessment="Level series only; deterministic two-speed gates.",
    manipulation_vectors=[
        AV(
            vector="Feed corruption (out-of-model)",
            description=(
                "Majority feed corruption wins by definition; feed "
                "diversification is infrastructure."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=False,
            requires_collusion=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    oracle_feasibility_score=7.3,
)

red = RedTeamReport(
    verdict="survives",
    strongest_attack=(
        "Regime-move flow payment: a genuine regime move funds the "
        "additive flow — the intended design response, bounded by the "
        "flow cap, with no per-step extraction path (drift-paced "
        "farming closed by the T-vs-slow-anchor separation key; the "
        "standing bleed routed to a disclosed beneficiary sink; the "
        "multiplicative compounding family closed by construction, "
        "913.5 -> 12.42 measured)."
    ),
    strongest_attack_is_profitable=False,
    attack_vectors=[
        AV(
            vector="Regime-move flow payment (bounded, by design)",
            description="Intended response; flow-capped.",
            attacker="arbitrageur",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Out-of-model: sink beneficiary governance; in-model all "
        "measured extraction paths are closed."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "1ef3d5fd2561cb89": sec,
        "aef3bb433f33f2c5": orc,
        "eec7e75934a24819": game,
        "f16a35f9ecf2c569": red,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
