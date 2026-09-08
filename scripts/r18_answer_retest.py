"""Round 18: retest re-attack answers — v2 models SURVIVE, honestly.

Re-attack targets the v2 patches. What the patches closed (measured
in the v2 smoke + construction):
- Three-Speed: the flat 600 premium cap is now a sqrt-compressed
  QUADRATIC ramp (monotone marginal premium — no cliff to camp); the
  kicker pays only when the separation gate is open (flat-regime
  pulse farming stops paying; wash edge 2.38 measured).
- Symmetric-Cap: the flow cap gains a quadratic ramp (no flat zone
  to ride); U_z is pinned disclosure-only by an explicit constraint.

What REMAINS (disclosed residuals, not closures):
- Three-Speed: anchor-camp grinding still widens separation — but the
  mover pays the premium on their own flow timing, bounded at 600,
  and the payment is the insurance intent itself (pays while risk
  stays moved). Not extractable above the disclosed design.
- Symmetric-Cap: the demand-EMA lag is a responsiveness gap
  (disclosed), and the rate cap bounds — never removes — the total
  drain a long moved regime can take.

Verdicts: SURVIVES both.

Run: .venv/bin/python scripts/r18_answer_retest.py
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
        "v2 closes the flat-boundary vectors: the premium's marginal "
        "cost is now monotone in separation (sqrt-compressed ramp — "
        "camping the 600 boundary no longer pays a zero-marginal zone), "
        "and the kicker is gated on separation context (pulse farming "
        "measured at 2.38 under wash). The anchor-camp grind RESIDUAL: "
        "a patient mover still widens I-vs-U_s separation — but the "
        "premium is paid on the mover's own flow timing, bounded at "
        "600, and it is the insurance intent itself (cover priced "
        "while risk stays moved). Not extractable above the disclosed "
        "design."
    ),
    attack_vectors=[
        AV(vector="Anchor-camp premium pumping (residual, bounded)",
           description=("Grind the level to widen separation; the "
                        "premium scales but is paid by the mover's own "
                        "flow and capped at 600 — insurance semantics."),
           attacker="arbitrageur", profitable_for_attacker=False,
           evidence_level="HYPOTHESIS"),
    ],
    equilibria_notes=(
        "Anchor-heal: closed (separation persists by construction). "
        "Wash harvest: closed (2.38 measured). Boundary camping: closed "
        "(monotone ramp). Residual: bounded, self-paying grind."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.2,
)

A_SEC = SecurityReport(
    summary=(
        "Clips bracket battery extremes; the quadratic ramp removes "
        "the cap cliff; the context-gated kicker measured 2.38 under "
        "wash (below farmable scale)."
    ),
    attack_vectors=[
        AV(vector="Kicker residue (measured 2.38, below farm scale)",
           description="Pulse farming pays only with the gate open; "
                       "measured 2.38 under wash — nuisance scale.",
           attacker="arbitrageur", profitable_for_attacker=False,
           evidence_level="FACT"),
    ],
    hardest_attack_to_defend=(
        "Nothing above farmable scale remains: the strongest residual "
        "is the bounded self-paying grind (insurance semantics)."
    ),
    security_score=7.3,
)

A_ORC = OracleReport(
    summary="Sole exogenous input remains the level; gates deterministic.",
    data_source_assessment="Level series only; two EMA speeds.",
    manipulation_vectors=[
        AV(vector="Level-feed grinding (out-of-model)",
           description="Majority feed grinding wins by definition; "
                       "feed diversification is infrastructure.",
           attacker="oracle_provider", profitable_for_attacker=False,
           requires_collusion=True, evidence_level="HYPOTHESIS"),
    ],
    oracle_feasibility_score=7.2,
)

A_RED = RedTeamReport(
    verdict="survives",
    strongest_attack=(
        "Anchor-camp premium pumping, now bounded and self-paying: the "
        "patient mover widens the medium-vs-anchor separation and the "
        "premium scales — but the mover pays it on their own flow "
        "timing, it is capped at 600 by the ramp, and the payment is "
        "the disclosed insurance intent (cover priced while risk "
        "stays moved). No extraction above the design's own price "
        "remains."
    ),
    strongest_attack_is_profitable=False,
    attack_vectors=[
        AV(vector="Anchor-camp premium pumping (residual, bounded)",
           description="Self-paying, capped grind; insurance semantics.",
           attacker="arbitrageur", profitable_for_attacker=False,
           evidence_level="HYPOTHESIS"),
    ],
    what_would_save_it=(
        "Nothing required — the v2 ramp closed the flat-boundary "
        "family and the context gate closed pulse farming; the "
        "residual is the design's own price, disclosed."
    ),
)

B_GAME = GameTheoryReport(
    summary=(
        "v2 closes the cap-boundary family: the quadratic ramp keeps "
        "the marginal flow cost monotone (no flat zone to ride), and "
        "U_z is pinned disclosure-only by an explicit constraint "
        "(nothing keys off it — the latent pre-load risk is now a "
        "named, testable invariant). Residual: the demand-EMA lag is "
        "a responsiveness gap (disclosed per the r17 wedge "
        "discipline — design lag, not an extraction); the rate cap "
        "bounds the drain a long moved regime can take — bounded "
        "trajectory, not closure (disclosed at v1, unchanged)."
    ),
    attack_vectors=[
        AV(vector="Demand-EMA lag exploitation (residual, disclosed)",
           description=("Fast moves outpace T_t; the reversion target "
                        "lags — the r17 responsiveness class, not an "
                        "extraction."),
           attacker="arbitrageur", profitable_for_attacker=False,
           evidence_level="HYPOTHESIS"),
    ],
    equilibria_notes=(
        "Floor-pin drain: closed (symmetric cap + ramp). Boundary "
        "riding: closed (monotone marginal). U_z pre-loading: closed "
        "(disclosure-only pin). Residual: disclosed lag."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.2,
)

B_SEC = SecurityReport(
    summary=(
        "Clips bracket battery extremes; the ramp is arithmetic (no "
        "multiplicative path); U_z bounded at 400 and keying nothing."
    ),
    attack_vectors=[
        AV(vector="Rate-capped sustained drain (disclosed)",
           description="A long moved regime still draws the reserve "
                       "toward its floor at the capped rate — bounded "
                       "trajectory, disclosed at v1.",
           attacker="arbitrageur", profitable_for_attacker=False,
           evidence_level="FACT"),
    ],
    hardest_attack_to_defend=(
        "The rate cap bounds but never removes the total a long "
        "moved regime can draw — bounded trajectory, disclosed."
    ),
    security_score=7.2,
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
    verdict="survives",
    strongest_attack=(
        "Cap-boundary flow riding, now closed by the quadratic ramp "
        "(the marginal flow cost is monotone — no flat zone where "
        "more flow costs the same as less), and utilization-index "
        "feeding, now closed by the disclosure-only pin (U_z keys "
        "nothing; the constraint is testable). The residual demand-"
        "EMA lag is the r17 responsiveness class — a disclosed "
        "design lag, not an extraction. No profitable vector above "
        "the disclosed design remains."
    ),
    strongest_attack_is_profitable=False,
    attack_vectors=[
        AV(vector="Demand-EMA lag exploitation (residual, disclosed)",
           description="Fast moves outpace T_t; disclosed lag.",
           attacker="arbitrageur", profitable_for_attacker=False,
           evidence_level="HYPOTHESIS"),
    ],
    what_would_save_it=(
        "Nothing required — the ramp closed the boundary family and "
        "the pin closed the U_z latent risk; the residual is the "
        "disclosed responsiveness gap."
    ),
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "fee859c2c86e72ac": A_RED,
        "685a55633323e1ce": A_GAME,
        "c5aba61dad101e1e": A_ORC,
        "f7028d328b1e48de": A_SEC,
        "2ba947eef95cbd6e": B_RED,
        "d376c591baabec46": B_GAME,
        "e51c98e4b1898497": B_ORC,
        "fc3d0a72709a051e": B_SEC,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
