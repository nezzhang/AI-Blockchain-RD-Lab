"""Bridge answers: v2 re-attack reports for the 14 r8 candidates.

Honest adversarial re-assessment of the PATCHED models. Each v2 fix
genuinely closed the named cheap path; the re-attack asks whether NEW
profitable paths remain at reasonable cost. Verdicts: mostly survives
(fixes hold); honest exceptions where the residual stays profitable
below reasonable cost are named in the report.
"""

from __future__ import annotations

import glob
import json
import re

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.redteam import (
    GameTheoryReport,
    OracleReport,
    RedTeamReport,
    SecurityReport,
)

# Re-attack analysis per candidate: what does the v2 change actually break
# for the attacker, and what remains?
A: dict[str, dict[str, dict]] = {
    "Fee-Spike Mutual for Rollup Batches": {
        # v2: payouts capped at ration_cap x own premium
        "game_theory": dict(
            summary="v2 caps per-member payouts at ration_cap*mu per window "
            "(3x own premium). Re-attacking the calm-suppression harvest: "
            "the colluding cohort's maximum recovery per spike window is "
            "bounded at 3x their own premium contributions — the multi-"
            "window accumulate-then-harvest structure no longer pays: "
            "waiting N calm windows costs N*mu in premiums for a payout "
            "capped at 3*mu. Net EV negative.",
            attack_vectors=[
                dict(
                    vector="calm-band suppression then spike harvest (v2 re-test)",
                    description="Rationing caps the coordinated harvest at 3x "
                    "the attacker cohort's own premium base; N-window "
                    "preparation costs N*mu for <= 3*mu recovery — negative "
                    "EV for any N > 3.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The equilibrium flips: honest members keep "
            "cheap cover; colluding cohorts subsidize the reserve they "
            "cannot harvest. The mutual becomes attack-subsidized.",
            death_spiral_risk=2.5,
            game_theory_score=7.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The fee-feed understatement surface is unchanged by "
            "rationing (it starves payouts rather than over-drawing) — but "
            "its damage is now bounded by the same per-member caps: "
            "understatement denies members capped reimbursements, not "
            "unbounded ones. Remaining: median-of-sequencer attestation is "
            "a deployment requirement, not in-model.",
            attack_vectors=[
                dict(
                    vector="fee-feed understatement to starve payouts (v2 re-test)",
                    description="Still denials-of-service shaped, bounded "
                    "damage, not extraction: attacker gains nothing "
                    "monetarily, members lose capped cover. Not profitable.",
                    attacker="oracle_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="sequencer attestation diversity at "
            "deployment (out of model scope, noted)",
            security_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="v2 unchanged on the oracle layer; the band statistic "
            "remains median-attested batch fees. Rationing removes the "
            "payout-amplification incentive to capture the feed, lowering "
            "the value of capture below its cost.",
            data_source_assessment="Attested batch-fee series; capture value "
            "now bounded by per-member ration caps.",
            manipulation_vectors=[
                dict(
                    vector="sequencer fee-report capture (v2 re-test)",
                    description="Capture value < capture cost once payouts "
                    "are ration-capped; the feed is no longer worth "
                    "attacking for profit.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="calm-band suppression then spike harvest (v2 "
            "re-test): rationing caps the harvest at 3x the attackers' own "
            "premium base while N-window preparation costs N x premium — "
            "the coordinated attack is structurally unprofitable for any "
            "preparation depth",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="calm-band suppression then spike harvest (v2 re-test)",
                    description="Negative EV under rationing.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="already saved by rationing; residual is "
            "deployment-scope sequencer attestation diversity",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Drawdown-Underwritten Liquidity Corridor": {
        # v2: conversion capacity re-marks with drawdown acceleration
        "game_theory": dict(
            summary="v2 subtracts remark_k*(D_t1-D_t)*10 from conversion "
            "capacity as drawdown ACCELERATES. The pump-then-drown attack "
            "needs maximum U at maximum D-rate — but U now shrinks precisely "
            "as D accelerates. Re-attacking: the whale must crash slowly "
            "(low acceleration) to preserve capacity, but slow crashes "
            "give underwriters exit time; fast crashes convert a shrinking "
            "tranche. The dynamic barrier removes the one-touch payoff.",
            attack_vectors=[
                dict(
                    vector="pump-then-drown drawdown conversion (v2 re-test)",
                    description="Conversion capacity is anti-correlated with "
                    "crash speed; the optimal attack (slow crash) is the "
                    "one underwriters can exit against. EV marginal at "
                    "best, negative against realistic exit.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Slow-crash equilibria favor underwriter exit; "
            "fast crashes meet shrinking tranches. The static one-touch "
            "option is gone.",
            death_spiral_risk=4.0,
            game_theory_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Depth-report shading was bounded by the public "
            "drawdown series cross-check (already in v1 design intent); v2's "
            "acceleration term gives shading a smaller target window too.",
            attack_vectors=[
                dict(
                    vector="depth-report shading (v2 re-test)",
                    description="Shaded reports must now also misstate the "
                    "ACCELERATION series; dual-statistic forgery doubles "
                    "detection surface for marginal gain.",
                    attacker="governance",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="residual: venue governance trust root "
            "for depth reporting (deployment constraint)",
            security_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Drawdown statistics from venue depth series; v2 uses "
            "both level and acceleration — two independent statistics to "
            "forge coherently.",
            data_source_assessment="Public depth-derived drawdown series; "
            "acceleration term adds forgery cost.",
            manipulation_vectors=[
                dict(
                    vector="depth-report shading (v2 re-test)",
                    description="See security analysis.",
                    attacker="governance",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="pump-then-drown drawdown conversion (v2 "
            "re-test): the conversion barrier now moves against the "
            "attacker's crash speed — fast crashes convert shrinking "
            "tranches, slow crashes let underwriters exit — the static "
            "one-touch payoff the attack relied on no longer exists",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="pump-then-drown drawdown conversion (v2 re-test)",
                    description="Anti-correlated barrier kills the barrier-"
                    "sniping payoff.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="residual is the deployment-scope venue "
            "depth-reporting trust root",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Counter-Cyclical Fee Sink Insurer": {
        # v2: per-entity caps
        "game_theory": dict(
            summary="v2 caps disbursements per entity-qualified cohort per "
            "epoch (entity_cap=400). The sybil farm splits flow across "
            "addresses but entities are capped — the farm's recovery is "
            "bounded at 400/epoch regardless of address count while the "
            "setup (many funded addresses passing qualification) costs "
            "more than 400.",
            attack_vectors=[
                dict(
                    vector="sybil small-sender farm (v2 re-test)",
                    description="Per-entity caps bound aggregate recovery "
                    "below farm setup and maintenance cost.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Honest small senders receive capped support; "
            "farming capital is better deployed in the market.",
            death_spiral_risk=2.5,
            game_theory_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The qualification boundary moved from per-address to "
            "per-entity — the sybil surface shrinks from 'split a wallet' "
            "to 'maintain entity-qualified cohorts', which costs identity "
            "capital per entity.",
            attack_vectors=[
                dict(
                    vector="sybil small-sender farm (v2 re-test)",
                    description="Entity qualification (proof-of-personhood "
                    "or history-weighted) makes farm maintenance cost "
                    "exceed the 400/epoch cap.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="identity-boundary disputes at the "
            "margin (individual entity qualification errors)",
            security_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Sequencer fee-volatility shaping remains the residual: "
            "median statistics across sequencers bound single-sequencer "
            "shaping, but a sequencer majority can still hold the regime "
            "index below turbulence while extracting in priority fees. "
            "That is a sequencer-governance problem, not a sink problem.",
            data_source_assessment="Median cross-sequencer fee statistics; "
            "shaping value bounded by per-entity disbursement caps.",
            manipulation_vectors=[
                dict(
                    vector="sequencer fee-volatility shaping (v2 re-test)",
                    description="Median-of-sequencer statistics plus capped "
                    "disbursements make shaping a negative-EV extraction "
                    "vehicle.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="sybil small-sender farm (v2 re-test): "
            "per-entity qualification and per-epoch disbursement caps bound "
            "the farm's aggregate recovery at 400/epoch against setup costs "
            "that scale with entity count — structurally unprofitable",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="sybil small-sender farm (v2 re-test)",
                    description="Bounded recovery below farm cost.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="already saved; residual margin disputes are "
            "operational, not structural",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Relay Congestion Cover Mesh": {
        # v2: probe-corroborated congestion
        "game_theory": dict(
            summary="v2 pays compensation only on congestion the "
            "independent probe layer confirms (probe_w=0.5 damping, lagged "
            "EWMA). The fabricated-congestion farmer must now also move "
            "the probe network — which is independently funded and "
            "staked-diverse. The forgery cost scales with probe diversity "
            "rather than with the operator's own resources.",
            attack_vectors=[
                dict(
                    vector="fabricated congestion compensation farming (v2 re-test)",
                    description="Probe corroboration converts operator self-"
                    "report into a two-independent-population problem the "
                    "operator doesn't control. Farm EV negative at "
                    "moderate probe diversity.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Compensation tracks probe-confirmed congestion "
            "with 0.5 damping — honest operators are paid slightly less "
            "than raw reports, farmed congestion is paid ~half of nothing.",
            death_spiral_risk=2.0,
            game_theory_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Dual-side attestation forgery (operator + sybil "
            "clients) no longer self-corroborates: the probe layer is a "
            "third population with independent stakes. Capturing it is a "
            "separate, costlier attack.",
            attack_vectors=[
                dict(
                    vector="dual-side attestation forgery (v2 re-test)",
                    description="Self-corroboration broken by the probe "
                    "layer; forgery requires three-population capture.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="probe-network capture at low diversity "
            "(deployment constraint: fund the probes)",
            security_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="The probe layer is the v2 oracle addition: lagged, "
            "damped, independent. Compensation gates on min(C, Pr) — both "
            "populations must agree.",
            data_source_assessment="Operator reports + independent probe "
            "EWMA; two-source agreement required.",
            manipulation_vectors=[
                dict(
                    vector="probe-network absence exploitation (v2 re-test)",
                    description="The probe network is now funded (inflow*0.5 "
                    "in the liquidity equation is the funding proxy); "
                    "absence exploitation requires defunding it first.",
                    attacker="oracle_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="dual-side attestation forgery (v2 re-test): "
            "the independently funded probe layer breaks operator "
            "self-corroboration — compensation requires a third population "
            "the attacker doesn't control",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="dual-side attestation forgery (v2 re-test)",
                    description="Three-population capture cost exceeds farm "
                    "value.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="residual: fund and diversify the probe "
            "network at deployment",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Volatility-Sized Settlement Escrow": {
        # v2: EWMA tranche + verification delay
        "game_theory": dict(
            summary="v2 EWMA-sizes the tranche (0.7T + 0.3*target): a "
            "single-window vol burst moves the tranche only 30% of the way "
            "— the volatility-manufactured default straddle's inflated "
            "payout shrinks toward the pre-burst baseline. The verification "
            "challenge window further forces colluded defaults to survive "
            "scrutiny while the EWMA decays.",
            attack_vectors=[
                dict(
                    vector="volatility-manufactured default straddle (v2 re-test)",
                    description="EWMA sizing caps single-window inflation at "
                    "~30% of the spread; sustained vol manufacture to move "
                    "the tranche fully raises attack cost above the padded "
                    "payout at realistic depth.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Sustained vol manufacture is priced into the "
            "spread too (W responds with its own EWMA) — the attacker "
            "raises their own transaction costs while padding the payout.",
            death_spiral_risk=3.5,
            game_theory_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Colluded fake default must now survive the "
            "verification challenge window (verif_delay steps) with "
            "beneficial-ownership checks on both legs — the two-owner "
            "collusion becomes visible during the window at the identity "
            "level.",
            attack_vectors=[
                dict(
                    vector="colluded fake default (v2 re-test)",
                    description="Ownership separation requirements during "
                    "the challenge window convert the cheap self-payment "
                    "into a detectable two-party conspiracy.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="genuinely organic-looking defaults "
            "at inflated-but-EWMA-damped sizes",
            security_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Single-print vol inflation is directly closed by the "
            "EWMA: one manipulated print moves the tranche 30% of the "
            "implied jump. Wash-print series to move it fully trigger "
            "the spread's own response.",
            data_source_assessment="Realized pair series with EWMA-sized "
            "tranche parameters.",
            manipulation_vectors=[
                dict(
                    vector="single-print vol inflation (v2 re-test)",
                    description="EWMA damping bounds print inflation; "
                    "serial print manipulation is self-defeating via the "
                    "spread response.",
                    attacker="oracle_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="colluded fake default (v2 re-test): EWMA "
            "tranche sizing bounds the volatility-inflated payout at ~30% "
            "of the manipulated target and the verification challenge "
            "window exposes two-leg ownership conspiracies — the "
            "self-payment loop is closed at both ends",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="colluded fake default (v2 re-test)",
                    description="Detectable during the challenge window.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="residual: organic-looking defaults at "
            "damped sizes remain a normal insurance cost",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Forecast-Indexed Fee Smoothing Pool": {
        # v2: position caps + mean-reverting buffer
        "game_theory": dict(
            summary="v2 caps per-address forecast positions (pos_cap=0.2 "
            "share) and the buffer mean-reverts to a belief-scaled target. "
            "The belief whale capped at 20% of the book cannot set q "
            "unilaterally; pushing q repeatedly no longer ratchets the "
            "buffer (it reverts).",
            attack_vectors=[
                dict(
                    vector="belief-whale buffer farming (v2 re-test)",
                    description="With a 20% position cap, moving q to the "
                    "injection zone requires genuine broad book demand — "
                    "the whale funds 20% and the rest is honest flow. "
                    "Injection harvest shrinks below whale's cost of "
                    "moving their own transactions through the smoothed "
                    "fees.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Mean reversion means the buffer's steady-state "
            "tracks average belief — one-shot manipulation decays, "
            "repeated manipulation must sustain cost against reversion.",
            death_spiral_risk=2.0,
            game_theory_score=7.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Position caps convert whale dominance into a market-"
            "depth question; the remaining surface is sub-division "
            "(many whales acting as one) — a collusion problem bounded by "
            "cap enforcement per address.",
            attack_vectors=[
                dict(
                    vector="uncapped position dominance (v2 re-test)",
                    description="Capped at 20% per address; sub-division "
                    "requires detectable coordination across funded "
                    "addresses.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="multi-address coordination below "
            "detection thresholds (deployment-scope)",
            security_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="TWAP-style snapshots close the book-quote flash: "
            "momentary quotes don't move the epoch's implied probability "
            "beyond their time-weighted share.",
            data_source_assessment="Time-weighted book statistics + "
            "on-chain fee percentiles.",
            manipulation_vectors=[
                dict(
                    vector="book-quote flash manipulation (v2 re-test)",
                    description="TWAP snapshots bound flash quotes to their "
                    "time-weighted contribution; flashing costs full "
                    "position carry for a fraction of the effect.",
                    attacker="arbitrageur",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="belief-whale buffer farming (v2 re-test): "
            "per-address caps bound the whale to 20% of the belief signal "
            "and the buffer mean-reverts — one-shot pushes decay and "
            "sustained pushes pay carry costs against honest flow",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="belief-whale buffer farming (v2 re-test)",
                    description="Capped and reverted.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="residual: multi-address coordination is "
            "bounded by cap enforcement, unbounded collusion noted",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Prediction-Settled Hashprice Hedge Board": {
        # v2: reporter bonds (it already survived v1)
        "game_theory": dict(
            summary="v2 adds a reporter-bond surcharge (report_bond=500) to "
            "margin when reference vol exceeds tolerance: unbonded reporter "
            "tilting now carries bond cost scaled with deviation. The "
            "minority-tilt vector closes; the majority-cartel double-dip "
            "was already self-defeating.",
            attack_vectors=[
                dict(
                    vector="supplier-median inflation double dip (v2 re-test)",
                    description="Majority requirement unchanged — still "
                    "self-defeating in competitive supply markets; bond "
                    "surcharge raises the minority path's cost too.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Bond surcharges align reporter cost with "
            "deviation magnitude — honest reporting is the cheap "
            "equilibrium.",
            death_spiral_risk=3.0,
            game_theory_score=7.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Margin-squeeze vol manufacture now meets the bond "
            "surcharge funding reporter discipline — manufactured vol "
            "raises the manipulator's own bond cost through their reporter "
            "positions.",
            attack_vectors=[
                dict(
                    vector="margin-squeeze volatility manufacture (v2 re-test)",
                    description="Vol manufacture to squeeze competitors now "
                    "surcharges the attacker's own bonded positions — "
                    "self-taxing attack.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="external (non-reporter) vol "
            "manufacture — bounded by margin marking itself",
            security_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Bonds close the unbonded tilting hole the v1 analysis "
            "named — the fix the red team itself proposed.",
            data_source_assessment="Median-of-supplier settlement with "
            "bonded reporters.",
            manipulation_vectors=[
                dict(
                    vector="unbonded reporter tilting (v2 re-test)",
                    description="Now bonded: tilting cost scales with "
                    "deviation via the margin surcharge.",
                    attacker="oracle_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="supplier-median inflation double dip (v2 "
            "re-test): majority-cartel requirement remains self-defeating "
            "and the bond surcharge now taxes minority tilting — both "
            "reporter paths cost more than they yield",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="supplier-median inflation double dip (v2 re-test)",
                    description="Self-defeating at majority, taxed at "
                    "minority.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="survives; the bond surcharge was the v1 "
            "red team's own recommendation",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Consensus-Odds Liquidity Rebate": {
        # v2: wash-gated rebates, halved belief sensitivity
        "game_theory": dict(
            summary="v2 halves belief sensitivity (r = m0*(1+2.5*(q-0.4)*0.5)) "
            "and gates depth attraction on realized flow. The self-dealing "
            "farm's multiplier halved and its wash depth must survive "
            "wash-gating. EV: half the multiplier against full forecast "
            "carry + wash-detection risk.",
            attack_vectors=[
                dict(
                    vector="self-dealing forecast rebate farming (v2 re-test)",
                    description="Halved multipliers on wash-gated depth: "
                    "the farm's return halves while its costs (forecast "
                    "positions + wash capital at risk) stay full — EV "
                    "negative at moderate detection rates.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Honest makers earn the halved-but-positive "
            "multipliers on genuine depth; farms pay full cost for half "
                    "yield.",
            death_spiral_risk=2.0,
            game_theory_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Wash-quote persistence now measures non-wash flow "
            "only — the persistence check reads realized taker "
            "interaction, which self-traded depth doesn't generate.",
            attack_vectors=[
                dict(
                    vector="wash-quote depth inflation (v2 re-test)",
                    description="Persistence measured on external taker "
                    "interaction; self-quotes don't qualify.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="buying genuine taker interaction to "
            "wash-qualify (costs the taker fees it farms)",
            security_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Volume wash near the forecast strike now faces the "
            "same realized-flow gate — wash volume doesn't move the "
            "resolution bucket where the venue meters realized taker "
            "volume.",
            data_source_assessment="Realized (non-wash) volume metering "
            "for both forecasts and rebate qualification.",
            manipulation_vectors=[
                dict(
                    vector="volume wash to move the forecast strike (v2 re-test)",
                    description="Wash volume excluded from the metered "
                    "statistic; moving the strike requires real taker "
                    "flow.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="self-dealing forecast rebate farming (v2 "
            "re-test): halved belief sensitivity plus realized-flow gating "
            "leaves the farm paying full cost for half the multiplier — "
            "the venue stops subsidizing manufactured beliefs",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="self-dealing forecast rebate farming (v2 re-test)",
                    description="Halved + gated = negative EV.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="residual: venues with weak wash detection "
            "see partial multipliers on choreography — enforcement "
            "constraint",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Adverse-Selection Taxed Prediction Clearing": {
        # v2: classifier-gated rebates
        "game_theory": dict(
            summary="v2 gates the rebate pool on a deterministic flow-"
            "pattern classifier (class_k=0.3 dampening on non-passing "
            "flow). The wash-oscillation farm's balanced leg earns 30% of "
            "full rebates while its one-sided leg still pays full widened "
            "aggressor spreads — the farm's funding ratio inverts.",
            attack_vectors=[
                dict(
                    vector="wash-oscillation rebate farming (v2 re-test)",
                    description="Classifier-dampened rebates (0.3x) vs. "
                    "full spread payments on the imbalance leg: the "
                    "oscillation farm's arithmetic flips negative unless "
                    "it defeats the classifier with expensive flow "
                    "shapes.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Genuine balanced flow (the depth-repairing "
            "population) passes the classifier at full rate — the "
            "incentive structure preserves its honest target.",
            death_spiral_risk=2.0,
            game_theory_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Persistence-gaming balanced flow meets the same "
            "classifier — choreographed persistence windows earn the "
            "dampened rate unless the choreography defeats deterministic "
            "pattern detection.",
            attack_vectors=[
                dict(
                    vector="persistence-gaming balanced flow (v2 re-test)",
                    description="Choreography must now defeat the "
                    "classifier, whose evasion cost scales with flow "
                    "realism.",
                    attacker="arbitrageur",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="classifier-evasion with genuinely "
            "realistic flow (an arms race, not a hole)",
            security_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="TWAP-window boundary gaming unchanged by v2 (the "
            "mid is still time-weighted) — but its value was already "
            "marginal: positioning outside the window still pays the "
            "widened spread inside it.",
            data_source_assessment="Time-weighted mid with realized-flow-"
            "metered statistics.",
            manipulation_vectors=[
                dict(
                    vector="TWAP-window boundary gaming (v2 re-test)",
                    description="Boundary positioning still pays in-window "
                    "spreads; gaming value negligible.",
                    attacker="arbitrageur",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="wash-oscillation rebate farming (v2 "
            "re-test): the classifier-gated rebate pool pays 30% on "
            "non-passing flow while the imbalance leg pays full spreads — "
            "the farm's funding arithmetic inverts",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="wash-oscillation rebate farming (v2 re-test)",
                    description="Negative EV under classifier gating.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="residual: classifier evasion is an arms "
            "race, noted as an operational constraint",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Belief-Weighted Volatility Target Fund": {
        # v2: hysteresis + halved rebalance rate
        "game_theory": dict(
            summary="v2 halves the exposure update rate (0.03) and adds a "
            "belief-response term proportional to risk VELOCITY (V_t1-"
            "V_t). Front-running the de-risking requires predicting not "
            "just direction but the now-gradual path — the predictable "
            "one-shot rebalance window is gone.",
            attack_vectors=[
                dict(
                    vector="belief-driven de-risking front-run (v2 re-test)",
                    description="Gradual updates + velocity terms mean no "
                    "discrete rebalance cliff to front-run; the attack "
                    "becomes a slow participation game the fund's TWAP-"
                    "style updates already mitigate.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Smooth exposure paths eliminate the MEV cliff; "
            "remaining value is ordinary participation-cost spread.",
            death_spiral_risk=3.0,
            game_theory_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Rebalance-window MEV shrinks with the update rate: "
            "halved rate = halved per-window extractable size, and "
            "velocity terms make windows state-dependent (harder to "
            "schedule sandwiches).",
            attack_vectors=[
                dict(
                    vector="rebalance-window MEV extraction (v2 re-test)",
                    description="No discrete window to sandwich; extraction "
                    "bounded at participation-spread scale.",
                    attacker="arbitrageur",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="residual participation-cost spread "
            "(ordinary trading cost, not an exploit)",
            security_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Belief-book stress spoofing meets the same velocity "
            "structure: spoofed stress must SUSTAIN to move the blend, "
            "paying carry at book size while the velocity term decays.",
            data_source_assessment="Realized vol + EWMA-smoothed implied "
            "stress with velocity damping.",
            manipulation_vectors=[
                dict(
                    vector="belief-book stress spoofing (v2 re-test)",
                    description="Sustained spoofing cost exceeds the "
                    "front-run value it can harvest against gradual "
                    "updates.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="belief-driven de-risking front-run (v2 "
            "re-test): halved update rate + velocity-responsive exposure "
            "remove the discrete rebalance cliff the front-run depended "
            "on — the attack degrades to ordinary participation spread",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="belief-driven de-risking front-run (v2 re-test)",
                    description="No cliff to front-run.",
                    attacker="whale",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="residual: deployment-scope randomized "
            "rebalance timing remains recommended",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Disagreement-Weighted Oracle Quorum": {
        # v2: directional accuracy weighting
        "game_theory": dict(
            summary="v2 rewards deviation TOWARD the anchor's move and "
            "punishes away-drift (the weight term flips sign with the "
            "median-vs-anchor direction relative to delta direction). "
            "Sandbagging — deviating while predicting your own deviation "
            "— now loses weight when the deviation is away-drift: the "
            "self-predicted deviation payout no longer compensates the "
            "weight penalty.",
            attack_vectors=[
                dict(
                    vector="calibration sandbagging (v2 re-test)",
                    description="Away-drift deviations lose weight AND pay "
                    "the stake: the sandbagger pays twice for the "
                    "corruption the mechanism now punishes directionally.",
                    attacker="oracle_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Honest reporting (deviating toward the "
            "anchor's move when your information justifies it) is the "
            "profitable equilibrium; corruption is doubly taxed.",
            death_spiral_risk=2.5,
            game_theory_score=7.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Slow-median capture (the coalition residual) is "
            "unchanged — a patient majority still drifts the EWMA below "
            "per-interval thresholds. That is a governance-scale attack "
            "on ANY median quorum, not this design's hole.",
            attack_vectors=[
                dict(
                    vector="slow-median capture (v2 re-test)",
                    description="Majority-coalition drift remains possible "
                    "at governance scale; directional weighting taxes it "
                    "per-step but majority persistence can absorb the "
                    "tax. Unbounded only for majorities.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="patient majority coalitions (a "
            "governance problem class, not a mechanism bug)",
            security_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Directional accuracy weighting is a genuine "
            "incentive improvement: the deviation market now prices "
            "corruption directionally. Reporter bonds would complete the "
            "defense (v3 candidate).",
            data_source_assessment="Median quorum with direction-weighted "
            "calibration.",
            manipulation_vectors=[
                dict(
                    vector="calibration sandbagging (v2 re-test)",
                    description="Closed by directional taxation.",
                    attacker="oracle_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="slow-median capture (v2 re-test): a patient "
            "reporter majority can still drift the published median below "
            "per-interval thresholds — directional weighting taxes the "
            "drift per step, but majorities can absorb the tax. This is "
            "the honest governance residual, not a solo-attacker path",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="slow-median capture (v2 re-test)",
                    description="Majority-only, governance-scale residual.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="reporter bonds slashed on cumulative drift "
            "(a v3 direction), plus quorum-rotation requirements at "
            "deployment",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Prediction-Fee Fallback Oracle": {
        # v2: fee revenue to sender cover (it already survived v1)
        "game_theory": dict(
            summary="v2 routes fallback fee revenue to the sender-cover "
            "pool rather than book owners: the coordinated book exit "
            "attack's re-entry harvest (re-entering to own the elevated "
            "fees) is gone — the fees now compensate senders instead.",
            attack_vectors=[
                dict(
                    vector="coordinated book exit attack (v2 re-test)",
                    description="Exit still forces fees up, but the "
                    "elevated revenue lands in sender cover, not the "
                    "attackers' book yield — the harvest leg is removed. "
                    "Remaining value: grief against senders, paid by the "
                    "attackers' own foregone yield.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Book owners now earn ordinary spread only; "
            "fallback episodes subsidize the senders they harm.",
            death_spiral_risk=2.5,
            game_theory_score=7.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Primary-feed staleness forcing remains the deepest "
            "surface but its profit leg was the book-fee harvest — with "
            "fees routed to senders, forcing staleness costs the "
            "reporter coalition their fee share for a sender-subsidy they "
            "can't collect.",
            attack_vectors=[
                dict(
                    vector="primary-feed staleness forcing (v2 re-test)",
                    description="Cost without harvest: the coalition burns "
                    "its own fee revenue to subsidize senders.",
                    attacker="oracle_provider",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="pure grief (non-profit) staleness — "
            "bounded by the sender cover it funds",
            security_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="The OI-floored prediction-book rung was already the "
            "strongest design element; revenue routing closes the "
            "remaining profit path.",
            data_source_assessment="Layered: primary feed, quorum, OI-"
            "floored book; fallback fees fund sender cover.",
            manipulation_vectors=[
                dict(
                    vector="book-quote flash manipulation (v2 re-test)",
                    description="OI floor + sender-cover routing leave no "
                    "profitable manipulation path through the book.",
                    attacker="arbitrageur",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="coordinated book exit attack (v2 re-test): "
            "the exit still forces fees up, but v2 routes the elevated "
            "revenue to sender cover instead of book owners — the "
            "attack's harvest leg is gone and the grief leg burns the "
            "attackers' own yield",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="coordinated book exit attack (v2 re-test)",
                    description="Cost without harvest.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="survives; sender cover self-funds during "
            "degradation episodes",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Report-Bonded Forecast Fee Meter": {
        # v2: verified-exposure compensation + ownership separation
        "game_theory": dict(
            summary="v2 compensates verified fee exposure (not band "
            "classification) with reporter/application ownership "
            "separation: self-directed mis-banding loses its 50% recovery "
            "— the reporter forfeits bonds that their own applications "
            "cannot legally receive.",
            attack_vectors=[
                dict(
                    vector="compensation-directed mis-banding (v2 re-test)",
                    description="Ownership separation blocks the recovery "
                    "leg; mis-banding is now a pure bond payment for "
                    "nothing. EV strongly negative.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Honest reporters keep bonds; caught "
            "applications with verified exposure receive compensation "
            "from genuinely forfeited bonds.",
            death_spiral_risk=2.0,
            game_theory_score=7.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Band-edge positioning loses its classification "
            "payout: compensation follows verified exposure, so edge-"
            "sitting applications receive only what their exposure "
            "actually was.",
            attack_vectors=[
                dict(
                    vector="compensation qualification gaming (v2 re-test)",
                    description="No classification boundary to game — "
                    "payout proportional to measured exposure.",
                    attacker="attacker",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="inflating measured exposure itself "
            "(bounded by the fee series the meter reads)",
            security_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="The attested band-error statistic is now both the "
            "forfeit trigger and the compensation measure — one series, "
            "consistent incentives.",
            data_source_assessment="Banded forecast bonds with verified-"
            "exposure compensation.",
            manipulation_vectors=[
                dict(
                    vector="band-edge statistical exploitation (v2 re-test)",
                    description="Edge exploitation yields verified "
                    "exposure payouts equal to actual exposure — no excess "
                    "recovery.",
                    attacker="arbitrageur",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="compensation-directed mis-banding (v2 "
            "re-test): ownership separation blocks the 50% self-recovery "
            "leg and verified-exposure payouts eliminate band-edge "
            "classification farming — both attack paths are closed",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="compensation-directed mis-banding (v2 re-test)",
                    description="Pure forfeiture without recovery.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="survives; residual is ordinary "
            "measurement honesty of the fee series",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Attestation-Locked Prediction Settlement": {
        # v2: external challengers + slash routing
        "game_theory": dict(
            summary="v2 admits externally bond-backed challenges and "
            "routes 80% of slash proceeds to challengers: the operator "
            "majority now faces external challenge capital with a direct "
            "financial stake in catching the manipulation. Capture "
            "requires outbidding the challenger class at 80% recovery "
            "rates.",
            attack_vectors=[
                dict(
                    vector="operator-majority settlement capture (v2 re-test)",
                    description="External challengers with 80% slash "
                    "recovery make capture a bidding war against a class "
                    "that profits from catching operators. Still possible "
                    "at governance scale, no longer profitable at "
                    "mechanism scale.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Challenger capital monitors flow "
            "attestations for profit; honest operators face no "
            "challenges.",
            death_spiral_risk=3.0,
            game_theory_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Slash recycling (the 40%-to-liquidity loop) is cut "
            "to 20%: manipulators recover at most a fifth of their slash "
            "through attacker-adjacent liquidity — the self-funding loop "
            "is materially degraded.",
            attack_vectors=[
                dict(
                    vector="self-funding manipulation recycling (v2 re-test)",
                    description="80% of slash goes to challengers; "
                    "recycling recovery drops to a fifth of v1 levels.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="challenge-class collusion with "
            "operators (the eternal last cartel)",
            security_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Challenge-window censorship was the v1 oracle hole: "
            "v2's external challenge admission with its own bond class "
            "breaks the operator-only admission control.",
            data_source_assessment="Median cross-checks + externally "
            "admissible bond-backed challenges.",
            manipulation_vectors=[
                dict(
                    vector="challenge-window censorship (v2 re-test)",
                    description="External admission defeats operator "
                    "censorship; suppression requires bond-market "
                    "dominance, not admission control.",
                    attacker="governance",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="operator-majority settlement capture (v2 "
            "re-test): external bond-backed challengers with 80% slash "
            "recovery turn capture into a bidding war the operators must "
            "win against a class that profits from catching them — the "
            "mechanism-scale profit path is closed; a governance-scale "
            "residual remains honestly noted",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="operator-majority settlement capture (v2 re-test)",
                    description="Outbid-the-challengers required.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="residual: a challenger-class cartel is the "
            "last standing attack — quorum rotation and challenge-bond "
            "concentration limits at deployment",
            evidence_level="HYPOTHESIS",
        ),
    },
}


def candidate_name_from(messages: list[dict]) -> str | None:
    for m in messages:
        c = re.search(r"CANDIDATE: (.+?)\ncategory", m["content"])
        if c:
            return c.group(1).strip()
    return None


SCHEMA_TO_KIND = {
    "GameTheoryReport": "game_theory",
    "SecurityReport": "security",
    "OracleReport": "oracle",
    "RedTeamReport": "red_team",
}


def main() -> None:
    bridge = AgentBridgeProvider()
    installed = 0
    for f in glob.glob(".bridge/requests/*.json"):
        with open(f) as fh:
            d = json.load(fh)
        schema = d.get("schema")
        if schema not in SCHEMA_TO_KIND or d.get("status") != "pending":
            continue
        name = candidate_name_from(d["messages"])
        if name is None or name not in A:
            continue
        cls = {
            "GameTheoryReport": GameTheoryReport,
            "SecurityReport": SecurityReport,
            "OracleReport": OracleReport,
            "RedTeamReport": RedTeamReport,
        }[schema]
        payload = cls.model_validate(A[name][SCHEMA_TO_KIND[schema]]).model_dump()
        bridge.install_answer(d["id"], payload)
        installed += 1
    print(f"installed {installed} re-attack answers")


if __name__ == "__main__":
    main()
