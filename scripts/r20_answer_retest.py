"""Round 20: retest re-attack answers (against v2 as stored).

The stored v2 carries the symmetric clip band (correct) but its
counter keys movement MAGNITUDE — the honest re-attack finds both
the counter's threshold blind spot AND the genuine-lead deadness
(the functionality failure the smoke probe caught before install).

Run: .venv/bin/python scripts/r20_answer_retest.py
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
        "v2's symmetric clip band closes the original saw-tooth bias "
        "(the cycling average now converges to the band center). "
        "But the saw-tooth counter C_t keys movement MAGNITUDE "
        "(|kappa_f*(X-L_f)|/8): two consequences — (1) any saw-tooth "
        "whose per-step moves stay small enough to keep the "
        "fast-EMA movement under the counter's threshold never "
        "raises C_t, and the separation key rides the alternation "
        "(the bias returns through the discount's blind spot); "
        "(2) any GENUINE fast move also has large fast-EMA movement, "
        "so C_t pins at 1.0 and retention stays at base through "
        "real sustained pressure — the smoothing function fails "
        "exactly when it is genuinely needed."
    ),
    attack_vectors=[
        AttackVector(
            vector="slow saw-tooth under the counter threshold",
            description=(
                "Craft a zero-mean saw-tooth with small per-step "
                "moves (fast-EMA movement < 8, the counter's "
                "normalization): C_t stays ~0, the separation key "
                "rides every alternation, and the symmetric band "
                "still lets up-legs push retention +0.25 while "
                "down-legs pull only -0.25 — the average can exceed "
                "base whenever the saw-tooth's positive legs are "
                "longer-lived than its negative legs (duty-cycle "
                "bias within the band)"
            ),
            attacker="attacker",
            profitable_for_attacker=True,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
        AttackVector(
            vector="genuine-lead deadness (functionality failure)",
            description=(
                "The counter pins at 1.0 under any sustained move "
                "with fast-EMA movement above 8 (a 3%/step grind "
                "measures C_t=1.0 throughout): retention never rises "
                "above base on REAL pressure — the escrow never "
                "builds its buffer when genuine stress arrives. "
                "Not directly attacker P&L, but the mechanism fails "
                "its core function under the conditions it exists for"
            ),
            attacker="unspecified",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="FACT",
        ),
    ],
    equilibria_notes=(
        "The magnitude threshold 8 creates a two-regime equilibrium: "
        "above it every path (crafted or genuine) is discounted "
        "equally; below it nothing is. The discriminator a fee "
        "escrow needs is sign persistence (alternation vs "
        "direction), not magnitude"
    ),
    death_spiral_risk=2.0,
    game_theory_score=5.0,
    evidence_level="INFERENCE",
)

SEC = SecurityReport(
    summary=(
        "The magnitude-normalized counter introduces a threshold "
        "boundary at fast-EMA movement = 8 — a flat zone below it "
        "where alternation passes undetected, and a cliff above it "
        "where genuine moves are discounted along with crafted ones. "
        "Both sides of the boundary are exploitable."
    ),
    attack_vectors=[
        AttackVector(
            vector="counter-threshold boundary riding",
            description=(
                "Saw-teeth calibrated to keep |kappa_f*(X-L_f)| "
                "just under 8: the counter reads ~0 and the "
                "separation key rides — the bias the counter was "
                "installed to remove returns at a smaller amplitude "
                "(bounded by the band half-width 0.25 and the "
                "duty-cycle asymmetry a saw-tooth can carry within "
                "the threshold)"
            ),
            attacker="attacker",
            profitable_for_attacker=True,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
        AttackVector(
            vector="genuine-stress buffer failure",
            description=(
                "Under real sustained stress (the scenario a fee "
                "escrow exists for) the counter discounts the "
                "retention response: the buffer target stays at "
                "base through the stress window — a solvency risk "
                "for the escrow's smoothing promise, disclosed as a "
                "functionality failure rather than an extraction"
            ),
            attacker="unspecified",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="FACT",
        ),
    ],
    hardest_attack_to_defend=(
        "The threshold riding: any magnitude-based discriminator has "
        "a flat zone under its threshold; the fix is a SIGN-"
        "PERSISTENCE key (alternation vs direction) which has no "
        "amplitude threshold to ride"
    ),
    security_score=4.5,
    evidence_level="INFERENCE",
)

ORACLE = OracleReport(
    summary=(
        "No external oracle; the added counter state derives "
        "locally from the level path. The oracle-relevant finding: "
        "the counter's magnitude normalization (8) is an implicit "
        "calibration oracle — a threshold chosen against today's "
        "move sizes that misclassifies tomorrow's genuine regimes "
        "(larger genuine moves -> counter pins -> retention dead)."
    ),
    data_source_assessment=(
        "X_t/dX_t on-chain series; fast/slow EMAs and the counter "
        "derive locally — no third-party dependency. The "
        "normalization constant is the only calibration surface"
    ),
    manipulation_vectors=[
        AttackVector(
            vector="calibration-threshold misclassification",
            description=(
                "Any genuine regime with step moves above the "
                "counter's normalization reads as 'oscillation' to "
                "the counter — retention stays at base through real "
                "stress (the deadness finding from the oracle side: "
                "the threshold is an implicit assumption about "
                "normal move sizes)"
            ),
            attacker="unspecified",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="FACT",
        ),
    ],
    oracle_feasibility_score=6.0,
    evidence_level="FACT",
)

RED = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Counter-threshold boundary riding: a saw-tooth calibrated "
        "under the counter's magnitude threshold (fast-EMA movement "
        "< 8) keeps C_t ~0 while the separation key rides every "
        "alternation — with duty-cycle asymmetry inside the "
        "symmetric band, the retention time-average exceeds base on "
        "a zero-mean path. The magnitude-keyed counter re-opens "
        "the saw-tooth class it was installed to close, at reduced "
        "amplitude; and its other side is worse: genuine sustained "
        "pressure pins the counter and the smoothing function "
        "fails when it is truly needed (retention flat at base "
        "through a 3%/step grind — measured)."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AttackVector(
            vector="counter-threshold boundary riding",
            description=(
                "Slow zero-mean saw-teeth under the counter's "
                "magnitude threshold: C_t ~0, the separation key "
                "rides, duty-cycle asymmetry inside the ±0.25 band "
                "biases average retention above base"
            ),
            attacker="attacker",
            profitable_for_attacker=True,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
        AttackVector(
            vector="genuine-lead deadness",
            description=(
                "Magnitude keying discounts genuine pressure with "
                "crafted: retention flat 0.300 through a 3%/step "
                "sustained grind (measured) — the buffer never "
                "builds under real stress"
            ),
            attacker="unspecified",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="FACT",
        ),
    ],
    what_would_save_it=(
        "Key the counter to separation SIGN PERSISTENCE (g_t*G_t "
        "with G_t the lagged separation): alternation (product "
        "negative) raises the counter regardless of amplitude — "
        "no threshold to ride; persistence (product positive, a "
        "genuine followed lead) decays it — the genuine response "
        "is preserved. Sign has no magnitude threshold"
    ),
    evidence_level="INFERENCE",
)


def main() -> None:
    p = AgentBridgeProvider()
    for rid, ans in [
        ("c88074c336171934", GAME),
        ("81fa9d4b0a19d01e", SEC),
        ("614a065eb45b8c8c", ORACLE),
        ("82efd51dc0ff4c8e", RED),
    ]:
        p.install_answer(rid, ans.model_dump(mode="json"))
        print(f"installed {rid} {type(ans).__name__}")


if __name__ == "__main__":
    main()
