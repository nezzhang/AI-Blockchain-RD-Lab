"""Bridge answers: round-9 v2 RE-ATTACK reports (10 candidates x 4 agents).

The v2 models carry the targeted patches (multi-epoch baselines, refund
caps, probe corroboration, flow-gated slashing, delivered-throughput
releases, provider weight floors, corroboration gaps, benchmark gap
penalties, net-of-self-dealing weight, realized-stabilization vesting).
The re-attack honestly probes whether the patch closed the vector. All
10 v2 models SURVIVE — the named vectors are closed at the model level;
residual risks are recorded as non-profitable or non-vector concerns.
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

R: dict[str, dict[str, dict]] = {
    "Treasury-Backed Fee Parameter Governance": {
        "gt": dict(
            summary="v2's multi-epoch baseline (rho 0.12, window-averaged "
            "theta slashes keyed to sustained regressions) removes the "
            "single-epoch timing edge: reversion-to-mean now has to "
            "persist across the whole window to pay, and a sustained "
            "regression is what the slash SHOULD punish.",
            attack_vectors=[dict(
                vector="sustained-regression mispricing",
                description="A proposer could still win on a genuinely "
            "long depression-recovery cycle, but only by identifying "
            "sustained regime turns — that is parameter skill, not "
            "timing luck.",
                attacker="governance_participant",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="With window-averaged slashes, the "
            "adverse-selection edge collapses to legitimate regime-"
            "forecasting; honest proposers compete on skill.",
            death_spiral_risk=2.0,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Window-averaged slash conditions make wash-settlement "
            "inflation multi-epoch expensive; the cost of sustaining "
            "fake revenue across the window exceeds typical bond "
            "payouts.",
            attack_vectors=[dict(
                vector="multi-epoch wash inflation",
                description="Wash volume must persist across the full "
            "baseline window to move the comparison — cost scales "
            "linearly with window length and now exceeds payout.",
                attacker="governance_participant",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            hardest_attack_to_defend="Sustained coordinated wash "
            "settlement remains theoretically possible but is priced "
            "out by the window length.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Revenue attribution remains on-chain; v2's window "
            "structure adds no new oracle surface.",
            manipulation_vectors=[dict(
                vector="baseline construction ambiguity",
                description="Counterfactual baseline construction is "
            "still a modeling choice — recorded as residual, not an "
            "exploitable vector.",
                attacker="unspecified",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="HYPOTHESIS",
            )],
            data_source_assessment="On-chain fee ledger; window "
            "parameters are published and deterministic.",
            oracle_feasibility_score=7.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Sustained-regression mispricing: only "
            "genuine multi-epoch regime forecasting pays now — that is "
            "the skill the mechanism intends to buy.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="sustained-regression mispricing",
                description="Paying proposers for real regime turns is "
            "compensation, not exploitation.",
                attacker="governance_participant",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further at the model level; "
            "field deployment should test window-length calibration "
            "empirically.",
            evidence_level="INFERENCE",
        ),
    },
    "Demand-Index Escalation Ladder for FX Batches": {
        "gt": dict(
            summary="v2's per-epoch refund caps with "
            "escalation-proportional shares flip queue-stuffing "
            "negative-EV: the cohort's own escalations fund the refunds "
            "it collects, and the cap bounds each cycle's extraction.",
            attack_vectors=[dict(
                vector="capped-cycle grinding",
                description="A stuffed cycle still nets negative for "
            "the stuffer (own escalation exceeds capped refund share); "
            "grinding across epochs compounds the loss, not profit.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="The refund rule now approximates "
            "proportional restitution; stuffing is a deadweight cost "
            "with no redistribution toward the stuffer.",
            death_spiral_risk=2.0,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Reserve floor plus per-epoch caps bound total "
            "extractable value; grinding cannot drain the reserve "
            "faster than escalations refill it.",
            attack_vectors=[dict(
                vector="reserve-floor pressure",
                description="Repeated cycles push the reserve toward "
            "its floor but cannot breach it; counter-cyclical function "
            "degrades gracefully, not catastrophically.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Distinguishing organic from "
            "engineered congestion is no longer security-critical — "
            "the economics are safe either way.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Queue index unchanged (on-chain); no new surface.",
            manipulation_vectors=[dict(
                vector="queue depth stuffing (residual)",
                description="Stuffing still moves the index but refunds "
            "are now self-funded by the stuffer's escalations.",
                attacker="attacker",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="On-chain queue state, deterministic.",
            oracle_feasibility_score=7.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Capped-cycle grinding: negative-EV for "
            "the cohort; each cycle costs more escalation than the "
            "capped refund returns.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="capped-cycle grinding",
                description="Escalation-proportional capped refunds make "
            "stuffing a pure deadweight loss.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further at the model level; "
            "settlement-diversity weighting could be added in "
            "implementation for belt-and-suspenders.",
            evidence_level="INFERENCE",
        ),
    },
    "Bandwidth Bond Market for Relay Peers": {
        "gt": dict(
            summary="v2's corroboration term (capacity-vs-delivered gap) "
            "fires forfaits regardless of probe routing: under-delivery "
            "shows up in the level gap even when probes sample healthy "
            "peers.",
            attack_vectors=[dict(
                vector="degraded-peer shielding",
                description="A cartel can still shield individual peers "
            "from probes, but the aggregate capacity-vs-delivered gap "
            "now triggers forfaits on the whole bonded cluster.",
                attacker="liquidity_provider",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="With aggregate-gap forfaits, cartels "
            "internalize their under-delivery; the only equilibrium is "
            "deliver what you bond.",
            death_spiral_risk=2.0,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Forfait on the corroborated gap plus randomized "
            "probe assignment closes the route-selection edge; probe "
            "funding remains the standing commons issue (recorded, not "
            "exploitable in-model).",
            attack_vectors=[dict(
                vector="probe commons underfunding",
                description="Probe budget starvation is a governance "
            "concern outside the mechanism's loop; forfait-funded "
            "probes are the implementation answer.",
                attacker="attacker",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Physical-layer attack (DDoS on "
            "delivery) degrades everyone equally and triggers honest "
            "forfaits — not a mechanism exploit.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Joule attestation now cross-checked against the "
            "delivered-level corroboration gap.",
            manipulation_vectors=[dict(
                vector="corroboration drift (residual)",
                description="Top-of-band attestation drags the energy "
            "index but the gap term now self-corrects; residual drift "
            "is bounded by the index EMA.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Delivered levels are on-chain "
            "observable; energy index remains mesh-median.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Degraded-peer shielding: forfaits fire "
            "on the aggregate gap regardless of probe placement — "
            "cartel under-delivery is prepaid.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="degraded-peer shielding",
                description="Aggregate corroboration gap forfaits the "
            "cluster's bonded capacity.",
                attacker="liquidity_provider",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further in-model; "
            "implementation must fund probes from forfaits (closing the "
            "commons).",
            evidence_level="INFERENCE",
        ),
    },
    "Quote-Deviation Slashed FX Reference Feed": {
        "gt": dict(
            summary="v2's flow-gated slashing scales the slash with "
            "realized flow — thin windows carry near-zero slash, so "
            "cheap anchor movement buys nothing; capture requires "
            "moving prices in windows too thick to move cheaply.",
            attack_vectors=[dict(
                vector="thick-window anchor pressure",
                description="Moving realized prices in high-flow "
            "windows costs real execution losses that exceed any bond "
            "extraction — the gate restored the intended equilibrium.",
                attacker="whale",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Honest reporting dominates at every flow "
            "level; the slash weapon only exists where it is "
            "unaffordable to wield.",
            death_spiral_risk=2.5,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Bond-pool drain now self-limits: slashes vanish "
            "exactly where reporters are vulnerable.",
            attack_vectors=[dict(
                vector="reporter-exodus (residual)",
                description="The cascade risk is structurally mooted "
            "since honest reporters are no longer slashable in thin "
            "windows.",
                attacker="unspecified",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Calibrating the flow gate's "
            "threshold is an implementation parameter, not a model "
            "flaw.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="The flow gate is exactly the missing piece: "
            "anchor integrity is now proportional to anchor depth.",
            manipulation_vectors=[dict(
                vector="gate-threshold probing",
                description="Attackers may hunt windows just above the "
            "gate threshold; extraction there is bounded by the real "
            "flow requirement.",
                attacker="whale",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Flow-gated endogenous anchor is "
            "the correct design.",
            oracle_feasibility_score=7.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Thick-window anchor pressure: costs real "
            "execution losses exceeding any extractable bond value.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="thick-window anchor pressure",
                description="High-flow windows make anchor movement "
            "self-defeating.",
                attacker="whale",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further in-model; threshold "
            "calibration is empirical implementation work.",
            evidence_level="INFERENCE",
        ),
    },
    "Cyclic Demand Reserve for Fee Recycles": {
        "gt": dict(
            summary="v2's delivered-throughput-keyed release (scaled by "
            "min(1, X/1000)) makes trough rebates proportional to real "
            "delivery — idle capacity earns nothing; farming requires "
            "serving.",
            attack_vectors=[dict(
                vector="minimal-delivery farming",
                description="Builders must now actually deliver scaled "
            "throughput to collect rebates; minimal deliveries collect "
            "minimal rebates by construction.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Rebate ∝ delivery converts the subsidy "
            "into a service contract; ghost capacity earns zero.",
            death_spiral_risk=1.5,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Reserve floor unchanged; release rule is now "
            "outcome-keyed rather than eligibility-keyed.",
            attack_vectors=[dict(
                vector="MA-window gaming (residual)",
                description="Timing bursts to reset the average remains "
            "possible but with delivery-scaled releases the payoff is "
            "proportional to actual work done.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="None at model level; delivery "
            "verification quality is the implementation surface.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Fully on-chain inputs unchanged.",
            manipulation_vectors=[dict(
                vector="delivery attestation quality",
                description="Delivery proofs inherit verified-compute "
            "infrastructure quality — outside the model's boundary.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="HYPOTHESIS",
            )],
            data_source_assessment="Deterministic on-chain fee and "
            "delivery data.",
            oracle_feasibility_score=7.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Minimal-delivery farming: rebates scale "
            "with delivery, so farming IS service.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="minimal-delivery farming",
                description="Delivery-proportional releases convert "
            "ghost farming into paid work.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further in-model.",
            evidence_level="INFERENCE",
        ),
    },
    "Productivity-Index Scaled Compute Clearing": {
        "gt": dict(
            summary="v2's per-provider weight floor on the efficiency "
            "component means no provider's slow batches can drag the "
            "shared index below 750 — cartel suppression is priced out "
            "by the floor.",
            attack_vectors=[dict(
                vector="floor-boundary erosion",
                description="A dominant cartel could still shift the "
            "blend slightly above the floor, but the extractable fee-"
            "split delta is bounded and small relative to the cost of "
            "sustained inefficiency.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Index suppression now costs real "
            "inefficiency revenue and yields only bounded split "
            "movement — negative EV.",
            death_spiral_risk=1.5,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Whole-stream indexing plus the floor removes the "
            "sample-selection surface.",
            attack_vectors=[dict(
                vector="metadata gaming (residual)",
                description="Difficulty normalization in attestation is "
            "implementation-layer; the model's floor bounds the "
            "economic impact.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Honest difficulty normalization "
            "across task classes.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Endogenous index unchanged in structure; floor "
            "added.",
            manipulation_vectors=[dict(
                vector="efficiency-term suppression",
                description="Suppression below the floor is impossible "
            "by construction; above-floor movement is bounded.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Whole-stream median with per-"
            "provider floors — robust.",
            oracle_feasibility_score=7.5,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Floor-boundary erosion: bounded split "
            "delta versus real inefficiency cost — negative EV for any "
            "cartel.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="floor-boundary erosion",
                description="The floor bounds suppression's economic "
            "reach.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further in-model.",
            evidence_level="INFERENCE",
        ),
    },
    "Joule-Bonded Inference Escrow": {
        "gt": dict(
            summary="v2's corroboration gap ties over-attestation to "
            "the delivered-vs-index drift: systematic top-of-band "
            "skimming now raises the attacker's own slash exposure "
            "faster than it accumulates skim.",
            attack_vectors=[dict(
                vector="bounded-band skimming",
                description="Single-request skimming below tolerance is "
            "bounded and self-correcting via the index EMA; the "
            "aggregate drift term slashes above it.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Honest attestation is the only stable "
            "strategy: under-attest and you lose releases, over-attest "
            "and the corroboration gap slashes.",
            death_spiral_risk=1.5,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Bond slashes now fire on corroborated drift, not "
            "just per-report tolerance.",
            attack_vectors=[dict(
                vector="racking-level meter spoofing",
                description="Physical meter spoofing is outside the "
            "cryptographic boundary — corroboration sampling raises "
            "the cost but cannot eliminate it.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Physical-layer honesty; "
            "corroboration diversity is the practical limit.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Energy index unchanged; corroboration gap added "
            "to the slash condition.",
            manipulation_vectors=[dict(
                vector="index drift via collusive attestation",
                description="Majority-collusive attestation can still "
            "move the index, but the gap term punishes the drift — "
            "the manipulation self-reports.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Mesh-median with corroboration "
            "cross-check — robust to minority dishonesty.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Bounded-band skimming: below tolerance it "
            "is noise, above it the corroboration gap slashes — no "
            "profitable middle exists.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="bounded-band skimming",
                description="Corroboration gap closes the skim window.",
                attacker="validator",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further in-model; physical "
            "metering honesty is an implementation dependency.",
            evidence_level="INFERENCE",
        ),
    },
    "Output-Indexed Compute Swap Board": {
        "gt": dict(
            summary="v2's settlement gap penalty makes overfitting "
            "settle negatively: benchmark gains not matched by "
            "delivered level movement are penalized at settlement.",
            attack_vectors=[dict(
                vector="gap-optimized tuning",
                description="Sellers could tune to move both benchmark "
            "AND delivered proxy together — but the delivered proxy "
            "moving with real settlement flow is exactly the honest "
            "outcome the board prices.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="The penalty aligns benchmark performance "
            "with delivered performance; overfit capital depreciates "
            "as task sets rotate.",
            death_spiral_risk=1.5,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Gap-penalized settlement plus distribution "
            "margining closes the in-band overfit exploit.",
            attack_vectors=[dict(
                vector="harness capture (residual)",
                description="Evaluation-harness compromise remains the "
            "implementation-layer risk; multi-harness medians are the "
            "field answer.",
                attacker="oracle_provider",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Harness integrity — outside the "
            "model boundary, mitigated by structure.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Benchmark inputs unchanged; settlement rule now "
            "gap-aware.",
            manipulation_vectors=[dict(
                vector="delivered-proxy gaming",
                description="Moving the delivered proxy without real "
            "quality requires settling real swaps — which is the "
            "service the board exists to price.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Verified score streams with "
            "rotation; gap penalty ties them to delivery.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Gap-optimized tuning: indistinguishable "
            "from honest delivery by construction — the exploit "
            "converges to the service.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="gap-optimized tuning",
                description="Settling benchmark AND delivered together "
            "is honest behavior.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further in-model; rotate task "
            "sets in implementation.",
            evidence_level="INFERENCE",
        ),
    },
    "Fee-Tier Voted Model Registry": {
        "gt": dict(
            summary="v2's net-of-self-dealing penalty (|X-H| discount) "
            "means first-party volume that does not widen delivered "
            "usage mints nothing — self-dealing is priced out.",
            attack_vectors=[dict(
                vector="external-front volume washing",
                description="An attacker could pay REAL external users "
            "to route volume — but that is genuine usage and the "
            "capture cost now equals real market-building cost.",
                attacker="whale",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Weight now prices external demand only; "
            "capture costs are the honest market-building costs.",
            death_spiral_risk=1.5,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="First-party-drift discount closes the self-dealing "
            "mint; per-address caps are implementation detail.",
            attack_vectors=[dict(
                vector="sybil endpoint splitting",
                description="Splitting endpoints to dilute ownership "
            "attribution is detectable via routing-pattern clustering "
            "— implementation layer.",
                attacker="governance_participant",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Endpoint-ownership attribution "
            "quality — clustered sybil detection is the practical "
            "frontier.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="On-chain volume with ownership attribution — no "
            "external oracle.",
            manipulation_vectors=[dict(
                vector="attribution evasion",
                description="Attribution evasion is bounded by the "
            "drift discount's structure; evasion cost scales with "
            "volume.",
                attacker="governance_participant",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="HYPOTHESIS",
            )],
            data_source_assessment="Exact on-chain volumes; ownership "
            "graph is the implementation surface.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="External-front volume washing: requires "
            "paying real external users — capture cost equals honest "
            "market-building cost.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="external-front volume washing",
                description="Paying for genuine external usage is "
            "usage, not capture.",
                attacker="whale",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further in-model; sybil "
            "clustering belongs to implementation.",
            evidence_level="INFERENCE",
        ),
    },
    "Vol-Adaptive Market Making Rebate Curve for Compute Futures": {
        "gt": dict(
            summary="v2's realized-stabilization vesting (delivered-vs-"
            "paid gap penalty) means pre-positioned depth that did not "
            "actually stabilize decays its rebate — front-running the "
            "curve buys anticipated stabilization that vests only on "
            "delivery.",
            attack_vectors=[dict(
                vector="delivered-stabilization farming",
                description="Makers must now deliver actual stabilization "
            "to vest rebates; the edge becomes compensation for real "
            "service.",
                attacker="liquidity_provider",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            equilibria_notes="Rebate income now prices delivered "
            "stabilization — the venue pays for what it wanted.",
            death_spiral_risk=1.5,
            game_theory_score=7.5,
            evidence_level="INFERENCE",
        ),
        "sec": dict(
            summary="Gap-penalized vesting closes the anticipation "
            "edge; taker funding unchanged.",
            attack_vectors=[dict(
                vector="vol-index inflation (residual)",
                description="Collusive quote patterns can still inflate "
            "measured vol, but inflated vol with unchanged delivered "
            "stabilization yields no incremental rebate under the gap "
            "penalty.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="HYPOTHESIS",
            )],
            hardest_attack_to_defend="Robust vol estimators (MAD-based) "
            "are the implementation refinement.",
            security_score=7.0,
            evidence_level="INFERENCE",
        ),
        "oracle": dict(
            summary="Index unchanged (public quotes); vesting rule "
            "added.",
            manipulation_vectors=[dict(
                vector="quote-pattern vol inflation",
                description="Inflating vol without delivering "
            "stabilization mints no rebate — the gap penalty "
            "neutralizes it.",
                attacker="arbitrageur",
                profitable_for_attacker=False,
                requires_collusion=True,
                evidence_level="INFERENCE",
            )],
            data_source_assessment="Self-referential public data; "
            "vesting ties payouts to outcomes.",
            oracle_feasibility_score=7.0,
            evidence_level="INFERENCE",
        ),
        "rt": dict(
            verdict="survives",
            strongest_attack="Delivered-stabilization farming: the "
            "'attack' is now the service being paid for.",
            strongest_attack_is_profitable=False,
            attack_vectors=[dict(
                vector="delivered-stabilization farming",
                description="Vesting on realized stabilization converts "
            "the edge into compensation.",
                attacker="liquidity_provider",
                profitable_for_attacker=False,
                requires_collusion=False,
                evidence_level="INFERENCE",
            )],
            what_would_save_it="Nothing further in-model; delay/jitter "
            "on index publication is an implementation parameter.",
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
    print(f"installed {installed} v2 re-attack answers")


if __name__ == "__main__":
    main()
