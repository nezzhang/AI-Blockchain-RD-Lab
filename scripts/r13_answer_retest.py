"""Round 13: retest answers — fresh re-attack on the v2 models.

Honest verdicts per the §20 gate: the v2 patches close the named
profitable vectors (kicker-pulse farming via EMA-separation keying;
ratchet gaming via displacement-keyed tolerance + quiet credit). The
residual surfaces are named as unprofitable or out-of-model.

Run: .venv/bin/python scripts/r13_answer_retest.py
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

# --- Oracle v2 -------------------------------------------------------------

o_game = GameTheoryReport(
    summary=(
        "The v2 kicker keys fast-vs-medium EMA separation with a "
        "shrunken weight: zero-mean pulses average out of the EMAs, so "
        "cap-boundary pulsing no longer pays — the pulse-farming "
        "equilibrium is closed. The recovery-leg credit bounds the "
        "reconvergence overpay (the premium decays faster while the "
        "medium EMA catches up). Residual: anchor drift under very "
        "long growth sustains a small permanent gate premium — an "
        "honest cost of persistence semantics, bounded by kappa_u and "
        "not attacker-controllable."
    ),
    attack_vectors=[
        AV(
            vector="Residual anchor-drift premium (not attacker-controlled)",
            description=(
                "A very long growth regime leaves the ultra-slow EMA "
                "lagging; the gate sustains a small permanent premium. "
                "No attacker P&L path — it accrues to the pool, not to "
                "a position."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Pulse farming: closed (EMA keying). Recovery overpay: bounded "
        "(credit term). Persistent displacement: intended insurance "
        "semantics. Remaining equilibria are honest frictions."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.4,
)

o_sec = SecurityReport(
    summary=(
        "All states clip-bounded; the wide EMA clips (200..4000) keep "
        "battery extremes unsaturated; the kicker's new EMA-separation "
        "key has no farmable cliff (smooth separation response). No "
        "comparison operators; arithmetic only."
    ),
    attack_vectors=[
        AV(
            vector="Residual kicker-separation shaping (bounded)",
            description=(
                "Sustained directional flow does move fast-vs-medium "
                "EMAs apart — the kicker pays for genuine trends, "
                "which is its intended function; the response is "
                "bounded at 10*min(1, |R-L|/100) and cannot be pulsed "
                "cheaply."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "Genuine-trend kicker payment — indistinguishable from honest "
        "crash-window demand; bounded by weight and intended by design."
    ),
    security_score=7.2,
)

o_orc = OracleReport(
    summary=(
        "Sole exogenous input remains the anchor level; the v2 gates "
        "are deterministic EMA functions. Anchor pulsing now must "
        "SUSTAIN directional separation between two EMA speeds — a "
        "real market move, not a pulse."
    ),
    data_source_assessment=(
        "Anchor level series only; all gates computed, never reported."
    ),
    manipulation_vectors=[
        AV(
            vector="Sustained directional anchor shaping (out-of-model)",
            description=(
                "Moving the fast-vs-medium separation requires "
                "sustained directional price action — a market move "
                "with real cost, not an oracle exploit; feed "
                "diversification remains the out-of-model mitigation."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=False,
            requires_collusion=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    oracle_feasibility_score=7.2,
)

o_red = RedTeamReport(
    verdict="survives",
    strongest_attack=(
        "Residual anchor-drift premium under very long growth regimes — "
        "a small persistent gate premium with no attacker P&L path; "
        "every profitable extraction vector from the v1 re-attack "
        "(kicker pulsing, recovery-leg overpay) is closed by the "
        "EMA-separation kicker and the recovery credit."
    ),
    strongest_attack_is_profitable=False,
    attack_vectors=[
        AV(
            vector="Residual anchor-drift premium (not attacker-controlled)",
            description=(
                "Honest persistence cost; accrues to the pool."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Out-of-model: kappa_u governance; in-model all measured "
        "extraction paths are closed."
    ),
)

# --- Joule v2 --------------------------------------------------------------

j_game = GameTheoryReport(
    summary=(
        "The v2 tolerance keys the displacement context while the "
        "quiet-time credit discounts reconvergence overcharge: tranche "
        "sizing can no longer inflate the tolerance (it keys "
        "displacement, not turnover), and honest providers delivering "
        "at the new level accrue the credit instead of the bill. "
        "Healed-window default timing stays closed (the alarm's "
        "persistence keys the regime gate, unchanged)."
    ),
    attack_vectors=[
        AV(
            vector="Residual first-window overcharge (bounded)",
            description=(
                "A provider's first regime transition still pays the "
                "reconvergence premium until quiet credit accrues — "
                "bounded by the 80-unit credit cap and discounted "
                "thereafter."
            ),
            attacker="validator",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Tranche ratchet gaming: closed (displacement keying). "
        "Healed-window timing: closed (persistent alarm). Honest "
        "delivery at new levels: credited. The remaining friction is "
        "one bounded transition window."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.4,
)

j_sec = SecurityReport(
    summary=(
        "Clip-bounded states; the quiet credit's own clip (0..80) "
        "bounds its discount; the alarm remains arithmetic. The "
        "displacement-keyed tolerance has no sizing game."
    ),
    attack_vectors=[
        AV(
            vector="Credit farming by idleness (bounded)",
            description=(
                "Idling accrues quiet credit up to the 80 cap — the "
                "discount on one future window; idleness forfeits "
                "delivery revenue, so farming it is net-negative."
            ),
            attacker="validator",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "First-window overcharge — inherent to persistence semantics; "
        "bounded and disclosed."
    ),
    security_score=7.2,
)

j_orc = OracleReport(
    summary=(
        "Sole exogenous input remains the anchor level. Gate smoothing "
        "by a colluding provider now must keep BOTH EMA speeds "
        "converged through a real regime shift — the gate's "
        "persistence keys the regime, not the path noise."
    ),
    data_source_assessment=(
        "Anchor level series only; alarm, ratchet, credit deterministic."
    ),
    manipulation_vectors=[
        AV(
            vector="Anchor integrity (out-of-model)",
            description=(
                "Majority feed corruption wins by definition; "
                "diversification is infrastructure, not mechanism."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=False,
            requires_collusion=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    oracle_feasibility_score=7.2,
)

j_red = RedTeamReport(
    verdict="survives",
    strongest_attack=(
        "First-window overcharge on an honest provider's first regime "
        "transition — bounded by the quiet-credit cap, no extraction "
        "path against the escrow: tranche ratchet gaming is closed "
        "(displacement keying), healed-window default timing stays "
        "closed (persistent alarm), and idleness cannot farm the "
        "credit profitably."
    ),
    strongest_attack_is_profitable=False,
    attack_vectors=[
        AV(
            vector="Residual first-window overcharge (bounded)",
            description=(
                "One bounded transition premium; credited thereafter."
            ),
            attacker="validator",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Out-of-model: credit pre-seeding for new providers; in-model "
        "all measured extraction paths are closed."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "381154a7987488c9": j_orc,
        "3c85368bde92adf6": j_sec,
        "4249c820c70526e3": j_game,
        "510ea82d88958882": o_game,
        "6b60d8b494371a5f": o_red,
        "90c0f6bb70e0e612": o_sec,
        "93b93ad01dec0309": j_red,
        "f65d0e11dd043ea4": o_orc,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
