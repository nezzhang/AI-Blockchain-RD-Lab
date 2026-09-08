"""Round 15: retest answers — fresh re-attack on the v2 model.

§20 gate: the v2 patches close the named profitable vectors (kicker
pulse farming via EMA-separation keying; window-dumping via the
age-gated slash). Residual surfaces named unprofitable or out-of-model.

Run: .venv/bin/python scripts/r15_answer_retest.py
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
        "The v2 kicker keys fast-vs-pool EMA separation: zero-mean "
        "pulses average out of both EMAs, so pulsing stops paying — "
        "the allocation-weight harvest is closed. The age-gated slash "
        "makes window-dumping self-funding: a fresh post's slash "
        "weight is 1.0x (vs the 0.3x tenure floor), so timing a post "
        "into the re-basing window carries the attacker's own cost "
        "rather than dumping it on incumbents. Standing burn stays "
        "closed (measured late-window stress 0.0000)."
    ),
    attack_vectors=[
        AV(
            vector="Residual tenure-floor accumulation (bounded)",
            description=(
                "An idle incumbent accrues tenure to the 0.3x floor "
                "and pays less transient slash per future window — "
                "bounded by the floor and funded by actually being "
                "there (idleness forfeits relay revenue)."
            ),
            attacker="liquidity_provider",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Pulse farming: closed (EMA-separation keying). Window "
        "dumping: self-funding (age gate). Standing burn: closed "
        "(single magnet). Remaining: bounded tenure accumulation, "
        "honestly disclosed."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.4,
)

sec = SecurityReport(
    summary=(
        "All states clip-bounded; the pool floor (250) sits below "
        "crash levels so the clip cannot re-create the eternal burn "
        "(the r15 floor lesson, pinned). The kicker separation has no "
        "farmable cliff; the age gate is arithmetic with a bounded "
        "floor."
    ),
    attack_vectors=[
        AV(
            vector="Residual separation shaping (bounded)",
            description=(
                "Sustained directional flow separates the fast EMA "
                "from the pool and pays the kicker — a genuine trend "
                "cost, bounded at 120 weight and intended."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "Genuine-trend kicker payment — indistinguishable from honest "
        "demand; bounded by weight."
    ),
    security_score=7.2,
)

orc = OracleReport(
    summary=(
        "Sole exogenous input remains the bandwidth level; pulsing the "
        "index must now SUSTAIN directional separation between two EMA "
        "speeds — a real market move, not a pulse."
    ),
    data_source_assessment="Bandwidth level series only; deterministic gates.",
    manipulation_vectors=[
        AV(
            vector="Anchor integrity (out-of-model)",
            description=(
                "Majority index corruption wins by definition; index "
                "diversification is infrastructure."
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
    verdict="survives",
    strongest_attack=(
        "Residual tenure-floor accumulation: an idle incumbent "
        "accrues a bounded slash discount — no extraction path "
        "against the pool (pulse farming closed by EMA-separation "
        "keying; window-dumping self-funded by the age gate; standing "
        "burn closed by the single-magnet re-basing, late stress "
        "0.0000 measured)."
    ),
    strongest_attack_is_profitable=False,
    attack_vectors=[
        AV(
            vector="Residual tenure-floor accumulation (bounded)",
            description="Bounded discount funded by actual tenure.",
            attacker="liquidity_provider",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Out-of-model: tenure governance; in-model all measured "
        "extraction paths are closed."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "4cde28b538a759f3": orc,
        "686cfed7d67a5d41": game,
        "917676a4644f0b2d": red,
        "fa94414e7f17c771": sec,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
