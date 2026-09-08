"""Round 15: red-team answers (4 schemas) — honest VULNERABLE.

Named vectors from the v1 semantics:
  - re-basing-window slash dumping: an attacker timing a collateral
    POST right after a shift window opens pays the transient slash at
    its worst while incumbents share it; timing shifts the cost
  - E_t kick keys instantaneous |dX| — the pulse-farming family from
    r13 (cap-boundary pulsing of the 250*|dX|/X term into escrow
    demand, harvesting allocation weight)
  - allocation shrinkage pass-through: A_t = 0.5*E + 0.5*C ties
    capacity to the re-based pool — a whale moving the level contracts
    everyone's allocation (a griefing vector with real cost)

Run: .venv/bin/python scripts/r15_answer_redteam.py
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
        "The single-magnet pool closes the standing-burn equilibrium "
        "measured in the predecessor (late-window stress 0.0000). The "
        "residual vectors are timing and flow-shaped: the re-basing "
        "window's transient slash can be dumped on incumbents by "
        "attackers timing their posts, and the escrow-demand kicker "
        "keys instantaneous |dX| — the r13 pulse-farming family, here "
        "harvesting allocation weight rather than fees."
    ),
    attack_vectors=[
        AV(
            vector="Re-basing-window slash dumping",
            description=(
                "An attacker posts collateral immediately after a "
                "level shift opens the re-basing window, then "
                "withdraws as it closes: the transient slash lands "
                "maximally on incumbents while the attacker's post "
                "enjoys the post-close pool weight."
            ),
            attacker="liquidity_provider",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Escrow-kicker pulse farming of allocation weight",
            description=(
                "E_t keys 250*|dX|/X each step; pulsing |dX| under the "
                "kicker's implicit scale inflates escrow demand and "
                "with it A_t weight — the r13 pulse family applied to "
                "allocation."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Standing burn: closed (measured 0.0000 late stress). "
        "Relative enrichment: closed (allocation tracks the re-based "
        "pool). Residual: timing-dumped transient slash and pulsed "
        "escrow demand — both bounded but positive."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.0,
)

sec = SecurityReport(
    summary=(
        "Single-magnet pool arithmetic, clip-bounded with a floor "
        "below crash levels (250 < 400, the r15 floor lesson — a floor "
        "above the crash level re-creates the eternal burn through the "
        "clip). The kicker's instantaneous |dX| key is the weakest "
        "surface (r13 family)."
    ),
    attack_vectors=[
        AV(
            vector="Kicker cap-scale pulsing",
            description=(
                "Pulse |dX|/X to farm the 250-weighted escrow bump "
                "each step without moving the level EMA."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "Kicker pulsing: any instantaneous |dX| term has a farmable "
        "scale unless keyed to EMA separation."
    ),
    security_score=6.8,
)

orc = OracleReport(
    summary=(
        "Sole exogenous input is the bandwidth level; pool, stress, "
        "and allocation are computed. Anchor integrity is "
        "out-of-model (index diversification)."
    ),
    data_source_assessment=(
        "Bandwidth level series only; all state transitions "
        "deterministic."
    ),
    manipulation_vectors=[
        AV(
            vector="Bandwidth-index pulsing",
            description=(
                "A majority index provider pulses |dX| to inflate "
                "escrow demand and allocation weight."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=True,
            requires_collusion=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    oracle_feasibility_score=7.0,
)

red = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Escrow-kicker pulse farming: E_t keys 250*|dX|/X each step — "
        "an attacker pulsing the level change under the kicker's scale "
        "inflates escrow demand and harvests allocation weight without "
        "moving the pool's regime."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AV(
            vector="Escrow-kicker pulse farming of allocation weight",
            description="Pulse |dX|; harvest A_t weight via E_t.",
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Re-basing-window slash dumping",
            description="Time posts to dump the transient slash on "
                        "incumbents.",
            attacker="liquidity_provider",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Key the escrow kicker to fast-vs-pool EMA separation (the "
        "r13 fix pattern — zero-mean pulses average out) and weight "
        "the transient slash by POST AGE so window-dumped posts pay "
        "their own slash."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "521a633ba325511e": orc,
        "55fd53ef7280179f": sec,
        "bf2d20cd0af68d0e": game,
        "e79c29789da05f5d": red,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
