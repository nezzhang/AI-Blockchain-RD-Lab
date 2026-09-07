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
        "The divergence gate matches the forecaster's actual claim "
        "(a sustained level path): zero-mean oscillation flattens both "
        "level-EMAs, so wash extraction is structurally closed, and a "
        "permanent shift costs one bounded re-centering transient. The "
        "rational attack surface moves to the gate's calibration: a "
        "patient reporter who sits JUST inside the divergence band "
        "collects band fees while contributing no information — a "
        "free-rider equilibrium the forfeit rule cannot reach because "
        "the reporter never exceeds."
    ),
    attack_vectors=[
        AV(
            vector="Intra-band free-riding on divergence gate",
            description=(
                "A reporter whose band always sits marginally inside "
                "the divergence gate collects fees with zero forfeit "
                "exposure; if enough reporters do this the meter's "
                "band quality degrades to the gate boundary itself."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Repeated regime-shift farming of the transient",
            description=(
                "An attacker engineering alternating permanent shifts "
                "harvests the re-centering transient's stabilization "
                "payout each cycle — bounded per cycle (40/step kicker "
                "and integral caps) but positive."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "The 1.2:0.5 forfeit/compensation ratio keeps every sustained "
        "EXCEEDANCE strategy net-negative; the residual equilibrium is "
        "inside the band, where the meter pays for information it does "
        "not receive — a calibration question, not an extraction path."
    ),
    death_spiral_risk=2.5,
    game_theory_score=7.0,
)

sec = SecurityReport(
    summary=(
        "All states clip-bounded; the EMA clips (200..3000) are wide "
        "enough that battery extremes do not saturate the gate (the "
        "r11 saturation defect). No comparison operators, arithmetic "
        "only; the transient kicker is capped at 40/step. The residual "
        "security surface is parameter choice: band and omega trade "
        "re-banding cost against gate sensitivity."
    ),
    attack_vectors=[
        AV(
            vector="Parameter-boundary squeeze",
            description=(
                "An attacker with knowledge of band/omega calibration "
                "rides the divergence gate's edge: enough sustained "
                "divergence to collect stabilization flow while under "
                "the asymmetric-accumulation threshold (250)."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "The intra-band free-rider: the meter cannot distinguish a "
        "band riding the gate boundary from an honest narrow forecast "
        "without a second information source."
    ),
    security_score=6.8,
)

orc = OracleReport(
    summary=(
        "The mechanism consumes only the anchor level series; the "
        "divergence gate is computed, not reported. Oracle risk "
        "concentrates in anchor integrity, as with every design in "
        "this family — median-of-feeds remains the out-of-model "
        "mitigation."
    ),
    data_source_assessment=(
        "Anchor level X_t is the sole exogenous input; feed "
        "diversification hardens the gate without changing semantics."
    ),
    manipulation_vectors=[
        AV(
            vector="Anchor path shaping between EMA speeds",
            description=(
                "A majority anchor provider shapes the path so the "
                "fast EMA persistently leads the slow one just beyond "
                "the band, farming the transient kicker cycle by cycle."
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
        "Intra-band free-riding: a reporter sitting marginally inside "
        "the divergence gate collects band fees with zero forfeit "
        "exposure — the meter pays for boundary-riding instead of "
        "information, degrading band quality to the gate edge."
    ),
    strongest_attack_is_profitable=True,
    attack_vectors=[
        AV(
            vector="Intra-band free-riding on divergence gate",
            description=(
                "Margin-inside bands collect fees with no exceedance "
                "exposure; band quality converges to the gate boundary."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
        AV(
            vector="Repeated regime-shift farming of the transient",
            description=(
                "Alternating engineered shifts harvest the bounded "
                "re-centering payout each cycle."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=True,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "A band-QUALITY term in reporter rewards (pay for forecast "
        "tightness INSIDE the band, not just band membership) plus a "
        "per-reporter transient-frequency penalty — repeated shift-"
        "harvest costs more than each payout."
    ),
)

p = AgentBridgeProvider()
for rid, ans in [('21532b0444002cfd', orc), ('be42fd6e7cbacbce', game),
                 ('dab24a4b9e78a1fe', red), ('fd98bedae4a464ac', sec)]:
    p.install_answer(rid, ans.model_dump(mode='json'))
    print('installed', rid, type(ans).__name__)
