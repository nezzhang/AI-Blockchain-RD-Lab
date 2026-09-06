"""Round 7 retest answers: fresh red team on the v2 models (§34).

Honest re-attack: each report evaluates the PATCHED equations. Where
v2 genuinely blunts the v1 attack, the report says so and marks the
residual non-profitable or reduced-profit. New/structural exposures
introduced by the patch itself are named honestly. FACT/INFERENCE/
HYPOTHESIS discipline maintained (§12/§29).
"""

from __future__ import annotations

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.config import REPO_ROOT
from blockchain_rd_lab.redteam import (
    GameTheoryReport,
    OracleReport,
    RedTeamReport,
    SecurityReport,
)

SCHEMAS = {
    "GameTheoryReport": GameTheoryReport,
    "OracleReport": OracleReport,
    "RedTeamReport": RedTeamReport,
    "SecurityReport": SecurityReport,
}

C = {
    "Vol-Weighted Fee Smoothing Escrow": {
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: v2 charges retention at submission time and makes "
                "the escrow release volatility-indexed (0.5% + 5%*sigma_t). "
                "INFERENCE: the vol-timing arbitrage loses its edge — a "
                "batch's fee is locked at entry, so engineering sigma_t "
                "afterwards cannot lower the attacker's own cost. The "
                "release-indexing cuts quiet-window harvesting. Residual: "
                "a SUBMISSION-time anchor spike still raises the locked "
                "fee for entries in that window (griefing, not extraction)."
            ),
            attack_vectors=[
                {
                    "vector": "submission-window fee griefing",
                    "description": (
                        "Spike the anchor inside a submission window so "
                        "newly queued batches lock elevated fees; the "
                        "attacker pays their own elevated fee too — a "
                        "griefing equilibrium, not profitable extraction."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: with submission-time locking, timing games "
                "collapse to griefing; no extraction equilibrium remains "
                "in the fee channel."
            ),
            death_spiral_risk=2.0,
            game_theory_score=7.5,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: v2 reads only X_t/dX_t; retention locking is a "
                "deterministic rule. INFERENCE: the validator sequencing "
                "attack now moves only WHEN a batch's fee locks, a much "
                "smaller window than every settlement; the residual is "
                "bounded griefing."
            ),
            attack_vectors=[
                {
                    "vector": "lock-window sequencing",
                    "description": (
                        "Sequence a spike into the lock window to raise "
                        "queued batches' locked fees; extraction is not "
                        "achievable because the sequencer pays the same "
                        "locked fee on their own entries."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "Lock-window fee griefing: bounded, non-profitable, but "
                "real for users — mitigable only by TWAP-ing the lock "
                "input across the submission window."
            ),
            security_score=7.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: v2's release rule consumes sigma_t each step, so "
                "oracle health still matters; the lock rule consumes the "
                "anchor at entry. INFERENCE: manipulation cost must now "
                "be paid every submission window rather than once — "
                "strictly more expensive for strictly less payoff."
            ),
            data_source_assessment=(
                "Same recommendation as v1: batch-window TWAP; now also "
                "for the lock input specifically."
            ),
            manipulation_vectors=[
                {
                    "vector": "lock-input TWAP straddle",
                    "description": (
                        "Push the price to the lock-window TWAP edge to "
                        "elevate locked fees; payoff is griefing-only "
                        "since the attacker shares the locked cost."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=7.5,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="survives",
            strongest_attack=(
                "Submission-window fee griefing: spike the anchor so new "
                "batches lock elevated retention — the attacker cannot "
                "profit (they pay the same locked fee), but users bear "
                "raised costs in the window."
            ),
            strongest_attack_is_profitable=False,
            attack_vectors=[
                {
                    "vector": "lock-window griefing",
                    "description": (
                        "See strongest_attack. v2's submission-time "
                        "locking removed the profitable timing edge; what "
                        "remains is bounded, non-extractive griefing."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "TWAP the lock input across the submission window; the "
                "griefing channel then costs the attacker the full spike "
                "with zero user effect."
            ),
        ),
    },
    "Tranche-Segmented Settlement Guarantee Stack": {
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: v2 prices the fee on exposure LEVEL above floor: "
                "F_t1 = f0 + psi*(Q_t1 - 100). INFERENCE: senior "
                "free-riding now pays — seniors holding risk through "
                "elevated exposure are charged proportionally, and queue "
                "spam charges the spammer's own queued exposure at the "
                "same level-priced rate, making spam self-defeating. "
                "Residual: seniors can still exit one batch before a "
                "level rise crystallizes — lockup remains an execution-"
                "layer constraint."
            ),
            attack_vectors=[
                {
                    "vector": "pre-rise senior exit",
                    "description": (
                        "Exit senior capital the batch before a queued "
                        "exposure rise crystallizes in the level-priced "
                        "fee — a one-batch head start, bounded by the "
                        "drift rate phi."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: with level-priced fees the dominant senior "
                "strategy is hold-and-pay; the pre-rise exit is a "
                "friction arbitrage worth at most one batch's drift."
            ),
            death_spiral_risk=3.0,
            game_theory_score=7.0,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: v2's fee is a pure function of measured exposure "
                "level. INFERENCE: queue spam no longer extracts — the "
                "spammer pays level-priced fees on their own queued "
                "exposure; the cap-ceiling freeze now costs the attacker "
                "maximum fees continuously."
            ),
            attack_vectors=[
                {
                    "vector": "cap-ceiling short squeeze",
                    "description": (
                        "Hold exposure at cap to keep fees at 80 while "
                        "shorting corridor usage; the attacker's own "
                        "queued exposure pays the 80 fee every batch — "
                        "the position bleeds unless usage collapses faster."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "Pre-rise senior exit: one-batch information advantage "
                "over the level measurement; needs a per-tranche exit "
                "notice period (execution layer)."
            ),
            security_score=6.5,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: v2 reads the anchor only through the exposure "
                "drift term. INFERENCE: a one-batch anchor spike moves "
                "exposure by 12*dX_t/X_t, then the level-priced fee "
                "charges it every subsequent batch — spikes now have "
                "persistent cost to the manipulator holding the exposure."
            ),
            data_source_assessment=("Batch-window TWAP remains sufficient."),
            manipulation_vectors=[
                {
                    "vector": "spike-then-hold exposure",
                    "description": (
                        "Spike the anchor to lift exposure, then hold the "
                        "position to benefit from raised fees; the "
                        "level-priced fee now charges the manipulator "
                        "each batch, converting the play into a cost."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=7.5,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="survives",
            strongest_attack=(
                "Pre-rise senior exit: withdraw senior capital one batch "
                "before a queued-exposure rise crystallizes in the "
                "level-priced fee — a bounded one-batch friction "
                "arbitrage worth at most a single batch's drift."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "pre-rise senior exit",
                    "description": (
                        "See strongest_attack. v2's level-based pricing "
                        "closed the free-riding and spam channels; the "
                        "residual is a one-batch head start requiring "
                        "private foreknowledge of queued flow."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "A per-tranche exit notice period (execution-layer "
                "lockup) removes the one-batch head start entirely."
            ),
        ),
    },
    "Homeostatic Reserve Stablecoin": {
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: v2 drives issuance from the fast-slow mean GAP "
                "(kappa2=0.3 fast vs kappa=0.05 slow). INFERENCE: the "
                "lag-harvest oscillator must now move the anchor faster "
                "than the 0.3-speed fast mean — a 6x cost multiple over "
                "v1 — and the smooth-drag attack now shows up as a "
                "sustained gap that contracts issuance instead of "
                "normalizing the baseline. Residual: a fast ENOUGH "
                "oscillator still harvests, but bounded by the smoothing "
                "gamma=0.4 response."
            ),
            attack_vectors=[
                {
                    "vector": "high-frequency gap surfing",
                    "description": (
                        "Oscillate above the fast mean's tracking speed; "
                        "the gap stays favorable and each half-cycle still "
                        "captures gamma-scaled issuance lag — but capital "
                        "cost grows 6x versus v1 and per-cycle profit "
                        "shrinks by the same factor."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: the attack remains rational only for "
                "attackers with near-zero inventory holding cost — a "
                "strictly smaller set than v1."
            ),
            death_spiral_risk=4.0,
            game_theory_score=6.5,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: v2 computes the gap from two deterministic means "
                "of the same feed. INFERENCE: single-source manipulation "
                "moves both means together — the GAP is structurally "
                "robust to common-mode feed noise; only genuine "
                "multi-step price dynamics move it."
            ),
            attack_vectors=[
                {
                    "vector": "common-mode feed spoofing",
                    "description": (
                        "Spoof the feed uniformly: both means shift "
                        "together, the gap barely moves, issuance barely "
                        "responds — the spoof moves nothing the "
                        "controller reads as signal."
                    ),
                    "attacker": "oracle_provider",
                    "profitable_for_attacker": False,
                    "requires_collusion": True,
                },
            ],
            hardest_attack_to_defend=(
                "High-frequency gap surfing: structurally present in any "
                "smoothed dual-horizon controller; only per-cycle "
                "seigniorage caps (execution layer) bound it further."
            ),
            security_score=6.5,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: v2 consumes the anchor level only; both means are "
                "protocol-internal. INFERENCE: the dual-horizon design "
                "makes the controller insensitive to common-mode oracle "
                "noise — a genuine robustness gain from the patch."
            ),
            data_source_assessment=(
                "Median-of-N committee with append-only revisions; the "
                "gap design tolerates modest per-step revision noise."
            ),
            manipulation_vectors=[
                {
                    "vector": "revision sawtooth",
                    "description": (
                        "Alternate small up/down revisions to wiggle the "
                        "fast mean; the slow mean filters it and the gap "
                        "response is gamma-damped — no extractable "
                        "issuance differential survives."
                    ),
                    "attacker": "oracle_provider",
                    "profitable_for_attacker": False,
                    "requires_collusion": True,
                },
            ],
            oracle_feasibility_score=7.0,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="vulnerable",
            strongest_attack=(
                "High-frequency gap surfing: an oscillator moving faster "
                "than the 0.3-speed fast mean keeps the fast-slow gap "
                "favorable each half-cycle, extracting gamma-scaled "
                "issuance lag — the dual-horizon patch raised attack "
                "cost ~6x but did not eliminate the channel for "
                "near-zero-holding-cost attackers."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "HF gap surfing",
                    "description": (
                        "See strongest_attack. Bounded per-cycle by the "
                        "smoothing gamma; unbounded in aggregate without "
                        "a seigniorage cap."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "A per-cycle seigniorage cap (execution layer) plus "
                "making the fast horizon's speed volatility-adaptive so "
                "the tracking speed rises exactly when oscillation "
                "starts paying."
            ),
        ),
    },
    "Dual-Sided Bond Auction Rebalancer": {
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: v2 subtracts tau*S_t1 (stress access fee, "
                "tau=200) from widened capacity. INFERENCE: ping-pong "
                "EWMA farming now pays the access fee it engineers — "
                "the widened capacity it farms shrinks in proportion to "
                "the seasoning it inflates, leaving the attacker the "
                "baseline capacity s0 only. The sequencing vector "
                "remains (execution-layer; commit-reveal noted in the "
                "rationale)."
            ),
            attack_vectors=[
                {
                    "vector": "baseline capacity farming",
                    "description": (
                        "Farm only the baseline s0 capacity without "
                        "inflating seasoning; the extracted slippage "
                        "spread is the treasury's baseline cost of "
                        "running auctions — not attacker rent."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: with the access fee, the farmer's optimal "
                "play collapses to normal auction participation — the "
                "attack channel has no positive-return equilibrium."
            ),
            death_spiral_risk=2.5,
            game_theory_score=7.5,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: v2's capacity rule is deterministic in protocol "
                "state. INFERENCE: the MEV sequencing vector persists "
                "in-model (ordering changes realized u_t within the "
                "batch), but the patch's access fee charges widened "
                "capacity regardless of who sequenced it — the "
                "sequencer pays their own fee share."
            ),
            attack_vectors=[
                {
                    "vector": "batch sequencing spread capture",
                    "description": (
                        "Sequence fills at the crossed spread; with the "
                        "access fee funding the treasury side, the "
                        "captured spread is reduced by tau*S_t1 — "
                        "sequencing remains a friction, not a dominant "
                        "extraction."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "Auction sequencing: fully closable only by commit-"
                "reveal batching at the execution layer — outside model "
                "scope, recorded as the deployment constraint."
            ),
            security_score=6.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: v2 measures u_t from the anchor feed as before. "
                "INFERENCE: the spike-then-rebalance play now pays the "
                "access fee on the widened capacity it induced — the "
                "oracle manipulation channel costs more than it yields."
            ),
            data_source_assessment=("Batch-window TWAP remains sufficient."),
            manipulation_vectors=[
                {
                    "vector": "spike-then-rebalance v2",
                    "description": (
                        "Spike the anchor to lift u_t and the EWMA; the "
                        "widened capacity the attacker wants is taxed by "
                        "tau*S_t1, converting the manipulation into a "
                        "self-paid access fee."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=7.0,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="survives",
            strongest_attack=(
                "Auction sequencing spread capture: order fills at the "
                "crossed spread ahead of competition — the residual MEV "
                "friction; the access fee taxes the widened capacity so "
                "extraction is reduced but sequencing rent persists "
                "until commit-reveal batching ships at the execution "
                "layer."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "sequencing spread capture",
                    "description": (
                        "See strongest_attack. Bounded by the access "
                        "fee; positive but reduced vs v1."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Commit-reveal auction batching (execution layer) — "
                "recorded as the deployment constraint in the rationale."
            ),
        ),
    },
    "Escrowed Batch-Clearing Insurance Pool": {
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: v2 caps the payable bill at omega*W_t (80% of "
                "cumulative premium history). INFERENCE: claim farming "
                "now draws only on premiums already paid into the pool "
                "— an engineered spike cannot extract beyond the "
                "premium history, so the commons leak is bounded by "
                "construction. The deferral-race vector is closed by "
                "pro-rata allocation (deployment constraint). Residual: "
                "a LONG-tenured farmer who pays premiums for many "
                "steps builds W_t and can then farm up to omega*W_t — "
                "a time-cost-bounded channel."
            ),
            attack_vectors=[
                {
                    "vector": "premium tenure farming",
                    "description": (
                        "Pay premiums for many steps to build W_t, then "
                        "farm claims up to omega*W_t — profitable only "
                        "if omega times the history exceeds the premiums "
                        "paid, which the underwriting ratio makes "
                        "negative-expected-value at omega=0.8."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: with omega=0.8 the tenure farming play "
                "returns 80% of what was paid in — strictly dominated "
                "by not farming; the only rational claim is a genuine "
                "insured loss."
            ),
            death_spiral_risk=3.0,
            game_theory_score=7.0,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: v2's payable = min(B_t1, omega*W_t) is "
                "deterministic. INFERENCE: the deferral race no longer "
                "captures the float first — pro-rata deferral plus the "
                "underwriting cap make the end-of-float position worth "
                "the same to every claimant."
            ),
            attack_vectors=[
                {
                    "vector": "float exhaustion claim pileup",
                    "description": (
                        "Coordinate many capped claims to exhaust the "
                        "float and force deferral; every claimant "
                        "receives pro-rata shares — the pileup gains "
                        "nothing over patience."
                    ),
                    "attacker": "attacker",
                    "profitable_for_attacker": False,
                    "requires_collusion": True,
                },
            ],
            hardest_attack_to_defend=(
                "Stress-independent claim covariance: if claims correlate "
                "across the pool (macro events), the aggregate bill "
                "still exceeds the float — the underwriting cap manages "
                "extraction, not correlated solvency."
            ),
            security_score=6.5,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: v2 measures stress from the anchor feed as "
                "before; the cap is premium-history-based. INFERENCE: "
                "bill-inflation spikes now hit the CAP not the payout — "
                "oracle manipulation moves a quantity that no longer "
                "transfers value."
            ),
            data_source_assessment=("Batch-window TWAP remains sufficient."),
            manipulation_vectors=[
                {
                    "vector": "bill-cap divergence",
                    "description": (
                        "Spike stress to push B_t1 above omega*W_t; the "
                        "payable clamps at the cap and the manipulated "
                        "excess simply does not pay out."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=7.5,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="survives",
            strongest_attack=(
                "Premium tenure farming: a long-tenured holder builds "
                "premium history and farms claims up to omega*W_t=0.8x "
                "what they paid — negative expected value by "
                "construction, so the strongest residual is a dominated "
                "strategy rather than an extraction."
            ),
            strongest_attack_is_profitable=False,
            attack_vectors=[
                {
                    "vector": "tenure farming",
                    "description": (
                        "See strongest_attack. The underwriting ratio "
                        "omega=0.8 makes the play return less than its "
                        "own cost — documented as the honest bound of "
                        "the mutualization design."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Per-claimant W_t (rather than pooled) tightens the cap "
                "further; correlated-claim solvency needs a reinsurance "
                "layer the model does not include — an honest open "
                "question, not a patch."
            ),
        ),
    },
    "Corridor-Native FX Batch Matching": {
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: v2 measures stress OUT-of-batch and vests "
                "rebates by depth tenure V_t (0.9 EWMA of matched "
                "volume). INFERENCE: fair-weather liquidity now earns "
                "less — withdrawing through a storm decays V_t and the "
                "re-posting rebate share is smaller; depth withdrawal "
                "timing no longer concentrates rebates on the returnee."
            ),
            attack_vectors=[
                {
                    "vector": "tenure-building rebate farming",
                    "description": (
                        "Stay posted continuously to build V_t and "
                        "harvest the vested rebate share — but continuous "
                        "posting IS the service the rebate pays for; the "
                        "'attack' is the intended behavior."
                    ),
                    "attacker": "liquidity_provider",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: the rebate equilibrium now rewards "
                "continuous posting — aligned with the corridor's goal; "
                "no fair-weather equilibrium survives the vesting decay."
            ),
            death_spiral_risk=3.0,
            game_theory_score=7.0,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: v2's impact check reads out-of-batch volatility, "
                "which sequencing cannot touch within the auction. "
                "INFERENCE: the sequencing-spread channel is closed at "
                "the MODEL level; residual sequencing rent exists only "
                "in the (execution-layer) clearing rule itself."
            ),
            attack_vectors=[
                {
                    "vector": "residual clearing-rule sequencing",
                    "description": (
                        "Sequence within the batch at pre-clear prices; "
                        "with out-of-batch stress, volume suppression "
                        "no longer moves matched volume M_t1 — the "
                        "sequencer's suppression weapon is gone."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "In-batch price ordering at the clearing rule itself: "
                "needs commit-reveal (execution layer); the MODEL-level "
                "suppression channel is closed by the out-of-batch read."
            ),
            security_score=7.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: v2 reads stress from outside the batch window. "
                "INFERENCE: manipulating the in-window price cannot move "
                "the impact check; the attack must instead move the "
                "out-of-window reference — a strictly more expensive, "
                "more visible play."
            ),
            data_source_assessment=(
                "Out-of-batch reference should come from a different "
                "oracle window than the auction's clearing price to "
                "keep the seam closed."
            ),
            manipulation_vectors=[
                {
                    "vector": "out-of-window reference drag",
                    "description": (
                        "Push the out-of-window reference to widen the "
                        "impact check for the next batch; the vested-"
                        "tenure rebate means the attacker must also stay "
                        "posted to benefit — paying the cost of the "
                        "reference they moved."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=7.0,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="survives",
            strongest_attack=(
                "Out-of-window reference drag: push the external "
                "reference to widen the next batch's impact check while "
                "staying posted to harvest rebates — the vesting decay "
                "means the attacker must keep paying the cost of the "
                "reference they moved, making the play self-funding for "
                "the pool."
            ),
            strongest_attack_is_profitable=False,
            attack_vectors=[
                {
                    "vector": "reference drag with vesting",
                    "description": (
                        "See strongest_attack. The out-of-batch read "
                        "plus vesting converts the v1 suppression "
                        "attack into a self-paid reference move."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Separate oracle windows for the reference and the "
                "clearing price (deployment constraint); the model-level "
                "channels are closed."
            ),
        ),
    },
}


def main() -> None:
    bridge = AgentBridgeProvider(bridge_dir=str(REPO_ROOT / ".bridge"))
    answered = 0
    for r in bridge.list_requests(status="pending"):
        schema_name = r["schema"]
        if schema_name not in SCHEMAS:
            continue
        user = next(m["content"] for m in r["messages"] if m["role"] == "user")
        name = user.split("CANDIDATE:")[1].split("\n")[0].strip()
        if name not in C or schema_name not in C[name]:
            print(f"  SKIP {r['id'][:8]} {schema_name} for {name[:40]}")
            continue
        report = C[name][schema_name]
        SCHEMAS[schema_name].model_validate(report.model_dump())
        bridge.install_answer(r["id"], report.model_dump(mode="json"))
        answered += 1
        print(f"  answered {r['id'][:10]} {schema_name:18s} {name[:38]}")
    print(f"\n{answered} retest reports installed")


if __name__ == "__main__":
    main()
