"""Round 18: red-team answers (8 schemas) — honest VULNERABLE.

Three-Speed named vectors: kicker-scale farming (0.04*|I1-I| — small
but nonzero per step); anchor-camp premium pumping (move the level
slowly to widen I-vs-U_s separation and harvest premium scale — the
grind direction); premium-cap boundary riding (the min(600, ...) cap
creates a cliff worth camping).
Symmetric-Cap named vectors: cap-boundary flow riding (the f_c cap
creates a flat region — flow just under the cap pays the same as at
it); utilization-index gaming (the U_z memory rewards sustained flow
stress — an attacker can feed it); demand-EMA lag exploitation.

Run: .venv/bin/python scripts/r18_answer_redteam.py
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

A_GAME = GameTheoryReport(
    summary=(
        "The three-speed gate holds premium persistently under moved "
        "regimes (the r13 polarity, heal ratios ~1.0 measured in "
        "smoke) and flattens under oscillation. Residual vectors are "
        "scale- and direction-shaped: the kicker pays on any intensity "
        "step (0.04 gain — small); a patient mover can grind the level "
        "upward to widen I-vs-U_s separation and harvest premium scale "
        "on their own flow timing; the 600 premium cap is a cliff "
        "worth camping."
    ),
    attack_vectors=[
        AV(vector="Anchor-camp premium pumping",
           description=("Grind the level upward slowly: I rises, U_s "
                        "lags (ultra-slow), separation widens, the "
                        "premium scales on the mover's own flow timing."),
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
        AV(vector="Kicker-scale accumulation",
           description=("Pulse |I1-I| steps to farm the 0.04 kicker "
                        "each step; bounded but positive."),
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
    ],
    equilibria_notes=(
        "Anchor-heal: closed (separation holds by construction). Wash "
        "harvest: closed (both speeds flatten). Residuals: grind-"
        "paced premium scale + small kicker."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.0,
)

A_SEC = SecurityReport(
    summary=(
        "All states clip-bounded (200..3000, brackets battery "
        "extremes); the premium cap min(600, ...) bounds the worst "
        "case; the kicker gain 0.04 is below farmable scale (battery "
        "wash ~2.4)."
    ),
    attack_vectors=[
        AV(vector="Premium-cap boundary riding",
           description=("Camp just under the 600 cap where the premium "
                        "stops responding — a flat zone worth parking "
                        "flow at."),
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
    ],
    hardest_attack_to_defend=(
        "Grind-paced separation widening: indistinguishable from "
        "genuine demand growth; only the cap bounds it."
    ),
    security_score=7.0,
)

A_ORC = OracleReport(
    summary="Sole exogenous input is the level; two internal EMA speeds.",
    data_source_assessment="Level series only; deterministic gates.",
    manipulation_vectors=[
        AV(vector="Level-feed grinding (out-of-model)",
           description="A majority feed grinding the level to farm "
                       "separation; feed diversification is infrastructure.",
           attacker="oracle_provider", profitable_for_attacker=False,
           requires_collusion=True, evidence_level="HYPOTHESIS"),
    ],
    oracle_feasibility_score=7.2,
)

A_RED = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Anchor-camp premium pumping: grind the level upward; the "
        "medium EMA rises while the ultra-slow anchor lags, the "
        "separation (the premium's key) widens on the mover's own "
        "schedule — a patience-shaped premium harvest bounded only "
        "by the 600 cap."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AV(vector="Anchor-camp premium pumping",
           description="Grind level; harvest premium scale.",
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
        AV(vector="Kicker-scale accumulation",
           description="Pulse intensity steps; farm 0.04/step.",
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
    ],
    what_would_save_it=(
        "Key the premium to the separation's RATE OF CHANGE direction "
        "or gate the kicker on separation context (the r13 successor "
        "pattern); make the premium respond to the GRIND specifically "
        "by keying a second, slower anchor so single-direction grinds "
        "cancel like pulses do."
    ),
)

B_GAME = GameTheoryReport(
    summary=(
        "The symmetric cap bounds both flow directions at f_c — no "
        "uncapped bleed remains (the r18 floor-pin family closed). "
        "Residuals: the cap's flat region lets flow ride at boundary "
        "costs; the utilization index U_z rewards sustained flow "
        "stress (an attacker can feed it); the demand EMA lags fast "
        "regime moves."
    ),
    attack_vectors=[
        AV(vector="Cap-boundary flow riding",
           description=("Push flow just under f_c where the marginal "
                        "cost of more flow is zero — a flat zone worth "
                        "riding."),
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
        AV(vector="Utilization-index feeding",
           description=("Sustained moderate outflow feeds U_z (stress "
                        "memory) — if any future term keys off U_z, the "
                        "attacker pre-loads it."),
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
    ],
    equilibria_notes=(
        "Floor-pin drain: closed (symmetric cap). Uncapped bleed: "
        "closed. Residuals: boundary riding + U_z pre-loading (U_z "
        "currently feeds nothing — latent only)."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.1,
)

B_SEC = SecurityReport(
    summary=(
        "Clips bracket battery extremes; the flow cap is arithmetic "
        "with no multiplicative path; the U_z memory is additive and "
        "bounded at 400."
    ),
    attack_vectors=[
        AV(vector="Demand-EMA lag exploitation",
           description=("Fast regime moves outpace T_t; the reversion "
                        "target lags (disclosed responsiveness, not an "
                        "extraction)."),
           attacker="arbitrageur", profitable_for_attacker=False,
           evidence_level="HYPOTHESIS"),
    ],
    hardest_attack_to_defend=(
        "Cap-boundary riding: the flat region is the cap's own price."
    ),
    security_score=7.1,
)

B_ORC = OracleReport(
    summary="Sole exogenous input is the level; flows deterministic.",
    data_source_assessment="Level series only; deterministic gates.",
    manipulation_vectors=[
        AV(vector="Feed corruption (out-of-model)",
           description="Majority feed corruption wins by definition.",
           attacker="oracle_provider", profitable_for_attacker=False,
           requires_collusion=True, evidence_level="HYPOTHESIS"),
    ],
    oracle_feasibility_score=7.2,
)

B_RED = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Cap-boundary flow riding: flow pushed just under the f_c cap "
        "pays the same marginal cost as flow at half the cap — the "
        "flat region invites boundary-riding; and the utilization "
        "index U_z accumulates the rider's own sustained stress "
        "(latent, but pre-loadable for any future term that keys it)."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AV(vector="Cap-boundary flow riding",
           description="Ride the cap's flat zone.",
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
        AV(vector="Utilization-index feeding",
           description="Sustained moderate outflow pre-loads U_z.",
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
    ],
    what_would_save_it=(
        "Smooth the cap (quadratic ramp near the boundary) so the "
        "marginal cost stays monotone; and either remove U_z or key "
        "nothing to it (it currently feeds nothing — the latent risk "
        "is its future use)."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "28df4d91d2ea9d65": B_SEC,
        "62d060ac19306615": B_GAME,
        "6d8b26624fcb7a95": A_ORC,
        "7c1f50a08884778f": A_RED,
        "9365a184e6897f7b": B_RED,
        "afdf19d81affbdd1": A_GAME,
        "d34f5d88b1501093": B_ORC,
        "ed4312b4568afe0d": A_SEC,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
