"""Bridge answers: round-9 red-team reports (10 candidates x 4 agents).

Genuine adversarial analysis against each FORMALIZED model. Verdicts are
honest: most candidates are vulnerable (profitable attack vectors exist
that the improver will then patch); a few bounded designs survive.
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

# Per candidate: {schema: payload}. Each agent report carries its own
# attack vectors; the RedTeamReport verdict consolidates.

R: dict[str, dict[str, dict]] = {
    "Treasury-Backed Fee Parameter Governance": {
        "gt": dict(
            summary="Fee-weighted governance with revenue-bonded proposals "
            "creates a pay-for-performance control market. The game is "
            "sound for single-epoch noiseless baselines, but proposers "
            "with superior revenue-forecast information can time changes "
            "to epochs where reversion-to-mean guarantees improvement "
            "regardless of merit — an adverse-selection edge over the "
            "treasury.",
            attack_vectors=[dict(
                vector="baseline-timing adverse selection",
                description="Proposer observes a depressed revenue epoch, "
                "proposes any change, and reversion-to-mean delivers "
                "improvement the proposer did not cause; bond pays out on "
                "luck.",
                attacker="governance_participant",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Honest proposers are outbid by "
            "baseline-timers; without a multi-epoch baseline the bond "
            "market selects for timing skill, not parameter skill.",
            death_spiral_risk=3.0,
            game_theory_score=6.0,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Bond slashing is the security core; its integrity "
            "depends on the revenue measurement being manipulation-"
            "resistant. Fee-volume attribution is attackable by wash "
            "settlement timed around proposals.",
            attack_vectors=[dict(
                vector="wash-settlement revenue inflation",
                description="Attacker proposing a change washes "
                "transactions to inflate the post-change revenue epoch, "
                "guaranteeing the bond pays out.",
                attacker="governance_participant",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            hardest_attack_to_defend="Wash settlement is cheap relative "
            "to bond payouts when the venue's fee share is small; "
            "measuring revenue net of wash patterns is hard.",
            security_score=5.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="No external oracle required — revenue is on-chain. "
            "The design's data problem is attribution, not oracles.",
            manipulation_vectors=[dict(
                vector="attribution gaming",
                description="Attributing revenue causally to a parameter "
                "change vs the counterfactual baseline is an econometrics "
                "problem done on-chain; unresolvable without a model.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="HYPOTHESIS",
            )],
            data_source_assessment="Fee ledger is on-chain and "
            "tamper-evident; the counterfactual baseline is constructed, "
            "not observed — this is the weak data surface.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Baseline-timing adverse selection: propose "
            "on depressed epochs and revert-to-mean pays the bond; "
            "profitable with moderate observation cost.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="baseline-timing adverse selection",
                description="Proposer times changes to depressed revenue "
                "epochs; reversion-to-mean guarantees improvement the "
                "proposer did not cause.",
                attacker="governance_participant",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Multi-epoch baseline windows plus "
            "wash-resistant revenue measurement (net-of-churn accounting) "
            "would neutralize the timing edge.",
            evidence_level="INFERENCE",
        ),
    },
    "Demand-Index Escalation Ladder for FX Batches": {
        "gt": dict(
            summary="Escalation with refund recycling is incidence-shifting; "
            "the queue index is on-chain. The game risk is a stuffed-queue "
            "refund cycle: a cohort pays escalations on its own volume but "
            "shares refunds with all congested-epoch settlers.",
            attack_vectors=[dict(
                vector="queue-stuffing refund farming",
                description="Cohort stuffs the queue above escalation "
                "rungs, triggering refund distribution to all congested "
                "settlers including the cohort; net positive when cohort "
                "share of refunds exceeds escalation paid.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Solo stuffing is negative-EV (escalation "
            "exceeds own refund share); a colluding cohort above the "
            "refund-share threshold is positive-EV. Collusion cap matters.",
            death_spiral_risk=3.5,
            game_theory_score=6.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="The reserve is the security boundary. Its floor and "
            "per-epoch refund cap bound extractable value, but the caps "
            "must be enforced exactly by the release rule.",
            attack_vectors=[dict(
                vector="refund-cap exhaustion",
                description="Repeated coordinated stuffing across epochs "
                "grinds the reserve toward its floor, degrading "
                "counter-cyclical function even if each cycle's profit is "
                "capped.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Distinguishing organic congestion "
            "from coordinated stuffing requires settlement-pattern "
            "diversity checks the index does not carry.",
            security_score=6.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Index is queue depth on-chain — oracle-free by "
            "design, which is a genuine strength.",
            manipulation_vectors=[dict(
                vector="queue depth stuffing",
                description="Queue depth is directly manipulable by "
                "submitting batches; the index measures pressure, not "
                "intent, so stuffing and congestion are "
                "indistinguishable to the rule.",
                attacker="attacker",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="On-chain queue state is exact and "
            "tamper-evident; the semantic gap (pressure vs stuffing) is "
            "the residual risk.",
            oracle_feasibility_score=7.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Coordinated queue-stuffing refund farming: "
            "colluding cohort's refund share exceeds escalation paid; "
            "profitable above the collusion threshold.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="queue-stuffing refund farming",
                description="Cohort stuffs the queue to rung-triggering "
                "depth and shares refunds paid to all congested-epoch "
                "settlers.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Per-epoch refund caps keyed to settlement "
            "diversity (unique settler count), and refund share "
            "proportional to escalation paid, would flip the cycle "
            "negative-EV.",
            evidence_level="INFERENCE",
        ),
    },
    "Bandwidth Bond Market for Relay Peers": {
        "gt": dict(
            summary="Bonded capacity with probe-verified forfait aligns "
            "incentives: over-commitment is prepaid. The residual game is "
            "probe placement — relays can choose probe routes through "
            "favorable peers.",
            attack_vectors=[dict(
                vector="probe-route selection",
                description="A relay cluster arranges that probes sample "
                "healthy peers while its degraded peers serve real "
                "traffic, collecting lease fees without delivering.",
                attacker="liquidity_provider",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            equilibria_notes="With randomized probe assignment the "
            "route-selection edge vanishes; without it, cartel clusters "
            "capture lease fees systematically.",
            death_spiral_risk=2.5,
            game_theory_score=7.0,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Forfait mechanics are sound if probes are honest; "
            "probe funding and assignment is the security commons.",
            attack_vectors=[dict(
                vector="probe underfunding",
                description="Starving the probe budget degrades "
                "verification coverage; forfaits stop firing and "
                "under-delivery becomes free.",
                attacker="attacker",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            hardest_attack_to_defend="Probe infrastructure is external to "
            "the market it polices; its funding must be endogenous "
            "(forfait-funded probes would close the loop).",
            security_score=6.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Energy attestation is the oracle surface: relay-side "
            "joule reports need corroboration.",
            manipulation_vectors=[dict(
                vector="joule over-attestation",
                description="Relays overstate consumed energy to raise "
                "escrow releases; tolerance bands bound single-report "
                "overstatement but systematic bias accumulates.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Energy index from mesh-median "
            "realized cost is robust to individual liars; "
            "regional blending blunts precision but not integrity.",
            oracle_feasibility_score=6.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Probe-route selection by a relay cartel: "
            "lease fees collected on undelivered capacity while probes "
            "sample healthy peers; profitable with moderate coordination.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="probe-route selection",
                description="Cartel routes probes through healthy peers "
                "while degraded peers collect lease fees undetected.",
                attacker="liquidity_provider",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            what_would_save_it="Randomized, cryptographic probe "
            "assignment (unpredictable routes) plus forfait-funded probe "
            "budgets closes the commons and the selection edge.",
            evidence_level="INFERENCE",
        ),
    },
    "Quote-Deviation Slashed FX Reference Feed": {
        "gt": dict(
            summary="Self-anchored deviation slashing is incentive-"
            "compatible above a flow floor: manipulation of the anchor "
            "requires moving the corridor's own realized prices, which is "
            "self-defeating for reporters who also settle there.",
            attack_vectors=[dict(
                vector="thin-window anchor capture",
                description="In low-flow windows, a wealthy attacker "
                "moves realized execution prices cheaply, forcing honest "
                "reporters into deviation slashes; bond pool drains to "
                "diversity grants while the attacker's own quotes "
                "prevail.",
                attacker="whale",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Above the flow floor, deviation is "
            "prepaid and honesty dominates; below it, the anchor inverts "
            "from discipline to weapon. The gate is everything.",
            death_spiral_risk=4.0,
            game_theory_score=6.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="The bond pool is the security budget; its drain "
            "condition must be flow-gated.",
            attack_vectors=[dict(
                vector="reporter-exodus cascade",
                description="Repeated thin-window slashes push reporters "
                "out; fewer reporters widens medians, increasing '"
                "deviation' slashes — a self-accelerating drain.",
                attacker="unspecified",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="The thin-window capture: cost of "
            "moving realized prices must exceed bond extraction in "
            "every window, which is a flow-dependent condition the "
            "mechanism must enforce.",
            security_score=5.5,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="This IS an oracle design; its manipulation surface "
            "is the anchor window's realized-flow depth.",
            manipulation_vectors=[dict(
                vector="thin-window anchor capture",
                description="Cheap realized-price movement in thin "
                "windows turns the slash condition against honest "
                "reporters.",
                attacker="whale",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Endogenous realized execution is the "
            "right anchor; its integrity is proportional to window flow "
            "— must be gated.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Thin-window anchor capture: cheap realized-"
            "price moves in low-flow windows weaponize deviation slashes "
            "against honest reporters; profitable below the flow floor.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="thin-window anchor capture",
                description="Whale moves thin-window realized prices to "
                "force deviation slashes on honest reporters and capture "
                "the reference.",
                attacker="whale",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Flow-gated slashing (no slash below a "
            "realized-flow floor per window) plus median re-weighting "
            "toward high-flow windows neutralizes thin capture.",
            evidence_level="INFERENCE",
        ),
    },
    "Cyclic Demand Reserve for Fee Recycles": {
        "gt": dict(
            summary="Counter-cyclical release is a fiscal stabilizer; "
            "the gaming surface is eligibility — builders staying "
            "'active' cheaply during troughs to collect rebates.",
            attack_vectors=[dict(
                vector="trough eligibility farming",
                description="Builders maintain minimal activity proofs "
                "during demand troughs, collecting counter-cyclical "
                "rebates far exceeding the value of infrastructure "
                "actually sustained.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="With activity proofs priced at real "
            "throughput, farming collapses; with cheap proofs (heartbeats),"
            " troughs subsidize ghosts.",
            death_spiral_risk=2.0,
            game_theory_score=7.0,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Reserve floor bounds catastrophic drain; the rule is "
            "deterministic and published — no discretionary surface.",
            attack_vectors=[dict(
                vector="index depression",
                description="Cohort suppresses fee volume (or withholds "
                "settlement) to deepen the perceived trough, harvesting "
                "rebates on artificially low demand.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Distinguishing organic troughs from "
            "engineered ones: the index measures volume, not intent.",
            security_score=6.5,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="On-chain fee data only — oracle-free. The index's "
            "moving average is computed deterministically.",
            manipulation_vectors=[dict(
                vector="MA window gaming",
                description="Timing volume bursts to reset the moving "
                "average high makes subsequent normal volume read as "
                "trough, triggering rebates.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            data_source_assessment="Fully on-chain, tamper-evident; "
            "statistical gaming of the MA window is the residual.",
            oracle_feasibility_score=7.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Trough eligibility farming: cheap activity "
            "proofs harvest counter-cyclical rebates during engineered "
            "or organic troughs; profitable for idle capacity.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="trough eligibility farming",
                description="Builders hold minimal activity proofs "
                "through troughs to collect rebates exceeding sustained "
                "value.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Rebate eligibility keyed to verifiable "
            "delivered throughput (not heartbeats), with decay for "
            "below-baseline delivery, converts farming into service.",
            evidence_level="INFERENCE",
        ),
    },
    "Productivity-Index Scaled Compute Clearing": {
        "gt": dict(
            summary="Index-indexed fee splits are incentive-compatible "
            "when the index samples the full batch stream; provider-"
            "selected samples invert the incentive (depress index to "
            "raise own share).",
            attack_vectors=[dict(
                vector="index suppression via slow batches",
                description="Provider submits deliberately inefficient "
                "batches at scale to depress the mesh productivity index, "
                "raising the provider fee share for all its batches.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Solo suppression is negative-EV (own "
            "inefficiency costs revenue); a provider cartel above a "
            "share threshold shifts the split profitably.",
            death_spiral_risk=2.5,
            game_theory_score=6.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Index computation is the security boundary: "
            "whole-stream medians with per-provider weight floors.",
            attack_vectors=[dict(
                vector="sample selection bias",
                description="If index statistics accept provider-chosen "
                "batch samples, cherry-picking skews the index "
                "systematically.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            hardest_attack_to_defend="Sample selection: the index must "
            "consume the complete batch stream with cryptographic "
            "inclusion proofs.",
            security_score=6.5,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Index is endogenous (execution proofs on-chain); "
            "no external oracle.",
            manipulation_vectors=[dict(
                vector="proof metadata gaming",
                description="Throughput attestation includes "
                "task-difficulty metadata; overstating difficulty "
                "inflates measured productivity.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            data_source_assessment="Execution proofs are verifiable "
            "compute's core competency; difficulty normalization needs "
            "agreed task classes.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Cartel index suppression: providers above "
            "a share threshold submit inefficient batches to depress the "
            "productivity index and raise their fee split; profitable at "
            "scale.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="index suppression via slow batches",
                description="Provider cartel depresses the mesh index "
                "with inefficient batches, shifting the fee split in "
                "its favor.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Whole-stream median indexing with "
            "per-provider weight floors and difficulty-normalized "
            "attestation makes suppression self-defeating.",
            evidence_level="INFERENCE",
        ),
    },
    "Joule-Bonded Inference Escrow": {
        "gt": dict(
            summary="Joule denomination with endogenous energy index is "
            "self-correcting toward marginal cost; the gaming surface is "
            "attestation tolerance.",
            attack_vectors=[dict(
                vector="tolerance-band over-attestation",
                description="Providers systematically attest at the top "
                "of the measurement tolerance band, collecting escrow "
                "releases for joules never consumed; per-request "
                "overstatement is legal, aggregate drift is theft.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="With mesh-median index correction, "
            "aggregate overstatement drags the index up, raising "
            "everyone's costs — bounded but persistent skim.",
            death_spiral_risk=2.0,
            game_theory_score=7.0,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Bond slashes bound per-request overstatement; "
            "aggregate tolerance drift is the residual.",
            attack_vectors=[dict(
                vector="energy index drift",
                description="Collusive over-attestation slowly raises "
            "the mesh energy index, taxing honest providers and users "
            "alike while skim accrues.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Independent energy measurement "
            "(metering at the rack level) is physical, not "
            "cryptographic — corroboration sampling is the defense.",
            security_score=6.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="The energy price index is the oracle; mesh-median "
            "realized cost is the right construction.",
            manipulation_vectors=[dict(
                vector="tolerance-band over-attestation",
                description="Top-of-band attestation aggregates into "
            "index drift favoring providers.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Realized-cost median is robust to "
            "minority liars; majority-collusion captures the index — "
            "bounded by demand-side exit.",
            oracle_feasibility_score=6.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Tolerance-band over-attestation: provider "
            "cartel attests at the top of the tolerance band, skimming "
            "escrow for unconsumed joules; profitable at scale.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="tolerance-band over-attestation",
                description="Systematic top-of-band joule attestation "
            "aggregates into paid escrow releases for energy never "
            "consumed.",
                attacker="validator",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Corroborated attestation (independent "
            "probe sampling of actual draw) plus median-based index "
            "reset when corroboration gaps exceed tolerance.",
            evidence_level="INFERENCE",
        ),
    },
    "Output-Indexed Compute Swap Board": {
        "gt": dict(
            summary="Distribution-margined output swaps complete the "
            "compute risk market; benchmark integrity is the game.",
            attack_vectors=[dict(
                vector="benchmark overfitting",
                description="Sellers tune models to the agreed task set "
                "rather than delivering general quality; swaps settle "
                "in their favor while real output quality stagnates.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Rotating task sets devalue overfitting "
            "capital; static tasks guarantee convergence to "
            "overfit-dominated settling.",
            death_spiral_risk=2.5,
            game_theory_score=7.0,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Margin engine against distribution volatility is "
            "sound; verification of scores is the weak link.",
            attack_vectors=[dict(
                vector="score verification capture",
                description="The verification oracle (public evaluation "
                "harness) is a single point of capture; a captured "
                "harness settles all swaps dishonestly.",
                attacker="oracle_provider",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            hardest_attack_to_defend="Evaluation harness integrity: "
            "multi-harness median scoring with bonded harnesses is the "
            "structural fix.",
            security_score=6.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Benchmark scores are the oracle input; MLPerf-style "
            "public evaluation is mature but centralizable.",
            manipulation_vectors=[dict(
                vector="harness capture",
                description="Bribing or compromising the evaluation "
            "harness moves settlements across all open swaps.",
                attacker="oracle_provider",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Multiple independent harnesses with "
            "reproducible evaluation would make capture expensive; "
            "single-harness designs inherit its failure.",
            oracle_feasibility_score=6.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Benchmark overfitting: sellers tune to "
            "the static task set, settling swaps in their favor while "
            "general quality stagnates; profitable and undetectable "
            "in-band.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="benchmark overfitting",
                description="Static agreed tasks let sellers optimize "
            "for the benchmark rather than delivered quality.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Rotating, expanding task sets with "
            "held-out evaluation splits, plus multi-harness median "
            "scoring, devalue overfit capital.",
            evidence_level="INFERENCE",
        ),
    },
    "Fee-Tier Voted Model Registry": {
        "gt": dict(
            summary="Decaying fee-paid weight is the correct flow-vs-"
            "stock correction; capture requires sustained current "
            "spend.",
            attack_vectors=[dict(
                vector="sustained-volume tier capture",
                description="A wealthy actor simply pays the fees — "
            "buying sustained inference volume to hold registry weight "
            "and set tiers favoring its own models; the bond rebates "
            "on regressions may be cheaper than the prize.",
                attacker="whale",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="The design raises capture cost to current-"
            "usage price, which is the honest goal; capture remains "
            "possible for actors whose model revenue exceeds fee cost.",
            death_spiral_risk=2.5,
            game_theory_score=7.0,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Registry weight ledger is on-chain; the security "
            "question is economic, not cryptographic.",
            attack_vectors=[dict(
                vector="self-dealing volume",
                description="Attacker routes its own inference through "
            "its own endpoints at scale, paying fees to itself to mint "
            "weight.",
                attacker="governance_participant",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            hardest_attack_to_defend="Net-of-self-dealing fee accounting "
            "(fees from first-party endpoints discounted in weight) is "
            "required but weakens legitimate self-hosting.",
            security_score=5.5,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="No external oracle — inference volume is on-chain "
            "per endpoint.",
            manipulation_vectors=[dict(
                vector="self-dealing volume",
                description="First-party endpoint volume mints weight "
            "without serving external demand.",
                attacker="governance_participant",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Volume data is exact; the semantic "
            "gap (own vs external demand) needs endpoint-ownership "
            "attribution.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Self-dealing volume: attacker pays itself "
            "inference fees at its own endpoints, minting registry "
            "weight to set tiers favoring its models; profitable when "
            "tier value exceeds fee cost.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="self-dealing volume",
                description="First-party routed volume mints "
            "governance weight without external demand.",
                attacker="governance_participant",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Net-of-self-dealing weight accounting "
            "with endpoint-ownership attribution, and per-address "
            "weight caps.",
            evidence_level="INFERENCE",
        ),
    },
    "Vol-Adaptive Market Making Rebate Curve for Compute Futures": {
        "gt": dict(
            summary="Deterministic curve with bond-gated parameters "
            "removes discretionary gaming; the surface is the index "
            "itself.",
            attack_vectors=[dict(
                vector="curve front-running",
                description="Makers compute the soon-to-publish "
            "volatility index from public quotes and pre-position "
            "depth where the curve will pay most, extracting rebates "
            "for anticipated (not delivered) stabilization.",
                attacker="liquidity_provider",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Delayed index publication and bounded "
            "steps shrink the edge; fully deterministic publication "
            "schedules still leak pre-position signal.",
            death_spiral_risk=2.0,
            game_theory_score=6.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Taker-funded rebates with published bounds are "
            "structurally sound; parameter bonds close the governance "
            "surface.",
            attack_vectors=[dict(
                vector="index manipulation for rebate capture",
                description="A cohort trades to inflate measured "
            "benchmark volatility, moving the curve to rebate-rich "
            "territory while their own depth collects.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Volatility indices are "
            "manipulable by volume patterns by construction; delayed "
            "publication is the only structural dampener.",
            security_score=6.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Index is computed from the board's own public "
            "quote distribution — self-referential, no external feed.",
            manipulation_vectors=[dict(
                vector="index manipulation for rebate capture",
                description="Quote patterns inflate measured volatility, "
            "steering the rebate curve.",
                attacker="arbitrageur",
                profitable_for_attacker=True,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            data_source_assessment="Public quote data is exact; "
            "volatility estimators are inherently pattern-sensitive — "
            "robust estimators (median absolute deviation) over long "
            "windows blunt it.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="vulnerable",
            strongest_attack="Curve front-running: pre-positioning on "
            "computable index updates extracts rebates for anticipated "
            "stabilization; profitable for fast makers.",
            strongest_attack_is_profitable=True,
            attack_vectors=[dict(
                vector="curve front-running",
                description="Makers pre-position where the "
            "volatility-indexed curve will pay, harvesting rebates for "
            "stabilization already priced.",
                attacker="liquidity_provider",
                profitable_for_attacker=True,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Delayed index publication with random "
            "jitter plus rebate vesting on realized (not anticipated) "
            "stabilization.",
            evidence_level="INFERENCE",
        ),
    },
}

BUILDERS = {
    "GameTheoryReport": (GameTheoryReport, "gt"),
    "SecurityReport": (SecurityReport, "sec"),
    "OracleReport": (OracleReport, "oracle"),
    "RedTeamReport": (RedTeamReport, "rt"),
}


def candidate_name_from(messages: list[dict]) -> str | None:
    for m in messages:
        c = re.search(r"CANDIDATE: (.+?)\ncategory", m["content"])
        if c:
            return c.group(1).strip()
    return None


def main() -> None:
    bridge = AgentBridgeProvider()
    installed = 0
    for f in sorted(glob.glob(".bridge/requests/*.json")):
        with open(f) as fh:
            d = json.load(fh)
        schema = d.get("schema")
        if schema not in BUILDERS or d.get("status") != "pending":
            continue
        name = candidate_name_from(d["messages"])
        if name is None or name not in R:
            continue
        cls, kind = BUILDERS[schema]
        payload = cls.model_validate(R[name][kind]).model_dump()
        bridge.install_answer(d["id"], payload)
        installed += 1
    print(f"installed {installed} red-team answers")


if __name__ == "__main__":
    main()
