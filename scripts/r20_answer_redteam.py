"""Round 20: red-team answers for the retention-ratchet successor.

DESTROY THE IDEA (§9): four adversarial reports against the
Separation-Keyed Fee Smoothing Escrow v1 — honest vectors, verdict
VULNERABLE where the strongest play is profitable.

Run: .venv/bin/python scripts/r20_answer_redteam.py
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
        "The signed-separation retention key closes the resonance "
        "ratchet (the r20 predecessor flaw: absolute-vol retention "
        "pinned at the 0.9 ceiling every ramp). The adversarial "
        "surface that remains: any play that holds the FAST-vs-SLOW "
        "separation positive for long windows without paying a "
        "proportional move cost — or that farms the buffer's "
        "REVERSION speed (lam_e) rather than its size."
    ),
    attack_vectors=[
        AttackVector(
            vector="sustained-lead retention farming",
            description=(
                "A whale grinds the level up at a steady +0.5%/step "
                "(sub-spike): the fast EMA leads the slow anchor by a "
                "stable ~+4%, retention pins near 0.36-0.9, and the "
                "buffer target 1000 + 18*r_t inflates ~6 units above "
                "anchor — the escrow holds fees the attacker's own "
                "grind priced in. The move cost is real but the "
                "buffer delta persists as long as the grind does"
            ),
            attacker="whale",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
        AttackVector(
            vector="buffer-reversion front-running",
            description=(
                "The escrow converges to its target at lam_e=0.15: a "
                "predictable ~7-step half-life. An attacker who "
                "knows the target path can time fee INFLow windows "
                "(when target > current escrow, retained inflow is "
                "locked at high retention) and fee USE windows "
                "(after the target falls) — extracting the "
                "convergence spread itself"
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="HYPOTHESIS",
        ),
        AttackVector(
            vector="separation-key oscillation wash",
            description=(
                "Zero-mean cycling averages the separation key to "
                "~0 — the design's stated immunity. But the clip "
                "floor 0.1 makes retention ASYMMETRIC around zero "
                "mean: down-legs release to 0.1 while up-legs retain "
                "to 0.9, so a 50/50 saw-tooth (slow down, fast up) "
                "could bias the time-average of r_t above delta_r"
            ),
            attacker="attacker",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Under cycling the escrow converges to the cycle-average of "
        "its target (measured heads [0,0,0,0] at N=2/4/8/16) — the "
        "ratchet equilibrium is closed. The remaining equilibria are "
        "reversion-spread plays (bounded by the cap 18) and "
        "saw-tooth retention bias (bounded by the clip band width "
        "0.8 * the buffer multiplier — second-order)"
    ),
    death_spiral_risk=2.0,
    game_theory_score=6.5,
    evidence_level="INFERENCE",
)

SEC = SecurityReport(
    summary=(
        "Attack surface: the retention key and the escrow target are "
        "both deterministic functions of the level path — fully "
        "observable, hence front-runnable in principle. The hardest "
        "defendable play is the saw-tooth: clip asymmetry around "
        "zero-mean separation biases retention upward without any "
        "net level move."
    ),
    attack_vectors=[
        AttackVector(
            vector="saw-tooth retention bias",
            description=(
                "Craft dX with slow negative legs (separation deeply "
                "negative, retention pinned at the 0.1 floor) and "
                "fast positive legs (separation positive, retention "
                "rises to the 0.9 ceiling): the clip band 0.1..0.9 is "
                "not symmetric around delta_r=0.3, so the "
                "time-average of retention exceeds the base 0.3 — "
                "the escrow target inflates on a ZERO-MEAN path"
            ),
            attacker="attacker",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
        AttackVector(
            vector="observable-path front-running",
            description=(
                "All keying states are public EMAs of the level: the "
                "escrow's target path is predictable ~7 steps ahead; "
                "fee-payers can time around high-retention windows, "
                "leaving the escrow holding adverse fees (a adverse-"
                "selection vector on fee inflow, not on the escrow "
                "stock itself)"
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="HYPOTHESIS",
        ),
        AttackVector(
            vector="anchor-drift stale-band hold",
            description=(
                "After a genuine one-sided regime break, the slow "
                "anchor trails for ~1/kappa_s steps; retention keys "
                "the stale separation and over-retains through the "
                "break's recovery leg — a transient overcharge "
                "window proportional to the anchor lag"
            ),
            attacker="liquidity_provider",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
    ],
    hardest_attack_to_defend=(
        "The saw-tooth: the clip band's asymmetry around the base "
        "retention converts zero-mean cycling into a positive "
        "retention bias — defending requires either a symmetric clip "
        "band or a frequency key that discounts saw-tooth paths"
    ),
    security_score=6.0,
    evidence_level="INFERENCE",
)

ORACLE = OracleReport(
    summary=(
        "No external oracle: all keying states are deterministic "
        "EMAs of the on-chain level series (X_t, dX_t). The oracle "
        "surface is the level feed itself — manipulable to the "
        "extent a whale can move the level (the battery's premise)."
    ),
    data_source_assessment=(
        "X_t/dX_t anchor series: on-chain observable, attacker-"
        "influenceable within the battery's crafted-move envelope; "
        "fast/slow EMAs and the separation key derive locally — no "
        "third-party data dependency, no reporting oracle, no "
        "cross-chain bridge"
    ),
    manipulation_vectors=[
        AttackVector(
            vector="level-feed manipulation via crafted moves",
            description=(
                "The attacker's whole choreography arsenal (spike, "
                "wash, resonance) IS the manipulation of the level "
                "feed; the design's defense is that every keying "
                "state keys SIGNED or slow-averaged quantities that "
                "average out zero-mean paths — measured: resonance "
                "heads [0,0,0,0]"
            ),
            attacker="whale",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="FACT",
        ),
        AttackVector(
            vector="stale-anchor oracle window",
            description=(
                "The slow EMA is an implicit internal oracle with a "
                "~17-step half-life; during genuine breaks its "
                "reports are stale and the separation key amplifies "
                "transient overcharge — bounded, disclosed, no "
                "profitable path identified"
            ),
            attacker="unspecified",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
    ],
    oracle_feasibility_score=7.5,
    evidence_level="FACT",
)

RED = RedTeamReport(
    verdict="vulnerable",
    strongest_attack=(
        "Saw-tooth retention bias: the retention clip band 0.1..0.9 "
        "is asymmetric around the base delta_r=0.3, so a crafted "
        "zero-mean saw-tooth (slow negative separation legs, fast "
        "positive legs) biases the time-average retention above "
        "base and inflates the escrow target without any net level "
        "move — the resonance class re-entering through the clip "
        "band's asymmetry rather than through absolute-vol keying"
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AttackVector(
            vector="saw-tooth retention bias",
            description=(
                "Slow-down/fast-up crafted cycles: down legs pin "
                "retention at 0.1, up legs ride toward 0.9; the "
                "time-average of retention exceeds 0.3 on a "
                "zero-mean path, inflating the buffer target "
                "(1000 + 18*r_t) persistently while the cycling "
                "continues"
            ),
            attacker="attacker",
            profitable_for_attacker=True,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
        AttackVector(
            vector="reversion-spread timing",
            description=(
                "The escrow's lam_e=0.15 convergence makes the "
                "target path predictable ~7 steps out; timing fee "
                "inflow windows against the convergence spread "
                "extracts the spread — bounded by the cap 18"
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="HYPOTHESIS",
        ),
        AttackVector(
            vector="stale-anchor overcharge window",
            description=(
                "After genuine breaks the slow anchor trails ~17 "
                "steps; retention over-charges through the recovery "
                "leg — a disclosed responsiveness gap, no profitable "
                "attacker path identified"
            ),
            attacker="liquidity_provider",
            profitable_for_attacker=False,
            requires_collusion=False,
            evidence_level="INFERENCE",
        ),
    ],
    what_would_save_it=(
        "Symmetrize the retention clip around the base (clip "
        "delta_r ± 0.4 rather than 0.1..0.9 asymmetric), or key a "
        "frequency counter (the r12 transient-counter primitive) "
        "that discounts paths whose fast/slow EMAs saw-tooth — "
        "measured zero-mean bias is the design's own claim; make "
        "the clip band honest to it"
    ),
    evidence_level="INFERENCE",
)


def main() -> None:
    p = AgentBridgeProvider()
    for rid, ans in [
        ("e9adbaf9db13130d", GAME),
        ("2983f3cbd488a374", SEC),
        ("733ebcf935ed1156", ORACLE),
        ("65f8b3eca5456725", RED),
    ]:
        p.install_answer(rid, ans.model_dump(mode="json"))
        print(f"installed {rid} {type(ans).__name__}")


if __name__ == "__main__":
    main()
