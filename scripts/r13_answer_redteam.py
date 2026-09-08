"""Round 13: red-team answers (4 schemas x 2 successors) — honest VULNERABLE.

The named attack vectors (evidence-based, from the model semantics):

Oracle (Persistent-Trend Prediction-Fee Oracle):
  - recovery-leg overpay: cover buyers overpay while the medium EMA
    climbs back to the regime anchor after a genuine recovery
    (bounded by kappa_l) — a cost-shifting vector, not theft
  - anchor-drift free premium: very long growth regimes sustain a
    small permanent gate premium (ultra-slow EMA lags)
  - kicker shaping: the fast kicker (20*min(1,|dX|/X/0.2)*10) keys
    instantaneous |dX| — a crash-timed attacker can pulse |dX| right
    under the 0.2 cap each step to farm the kicker's OI bump

Joule (Persistent-Drift Joule Escrow):
  - persistent-alarm overcharge: providers delivering fine at the new
    level pay the alarm premium until the EMAs reconverge
  - ratchet gaming: chi shrinks with escrow turnover — a provider
    refilling escrow in small tranches keeps tolerance high
  - crash-window kicker shaping: min(18, 8*sqrt(|dX|/X)) keys
    instantaneous moves — pulsing |dX| below cap farms nothing here,
    but a large single spike slashes others' escrow while the
    attacker's own refill lands after (timing shift)

All verdicts VULNERABLE with the strongest attack profitable — the
improve stage will patch what code can measure.

Run: .venv/bin/python scripts/r13_answer_redteam.py
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

# --- Oracle (cand-d656eeeaeca1) -------------------------------------------

o_game = GameTheoryReport(
    summary=(
        "The persistent-regime gate prices cover honestly across "
        "crash-park regimes, but its three-speed construction leaves "
        "two priced-in frictions an attacker can exploit: the "
        "recovery-leg overpay (cover buyers overpay while the medium "
        "EMA climbs back to the anchor) and the anchor-drift free "
        "premium under very long growth. Neither drains the pools "
        "directly; both shift cost onto cover buyers. The fast kicker "
        "keys instantaneous |dX| — pulse farming is the direct "
        "extraction vector."
    ),
    attack_vectors=[
        AV(
            vector="Kicker-pulse farming of the crash kicker",
            description=(
                "The kicker pays 20*min(1,|dX|/X/0.2)*10 into the fee "
                "each step; an attacker pulsing |dX| just under the "
                "0.2-cap every step sustains the full kicker without "
                "moving the regime gate — collected as inflated fee "
                "spread on wash-traded flow."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Recovery-leg overpay harvesting",
            description=(
                "After a genuine recovery the medium EMA lags the anchor "
                "for ~1/kappa_l steps; cover sellers hold the elevated "
                "premium through the recovery leg and harvest the "
                "overpay."
            ),
            attacker="liquidity_provider",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Sustained regime displacement persists honestly (the r13 fix); "
        "the residual equilibria are priced frictions — recovery-leg "
        "lag and anchor drift — plus the instantaneous kicker, which "
        "is a genuine extraction surface."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.0,
)

o_sec = SecurityReport(
    summary=(
        "All states clip-bounded (200..4000 for the EMAs — no "
        "saturation); the regime gate is arithmetic and computed, "
        "never reported. The kicker is the weakest surface: it keys "
        "instantaneous |dX| with a min() cap, and the cap boundary "
        "is a farmable cliff."
    ),
    attack_vectors=[
        AV(
            vector="Kicker cap-boundary farming",
            description=(
                "Pulse |dX|/X just under the 0.2 kicker cap each step: "
                "max kicker response, no regime-gate movement — the "
                "cap boundary is a cliff, not a smooth decay."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "Kicker cap-boundary farming: any instantaneous kicker keyed "
        "to |dX| has a farmable boundary unless the response decays "
        "smoothly or keys the EMA displacement instead."
    ),
    security_score=6.8,
)

o_orc = OracleReport(
    summary=(
        "The mechanism consumes only the anchor level series; the "
        "three-speed gate is computed, not reported. Oracle risk "
        "reduces to anchor integrity (out-of-model: median-of-feeds)."
    ),
    data_source_assessment=(
        "Anchor level X_t is the sole exogenous input; gate and "
        "kicker are deterministic functions of the series."
    ),
    manipulation_vectors=[
        AV(
            vector="Anchor pulsing to farm the kicker",
            description=(
                "A majority anchor provider pulses |dX| just under the "
                "kicker cap; the collected premium spreads to flow "
                "while regime displacement stays flat."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=True,
            requires_collusion=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    oracle_feasibility_score=7.0,
)

o_red = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Kicker-pulse farming: the crash kicker keys instantaneous "
        "|dX|/X with a hard 0.2 cap — an attacker pulsing just under "
        "the cap every step collects the full kicker premium without "
        "moving the regime gate."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AV(
            vector="Kicker-pulse farming of the crash kicker",
            description=(
                "Pulse |dX| under the cap; harvest the fee spread "
                "while the gate stays quiet."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Recovery-leg overpay harvesting",
            description=(
                "Cover sellers hold the lagging premium through the "
                "recovery leg."
            ),
            attacker="liquidity_provider",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Key the kicker to EMA displacement (fast-minus-medium EMA "
        "separation) instead of instantaneous |dX| — zero-mean pulses "
        "average out of an EMA, so pulsing stops paying — and shrink "
        "the kicker's weight."
    ),
)

# --- Joule (cand-4e292d1b929b) ---------------------------------------------

j_game = GameTheoryReport(
    summary=(
        "The persistent alarm closes healed-window default timing (the "
        "r13 flaw) — a default timed after the alarm heals now pays the "
        "full persistent premium. The residual vectors: ratchet gaming "
        "(chi shrinks with escrow turnover — tranche refills keep "
        "tolerance high) and persistent-alarm overcharge on providers "
        "delivering fine at the new level (a cost the design must "
        "disclose, not hide)."
    ),
    attack_vectors=[
        AV(
            vector="Ratchet gaming via tranche refills",
            description=(
                "The ratcheting tolerance chi shrinks with escrow "
                "turnover; a provider refilling in many small tranches "
                "keeps measured turnover high and tolerance wide, "
                "delaying the alarm's persistence discipline."
            ),
            attacker="validator",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Persistent-alarm overcharge pass-through",
            description=(
                "Providers delivering correctly at the new level "
                "still pay the alarm premium during the reconvergence "
                "window; a dominant provider passes this cost to "
                "customers as a scarcity surcharge."
            ),
            attacker="validator",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Defaults timed to healed windows: closed (alarm cannot heal "
        "while displacement persists). The remaining equilibria are "
        "calibration frictions — ratchet width and reconvergence "
        "overcharge — both bounded but positive."
    ),
    death_spiral_risk=2.5,
    game_theory_score=7.0,
)

j_sec = SecurityReport(
    summary=(
        "Clip-bounded states (600..2200 escrow, wide EMA clips); the "
        "alarm is arithmetic on computed EMAs. The ratchet's chi key "
        "(escrow turnover) is gameable by tranche sizing — the "
        "weakest surface."
    ),
    attack_vectors=[
        AV(
            vector="Tranche-sized ratchet evasion",
            description=(
                "Small-tranche refills inflate turnover, keeping chi "
                "wide and the alarm slow to ratchet against a "
                "drifting provider."
            ),
            attacker="validator",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "Tranche-sized ratchet evasion: turnover-keyed tolerance can "
        "always be inflated by sizing unless it keys the displacement "
        "trend itself rather than flow."
    ),
    security_score=6.6,
)

j_orc = OracleReport(
    summary=(
        "The escrow consumes only the anchor level; the alarm and "
        "ratchet are computed. Anchor integrity remains out-of-model "
        "infrastructure risk."
    ),
    data_source_assessment=(
        "Sole exogenous input: the anchor level series; all gates "
        "deterministic."
    ),
    manipulation_vectors=[
        AV(
            vector="Anchor shaping to keep the gate narrow",
            description=(
                "A colluding anchor provider smooths the path so the "
                "medium EMA tracks the regime anchor closely, keeping "
                "the alarm quiet while delivery actually degrades at "
                "the new level."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=True,
            requires_collusion=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    oracle_feasibility_score=7.0,
)

j_red = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Ratchet gaming via tranche refills: turnover-keyed tolerance "
        "stays wide under small-tranche refills, letting a drifting "
        "provider delay the persistent alarm's discipline while "
        "defaults stay timed to quiet windows."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AV(
            vector="Ratchet gaming via tranche refills",
            description=(
                "Small tranches keep chi wide; the alarm stays quiet "
                "for a drifting provider."
            ),
            attacker="validator",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Persistent-alarm overcharge pass-through",
            description=(
                "Reconvergence-window premium passed to customers."
            ),
            attacker="validator",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Key the ratchet to the displacement TREND (medium EMA's own "
        "movement toward/away from the anchor) rather than escrow "
        "turnover — sizing flow cannot inflate a displacement-keyed "
        "tolerance — and cap the reconvergence overcharge with a "
        "delivery-resumption credit."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "33da98839dcc32aa": o_game,
        "371389b2912fea49": j_game,
        "3e17e09fbfa19261": j_red,
        "874b27f600fa42b5": j_sec,
        "87e41ae8bdba03c6": j_orc,
        "b90f7d46308e70ec": o_red,
        "f71b5bdb62624c7f": o_orc,
        "f7c39b0c9efadfdf": o_sec,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
