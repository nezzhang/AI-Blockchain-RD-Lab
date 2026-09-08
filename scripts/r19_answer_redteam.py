"""Round 19: red-team answers (4 schemas) — honest VULNERABLE.

Named vectors (all HYPOTHESIS, structurally grounded):
- Flow-cap boundary riding: the ±f_c cap creates a flat marginal-cost
  zone just under the cap (the r18 Symmetric-Cap finding family — its
  v2 fixed this with a quadratic ramp; this v1 carries the flat cap).
- Stress-memory pre-loading: S_w accumulates sustained |dX| and keys
  NOTHING today (disclosure-only, the r18 U_z discipline) — latent
  future-use risk if any later version keys off it.
- Kicker-scale accumulation: 6*|dX|/X pays per step on pulses —
  measured worst battery edge 0.73 (sub-farmable), disclosed.
- Re-basing lag exploitation: the capped flow lags fast moves by
  construction (the r17 responsiveness class — design lag, not an
  extraction).

Run: .venv/bin/python scripts/r19_answer_redteam.py
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

GAME = GameTheoryReport(
    summary=(
        "The single-magnet pool re-bases at a bounded rate: sustained "
        "moves arrive (verified numerically at 120/240-step windows — "
        "the r19 audit), oscillation leaves the slow EMA flat (no "
        "wash harvest; battery worst edge 0.73 measured). Residuals: "
        "the ±f_c flow cap has a FLAT marginal-cost zone just under "
        "the boundary (flow at 0.9*f_c costs the same as at 0.5*f_c — "
        "the r18 Symmetric-Cap red-team finding, same shape here); "
        "the stress memory S_w is disclosure-only today but "
        "pre-loadable by sustained moderate |dX| for any future "
        "version that keys off it."
    ),
    attack_vectors=[
        AV(vector="Flow-cap boundary riding",
           description=("Ride the flat zone just under the ±f_c cap "
                        "where more flow costs the same as less."),
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
        AV(vector="Stress-memory pre-loading",
           description=("Sustained moderate |dX| feeds S_w; it keys "
                        "nothing today (latent only)."),
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
    ],
    equilibria_notes=(
        "Floor-pin: closed (floor 250 below crash 400, verified "
        "arriving). Wash harvest: closed (0.73 measured). Residuals: "
        "boundary riding + latent S_w pre-loading."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.1,
)

SEC = SecurityReport(
    summary=(
        "Clips bracket battery extremes; the bounded-step regime EMA "
        "(±500/step, value clip 100..9000) cannot saturate at battery "
        "scales (extremes reach 700k — verified distinct 13/13); the "
        "kicker measured 0.73 worst (sub-farmable)."
    ),
    attack_vectors=[
        AV(vector="Kicker-scale accumulation",
           description=("Pulse |dX| steps to farm the 6*|dX|/X kicker; "
                        "measured worst 0.73 — nuisance scale."),
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="FACT"),
    ],
    hardest_attack_to_defend=(
        "Flow-cap boundary riding: the flat region is the cap's own "
        "price — fixable by a quadratic ramp (the r18 pattern)."
    ),
    security_score=7.1,
)

ORC = OracleReport(
    summary="Sole exogenous input is the level; the regime EMA is deterministic.",
    data_source_assessment="Level series only; bounded-step gates.",
    manipulation_vectors=[
        AV(vector="Level-feed grinding (out-of-model)",
           description="A majority feed grinding the level; feed "
                       "diversification is infrastructure.",
           attacker="oracle_provider", profitable_for_attacker=False,
           requires_collusion=True, evidence_level="HYPOTHESIS"),
    ],
    oracle_feasibility_score=7.2,
)

RED = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Flow-cap boundary riding: the ±f_c cap leaves a flat "
        "marginal-cost zone just under the boundary — flow pushed to "
        "0.9*f_c costs the same per step as flow at half the cap, so "
        "a rider takes maximum bounded flow at minimum marginal cost; "
        "and the stress memory S_w accumulates the rider's own "
        "sustained |dX| (disclosure-only today — the latent risk is "
        "any future version keying off it)."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AV(vector="Flow-cap boundary riding",
           description="Ride the flat zone under the cap.",
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
        AV(vector="Stress-memory pre-loading",
           description="Sustained |dX| pre-loads S_w (latent).",
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="HYPOTHESIS"),
        AV(vector="Kicker-scale accumulation",
           description="Pulse farming; 0.73 measured (nuisance).",
           attacker="arbitrageur", profitable_for_attacker=True,
           evidence_level="FACT"),
    ],
    what_would_save_it=(
        "A quadratic ramp near the f_c boundary (monotone marginal "
        "cost — the r18 Symmetric-Cap v2 fix pattern) closes the "
        "boundary zone; S_w stays disclosure-only by explicit "
        "constraint (nothing keys off it; testable invariant)."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "2b188b0f9865c4d4": SEC,
        "72c374e57b6d603d": RED,
        "9b99a2a1376137f9": GAME,
        "de6d6034c65b7af0": ORC,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
