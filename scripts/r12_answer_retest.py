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
        "The v2 counter-gated escalation breaks the transient-farming "
        "equilibrium: the counter C_t is an EMA of the SLOW-EMA's own "
        "movement, so oscillation (X moves, T flat) leaves it at zero "
        "while genuine re-centering accumulates it — repeated "
        "engineered shifts pay escalating bond drains (rho_c*C_t*8) and "
        "receive deflated compensation (rho_c*C_t*4), strictly "
        "net-negative per cycle after the first. The intra-band "
        "free-rider remains as a bounded calibration equilibrium: "
        "margin-inside bands earn fees without exceedance exposure — "
        "but the free-rider carries no extraction path against the "
        "pools (no forfeit event to harvest), only a band-quality "
        "dilution that fee competition prices."
    ),
    attack_vectors=[
        AV(
            vector="Residual intra-band free-riding (no extraction path)",
            description=(
                "Margin-inside bands collect fees without forfeit "
                "exposure; the residual is band-quality dilution priced "
                "by reporter fee competition, not pool extraction — "
                "unprofitable as an attack on the mechanism's funds."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    equilibria_notes=(
        "Sustained exceedance: forfeit 1.2x vs compensation 0.5x — "
        "net-negative. Repeated shifts: escalating drain vs deflated "
        "payout 2:1 — net-negative after cycle one. Oscillation: "
        "counter flat, divergence flat — no path. The remaining "
        "equilibrium is honest narrow banding."
    ),
    death_spiral_risk=2.0,
    game_theory_score=7.5,
)

sec = SecurityReport(
    summary=(
        "v2 keeps every state clip-bounded; the counter's own clip "
        "(0..300) bounds the escalation terms (max 240 drain / 120 "
        "deflation per step) within pool floors. No comparison "
        "operators; all terms arithmetic. The counter's re-keying to "
        "slow-EMA movement closes the v1-draft regression where "
        "oscillation-driven |X-T| pumped the escalation."
    ),
    attack_vectors=[
        AV(
            vector="Residual parameter-boundary exposure (bounded)",
            description=(
                "Boundary riders face the 250-threshold asymmetric "
                "accumulation plus the counter-gated escalation; the "
                "residual exposure is bounded by the min() caps and "
                "pool floors — no unbounded path exists."
            ),
            attacker="arbitrageur",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    hardest_attack_to_defend=(
        "Intra-band free-riding (information dilution, not fund "
        "extraction) — mitigated by band-fee competition outside the "
        "model."
    ),
    security_score=7.3,
)

orc = OracleReport(
    summary=(
        "The counter keys the slow EMA's own movement, so anchor-path "
        "shaping between EMA speeds now accumulates escalation costs "
        "on the shaper: each shaped cycle moves the slow EMA, raising "
        "the counter, and the drain compounds while compensation "
        "deflates. Oracle risk reduces to anchor integrity, "
        "out-of-model (median-of-feeds)."
    ),
    data_source_assessment=(
        "Anchor level X_t sole exogenous input; gate and counter are "
        "computed, never reported."
    ),
    manipulation_vectors=[
        AV(
            vector="Residual anchor-integrity exposure (out-of-model)",
            description=(
                "Majority anchor corruption moves the slow EMA at will; "
                "the counter escalates costs but a corrupted feed "
                "wins by definition — mitigation is feed "
                "diversification outside the model."
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
        "Residual intra-band free-riding: margin-inside bands earn "
        "fees without exceedance exposure — but it dilutes band "
        "quality rather than extracting pool funds; no profitable "
        "extraction path against the v2 pools exists (sustained "
        "exceedance forfeits 2.4x what it pays; repeated shifts "
        "escalate; oscillation measures nothing)."
    ),
    strongest_attack_is_profitable=False,
    attack_vectors=[
        AV(
            vector="Residual intra-band free-riding (no extraction path)",
            description=(
                "Band-quality dilution priced by fee competition; no "
                "pool-drain path."
            ),
            attacker="oracle_provider",
            profitable_for_attacker=False,
            evidence_level="HYPOTHESIS",
        ),
    ],
    what_would_save_it=(
        "Out-of-model: band-quality-weighted reporter rewards; "
        "in-model the extraction paths (exceedance, shifts, "
        "oscillation) are all closed and measured."
    ),
)

p = AgentBridgeProvider()
for rid, ans in [('4f3df6ccd30fdacb', game), ('892b1ecd30ef1b70', sec),
                 ('975d80bf84f6c9f8', orc), ('dc99c923ebc0a905', red)]:
    p.install_answer(rid, ans.model_dump(mode='json'))
    print('installed', rid, type(ans).__name__)
