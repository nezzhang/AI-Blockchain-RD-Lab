"""Round 20: retest round-2 answers (against v3, sign-persistence).

The re-attack names the v2 flaws; v3 (sign-persistence counter)
closes both by measurement: slow saw-tooth mean retention 0.300 =
base exactly (C_t 1.0, fully discounted — no amplitude threshold
to ride), duty-cycle saw 0.300, genuine 3%/step lead 0.428 -> 0.473
(C_t 0.001 — the response rides), resonance heads [0,0,0,0].

Run: .venv/bin/python scripts/r20_answer_retest2.py
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

GAME = GameTheoryReport(
    summary=(
        "v3's sign-persistence counter closes both named v2 flaws: "
        "there is no magnitude threshold to ride (alternation "
        "raises the counter at ANY amplitude — measured slow "
        "saw-tooth mean retention 0.300 = base with C_t pinned "
        "1.0), and genuine sustained pressure is no longer "
        "discounted (measured 3%/step grind: retention 0.428 -> "
        "0.473 with C_t 0.001). The remaining surface is "
        "second-order: the counter's decay lam_c gives a brief "
        "window after a genuine lead ends during which a crafted "
        "alternation is still partially discounted (and vice versa "
        "— an alternation ending leaves the counter briefly high)."
    ),
    attack_vectors=[
        AttackVector(
            vector="counter handoff window",
            description=(
                "After a genuine lead (C_t ~0) ends, an immediate "
                "saw-tooth rides the separation key at full strength "
                "for ~1/lam_c steps before the counter catches up — "
                "a first-cycle transient the discount misses; bounded "
                "by the symmetric band half-width 0.25 and requires "
                "paying the genuine lead's move cost first"
            ),
            attacker="attacker",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
    ],
    equilibria_notes=(
        "The alternation/persistence dichotomy is amplitude-free: "
        "the equilibrium discount rate is the cycle's alternation "
        "FRACTION, not its size; with the symmetric band the "
        "cycling average converges to the band center"
    ),
    death_spiral_risk=1.5,
    game_theory_score=7.5,
    evidence_level="INFERENCE",
)

SEC = SecurityReport(
    summary=(
        "The sign-persistence key removes the exploitable boundary "
        "entirely: the counter's input g_t*G_t is a sign test, not a "
        "magnitude test — no threshold to sit under. Measured: slow "
        "saw-tooth 0.300 (= base), duty-cycle saw 0.300, genuine "
        "lead 0.428 (response preserved). Residual: the counter is "
        "a DISCOUNT, not a veto — a path that alternates slowly "
        "enough (period longer than 1/lam_c) spends part of each "
        "leg at partial discount."
    ),
    attack_vectors=[
        AttackVector(
            vector="long-period alternation partial ride",
            description=(
                "A saw-tooth with period >> 1/lam_c (~5 steps) lets "
                "the counter partially decay during each long leg, "
                "so the first portion of every leg rides at partial "
                "discount — the average discount is < 1 and part of "
                "each leg's separation keys retention; bounded by "
                "the symmetric band (±0.25 around base) and "
                "second-order"
            ),
            attacker="attacker",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
    ],
    hardest_attack_to_defend=(
        "The long-period alternation: any EMA-based discount has a "
        "time-constant boundary; the symmetric band bounds the "
        "harvest to the band half-width regardless"
    ),
    security_score=7.0,
    evidence_level="INFERENCE",
)

ORACLE = OracleReport(
    summary=(
        "v3 removes the magnitude normalization (the implicit "
        "calibration oracle the re-attack flagged): the counter keys "
        "sign persistence, which is scale-free — no assumption "
        "about normal move sizes remains. All states derive "
        "locally from the on-chain level series."
    ),
    data_source_assessment=(
        "X_t/dX_t on-chain; fast/slow EMAs, lagged separation, and "
        "the counter all derive locally; no calibration constants "
        "on move magnitudes remain (the only scale constants are "
        "the clip bounds, disclosed)"
    ),
    manipulation_vectors=[
        AttackVector(
            vector="alternation-sign manipulation",
            description=(
                "The attacker controls dX fully, hence the "
                "separation's sign — but the counter reads exactly "
                "that control: alternation raises the discount. The "
                "only path left is paying for persistence (a real "
                "sustained move), which is the design's genuine "
                "use case"
            ),
            attacker="whale",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="FACT",
        ),
    ],
    oracle_feasibility_score=8.0,
    evidence_level="FACT",
)

RED = RedTeamReport(
    verdict="survives",
    strongest_attack=(
        "Long-period alternation partial ride: a saw-tooth with "
        "period well above the counter's time constant spends the "
        "first fraction of each leg at partial discount (the EMA "
        "discount's own handoff lag) — but the harvest is bounded "
        "by the symmetric band's half-width (0.25 around base "
        "retention) and requires alternating the level for the "
        "whole window at real move cost; no profitable path "
        "identified. Both v2 flaws measured closed: slow saw "
        "0.300, genuine lead 0.428 -> 0.473, resonance [0,0,0,0]."
    ),
    strongest_attack_is_profitable=False,
    attack_vectors=[
        AttackVector(
            vector="long-period alternation partial ride",
            description=(
                "Period >> 1/lam_c saw-tooth: partial discount on "
                "each leg's first fraction; bounded by the band "
                "half-width, second-order"
            ),
            attacker="attacker",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
        AttackVector(
            vector="counter handoff window after a genuine lead",
            description=(
                "~1/lam_c-step window after a real lead ends where "
                "alternation rides at full key strength before the "
                "counter catches up; requires paying the lead's "
                "cost first"
            ),
            attacker="attacker",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
    ],
    what_would_save_it=(
        "Nothing needed for the named class; the handoff window "
        "could shrink with a faster counter decay if a future "
        "measurement makes the partial ride profitable"
    ),
    evidence_level="INFERENCE",
)


def main() -> None:
    p = AgentBridgeProvider()
    for rid, ans in [
        ("171b78fbccb754fe", GAME),
        ("db946d7936644e3b", SEC),
        ("862ad61c65989448", ORACLE),
        ("a79cbc250ef8ea74", RED),
    ]:
        p.install_answer(rid, ans.model_dump(mode="json"))
        print(f"installed {rid} {type(ans).__name__}")


if __name__ == "__main__":
    main()
