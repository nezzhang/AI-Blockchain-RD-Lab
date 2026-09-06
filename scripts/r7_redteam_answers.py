"""Round 7 red-team answers: authored adversarial analysis (§9/§30).

Each report is genuine research content: the attack reasoning targets
the CORRECTED model's actual equations (read from the brief's
formal_model), grounded in the §15 evidence that now exists. Facts vs
inference vs hypothesis distinguished (§12/§29). No absolute claims.

Validation discipline: every report is schema-validated against the
request's schema before writing the answer file.
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

# ----------------------------------------------------------------- content
# Per candidate: {schema: report}. Attacks reference the corrected
# equations honestly — including that the §15 battery now distinguishes
# scenarios (that is measured FACT), while attack profitability remains
# HYPOTHESIS unless simulated.

C = {
    "cand-cd39d95ea572": {  # Vol-Weighted Fee Smoothing Escrow
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: retention responds to realized relative volatility "
                "|dX_t|/X_t with bounds [0.1, 0.9], and §15 shows 13/13 "
                "distinct trajectories. INFERENCE: a volatility oscillator "
                "can still extract rent — an attacker who can move the "
                "anchor by delta in one step raises retention to delta-"
                "dependent levels, then transacts when vol decays and "
                "retention (hence effective fees) falls. The 0.02 escrow "
                "release leak is small, so retained fees accrue to the "
                "pool, not the attacker; the attack extracts via timing "
                "fees, not pool theft."
            ),
            attack_vectors=[
                {
                    "vector": "vol timing fee arbitrage",
                    "description": (
                        "Oscillate the anchor to push sigma_t up (retention "
                        "rises, users pay more into escrow), then clear "
                        "large batches in the quiet window while retention "
                        "decays toward 0.1 — pay the floor fee while having "
                        "caused others to prepay the ceiling."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "escrow drain via release rate",
                    "description": (
                        "The 2% per-step release is unconditional; an "
                        "attacker holding settlement rights during a "
                        "calm stretch captures released escrow without "
                        "having funded the stress that filled it."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: the retention game has no pure dominant "
                "strategy for users — waiting for low retention is "
                "optimal per-batch but stale if the queue clears first. "
                "The escrow's floor (100) bounds worst-case drain; the "
                "cap (1e5) is far above the reachable range (battery "
                "means ~3.7k), so the cap is not economically binding."
            ),
            death_spiral_risk=2.5,
            game_theory_score=6.5,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: all quantities derive from on-chain-observable X_t "
                "and dX_t; no external oracle is needed. INFERENCE: the "
                "attack surface is the anchor price itself — whoever "
                "moves X_t inside a batch window moves retention. The "
                "escrow cap at 1e5 and floor at 100 bound state theft; "
                "the residual risk is economic (fee timing), not "
                "cryptographic."
            ),
            attack_vectors=[
                {
                    "vector": "anchor manipulation inside batch window",
                    "description": (
                        "A dominant validator or MEV bundle reorders to "
                        "create a large dX_t immediately before fee "
                        "computation, raising retention for that batch "
                        "and capturing the differential from users who "
                        "cannot reprice."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "retention ratchet griefing",
                    "description": (
                        "Repeated small oscillations keep sigma_t "
                        "elevated, pinning retention near its 0.9 bound "
                        "for honest users while the griefer's cost is "
                        "only the oscillation capital's own fees."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": False,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "In-batch anchor manipulation by validators: the model "
                "reads X_t/dX_t as given, so the defense must live at "
                "the oracle/timestamp layer the model assumes away."
            ),
            security_score=6.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: the model consumes only the anchor level and its "
                "per-step delta; both are candidate oracle feeds. "
                "INFERENCE: a median-of-N price feed with per-batch "
                "timestamps bounds single-source manipulation; the "
                "manipulation cost scales with the depth needed to move "
                "the median, which the retention response amplifies into "
                "user fees."
            ),
            data_source_assessment=(
                "A DEX spot price with TWAP smoothing over the batch "
                "window is the minimum honest source; a committee feed "
                "adds latency but resists single-block manipulation. "
                "Revisions are unnecessary — the model only needs the "
                "level and delta once per batch."
            ),
            manipulation_vectors=[
                {
                    "vector": "single-block spot spike",
                    "description": (
                        "Manipulate a thin DEX pool for one block to "
                        "spike dX_t, inflating sigma_t and retention "
                        "for that batch; profit from users locked into "
                        "pre-committed fees."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "TWAP window straddling",
                    "description": (
                        "Push the price to the edge of the TWAP window "
                        "so the reported delta stays elevated across "
                        "several batches without holding the position "
                        "through settlement."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=7.0,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="survives",
            strongest_attack=(
                "Volatility-timing fee arbitrage: an attacker with anchor "
                "influence engineers high sigma_t to inflate retention "
                "for others' batches, then settles their own volume in "
                "the induced quiet window at the 0.1 retention floor."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "oscillation fee farming",
                    "description": (
                        "See strongest_attack. Measured §15 dynamics show "
                        "retention genuinely responsive (13/13 distinct "
                        "trajectories), so the attack changes real fees, "
                        "not vacuous ones — this is the honest cost of "
                        "the mechanism's responsiveness."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "quiet-window queue stuffing",
                    "description": (
                        "After engineering a stress peak, submit the "
                        "attacker's queued volume as sigma_t decays, "
                        "harvesting the floor retention."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Charge retention determined at SUBMISSION time, not "
                "clearance time, removing the timing edge; and make the "
                "escrow release rate volatility-indexed so quiet-window "
                "harvesting returns less to the harvester."
            ),
        ),
    },
    "cand-5d41cd41f68d": {  # Tranche-Segmented Settlement Guarantee Stack
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: exposure Q_t drifts with phi=0.006 and responds "
                "to dX_t/X_t; fee F_t pressure is linear in relative "
                "exposure growth with bounds [5, 80]; §15 shows 13/13 "
                "distinct trajectories. INFERENCE: senior tranche "
                "providers can free-ride: they earn the guarantee fee "
                "while first-loss tranches absorb shocks; the aggregate "
                "fee schedule underprices tail risk because pressure "
                "scales with growth rate, not level."
            ),
            attack_vectors=[
                {
                    "vector": "senior tranche yield farming",
                    "description": (
                        "Load capital into the seniormost tranche, "
                        "collect guarantee fees priced off exposure "
                        "GROWTH, exit before a slow-building exposure "
                        "level (cap 2500) converts into losses."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "exposure ratchet gaming",
                    "description": (
                        "Coordinate queued exposure in small increments "
                        "below the fee-pressure sensitivity so F_t never "
                        "rises while Q_t climbs toward its cap."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": True,
                },
            ],
            equilibria_notes=(
                "INFERENCE: the fee game has a dominant strategy for "
                "seniors (stay, harvest, exit early) because solvency "
                "checks bind on the aggregate, not per-tranche "
                "withdrawal. A per-tranche lockup would change the "
                "equilibrium to hold-through-stress."
            ),
            death_spiral_risk=4.0,
            game_theory_score=5.5,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: the model runs on-chain from observables only; no "
                "oracle beyond the anchor feed. INFERENCE: the critical "
                "attack is queue-depth manipulation — queued exposure "
                "is protocol-internal, so a spam campaign can inflate Q_t "
                "toward its cap, triggering the maximum fee on honest "
                "users (a griefing vector with fee revenue diverted to "
                "whomever holds guarantee capital)."
            ),
            attack_vectors=[
                {
                    "vector": "queue spam fee inflation",
                    "description": (
                        "Spam the settlement queue to push Q_t1 to cap, "
                        "raising guarantee fees to the 80 ceiling for "
                        "honest batch participants while the spammer "
                        "holds guarantee capital and collects."
                    ),
                    "attacker": "attacker",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "cap-ceiling credit freeze",
                    "description": (
                        "Hold Q_t pinned at cap=2500 so the fee sits at "
                        "80 and settlement activity migrates elsewhere; "
                        "the attacker shorts the corridor's usage."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "Queue spam with capital at both ends: the mechanism "
                "cannot distinguish legitimate queued exposure from "
                "adversarial volume without identity/bonding assumptions "
                "the model does not make."
            ),
            security_score=5.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: only X_t/dX_t feed the model; queue depth is "
                "protocol-internal. INFERENCE: anchor manipulation "
                "shifts exposure dynamics modestly (phi*dX_t/X_t term) "
                "— the fee pressure responds to growth, so a one-step "
                "anchor spike has bounded effect on F_t."
            ),
            data_source_assessment=(
                "Batch-window TWAP on the anchor suffices; the exposure "
                "term already smooths single spikes. Committee feeds are "
                "overkill for this sensitivity profile."
            ),
            manipulation_vectors=[
                {
                    "vector": "anchor spike exposure inflation",
                    "description": (
                        "Spike the anchor for one batch to add 12*dX_t/X_t "
                        "to exposure, nudging Q_t1 toward cap and fees up "
                        "for subsequent batches."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=7.5,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="vulnerable",
            strongest_attack=(
                "Senior tranche free-riding: guarantee fees price "
                "exposure growth, not exposure level or tranche risk, so "
                "senior capital harvests fees and exits before slowly "
                "accumulated exposure (Q_t toward cap 2500) turns into "
                "first-loss claims — the aggregate schedule leaves "
                "juniors holding the tail."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "senior harvest-and-exit",
                    "description": (
                        "See strongest_attack. The §15 evidence shows the "
                        "fee genuinely responds (13/13 distinct runs), so "
                        "the flaw is economic structure, not simulation "
                        "artifacts."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "queue spam fee squeeze",
                    "description": (
                        "Inflate queued exposure to the cap to harvest "
                        "maximum guarantee fees from honest settlers."
                    ),
                    "attacker": "attacker",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Price fees off exposure LEVEL and tranche seniority, "
                "not growth; add per-tranche lockup through stress; make "
                "queue admission bond-backed so spam costs capital."
            ),
        ),
    },
    "cand-a6cb3c735045": {  # Homeostatic Reserve Stablecoin
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: issuance I_t smoothly tracks i0 - lambda*relative "
                "deviation via convex smoothing (gamma=0.4); mean tracker "
                "P_t follows the anchor with kappa=0.05; §15 shows 13/13 "
                "distinct trajectories with no pinned states. INFERENCE: "
                "the smoothing that prevents pinning also creates lag — "
                "an attacker who oscillates the anchor around P_t keeps "
                "issuance perpetually behind, harvesting seigniorage on "
                "each expansion half-cycle."
            ),
            attack_vectors=[
                {
                    "vector": "lag-harvest oscillation",
                    "description": (
                        "Oscillate X_t around the slowly-moving P_t: buy "
                        "expansion (issuance up) each trough, sell into "
                        "contraction each peak; the convex controller "
                        "always confirms one step late."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "mean-tracker dragging",
                    "description": (
                        "Sustained pressure moves P_t itself (kappa=0.05), "
                        "lowering the deviation the controller sees and "
                        "normalizing an artificial price level."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: against a gamma-smoothed controller, the "
                "oscillator's per-cycle profit scales with lambda and "
                "the oscillation amplitude; P_t dragging is the more "
                "dangerous equilibrium because it converts a transient "
                "manipulation into a persistent baseline shift."
            ),
            death_spiral_risk=5.5,
            game_theory_score=5.0,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: inputs are the anchor level/delta only; states "
                "are protocol-internal (P_t, I_t). INFERENCE: no "
                "cryptographic surface beyond the anchor feed; the risk "
                "is economic lag exploitation. The unclipped design means "
                "no bounds to attack — but also no structural caps "
                "limiting a manipulated regime."
            ),
            attack_vectors=[
                {
                    "vector": "deviation masking",
                    "description": (
                        "Push the anchor smoothly so each per-step delta "
                        "stays small while the cumulative drift is large; "
                        "the controller's relative-deviation term never "
                        "sees a big single-step signal and issuance "
                        "follows the drag."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "Slow-drift deviation masking: any threshold or rate "
                "controller is blind to gradients below its per-step "
                "sensitivity; defense requires multi-horizon deviation "
                "measures the model does not include."
            ),
            security_score=5.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: the controller consumes anchor level and delta "
                "each step — oracle health IS the mechanism's health. "
                "INFERENCE: a committee feed with bounded per-step "
                "revisions caps the drag attack's speed; a single DEX "
                "feed makes P_t follow manipulable prices directly."
            ),
            data_source_assessment=(
                "Median-of-N committee with per-step revision bounds; "
                "TWAP adds lag that compounds the controller's own lag — "
                "inadvisable here. Revision policy must be append-only."
            ),
            manipulation_vectors=[
                {
                    "vector": "cumulative drift via small revisions",
                    "description": (
                        "Each oracle revision moves the anchor a little; "
                        "cumulative movement drags P_t while every "
                        "per-step delta passes the manipulation check."
                    ),
                    "attacker": "oracle_provider",
                    "profitable_for_attacker": True,
                    "requires_collusion": True,
                },
            ],
            oracle_feasibility_score=6.0,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="vulnerable",
            strongest_attack=(
                "Lag-harvest oscillation: the gamma-smoothed issuance "
                "controller confirms every price move one step late, so "
                "an oscillator buys expansion troughs and sells into "
                "contraction peaks, extracting seigniorage each cycle — "
                "profit scales with amplitude, and the unclipped design "
                "offers no structural cap to stop it."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "oscillation seigniorage",
                    "description": (
                        "See strongest_attack. §15's 13/13 distinct "
                        "trajectories confirm the controller genuinely "
                        "tracks — the flaw is the tracking lag, not any "
                        "simulation artifact."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "slow-drag baseline shift",
                    "description": (
                        "Move the anchor persistently so P_t (kappa=0.05) "
                        "follows, redefining 'the mean' and un-anchoring "
                        "the stablecoin's reference level."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Multi-horizon deviation measures (fast + slow means) "
                "with issuance responding to their GAP; per-cycle "
                "seigniorage caps; and an anchor committee whose "
                "revisions are bounded per step."
            ),
        ),
    },
    "cand-3132499bb565": {  # Dual-Sided Bond Auction Rebalancer
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: capacity C_t grows with a stress EWMA S_t "
                "(weight 0.1) and deviation D_t; deviation responds to "
                "800*u_t and shrinks 0.5*C_t; §15 shows 13/13 distinct "
                "trajectories. INFERENCE: an attacker who alternates "
                "large opposite anchor moves keeps S_t elevated, "
                "harvesting the elevated capacity to rebalance THEIR "
                "inventory at the crossed spread while the treasury "
                "absorbs slippage both directions."
            ),
            attack_vectors=[
                {
                    "vector": "stress EWMA ping-pong",
                    "description": (
                        "Alternate big up/down anchor moves so u_t and "
                        "the EWMA S_t stay high, keeping capacity C_t "
                        "near its 500 cap; the attacker's rebalancing "
                        "flow rides treasury-paid capacity each round."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "deviation floor squatting",
                    "description": (
                        "Keep D_t near its 20 floor via opposite trades, "
                        "then submit one large move — the 800*u_t term "
                        "spikes deviation, capacity follows, and the "
                        "attacker's next-round flow gets the widened "
                        "capacity at stale spread."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: with capacity responsive to stress, honest "
                "rebalancers and the attacker are complements in calm "
                "regimes and rivals in stressed ones — the attacker wins "
                "whenever their oscillation cost is below the slippage "
                "the treasury eats on the widened capacity."
            ),
            death_spiral_risk=3.5,
            game_theory_score=5.5,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: all quantities are protocol-internal plus the "
                "anchor feed; no custody beyond the escrowed legs. "
                "INFERENCE: the crossed-spread auction is MEV-"
                "reorderable — a validator can sequence auction "
                "participation to fill against the widened capacity "
                "first."
            ),
            attack_vectors=[
                {
                    "vector": "auction sequencing MEV",
                    "description": (
                        "Reorder auction participation so the attacker's "
                        "fills clear at the crossed spread before "
                        "competition narrows it, harvesting the spread "
                        "the dual-sided structure creates."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "Sequencing extraction: any batch auction with a "
                "deterministic clearing rule leaks rent to whoever "
                "controls ordering; commit-reveal batching is the "
                "known mitigation this model omits."
            ),
            security_score=5.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: the mechanism consumes X_t/dX_t for stress; bond "
                "inventory valuations also need a price. INFERENCE: the "
                "stress term u_t is manipulation-sensitive — a one-block "
                "anchor spike inflates u_t and the EWMA trails it for "
                "~10 steps, widening capacity for the attacker's "
                "subsequent flow."
            ),
            data_source_assessment=(
                "Per-batch TWAP on the anchor limits single-block spikes; "
                "bond fair values should come from a separate committee "
                "feed so one manipulated source cannot move both stress "
                "and valuation."
            ),
            manipulation_vectors=[
                {
                    "vector": "spike-then-rebalance",
                    "description": (
                        "Spike the anchor to lift u_t; the EWMA keeps "
                        "capacity high for the next ~10 batches; submit "
                        "rebalancing flow into that widened window."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=6.5,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="survives",
            strongest_attack=(
                "Stress-EWMA capacity farming: alternate anchor moves to "
                "keep the seasoning EWMA elevated, then rebalance "
                "inventory through the widened capacity at the crossed "
                "spread, socializing slippage onto the treasury."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "ping-pong capacity farming",
                    "description": (
                        "See strongest_attack. §15 shows capacity and "
                        "deviation genuinely responsive (13/13 distinct) "
                        "— the attack exploits that responsiveness, so "
                        "it is a real economic exposure, not an artifact."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "auction sequencing MEV",
                    "description": (
                        "Sequence fills at the crossed spread ahead of "
                        "competition each round."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Commit-reveal auction batching (kills sequencing rent); "
                "charge an explicit stress-proportional access fee for "
                "widened capacity so the farmer pays for the EWMA they "
                "inflated."
            ),
        ),
    },
    "cand-e8e15b483070": {  # Escrowed Batch-Clearing Insurance Pool
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: the claim bill B_t1 responds to relative anchor "
                "stress (chi*300*|dX_t|/X_t, bounds [20, 500]); the "
                "float L_t1 adds premiums (25/step) and pays the bill "
                "with a 150 floor; §15 shows 12/13 distinct finals. "
                "INFERENCE: an attacker can farm claims — engineer "
                "stress spikes right before their insured position "
                "triggers, drawing from the shared float that honest "
                "premiums funded."
            ),
            attack_vectors=[
                {
                    "vector": "stress-timed claim farming",
                    "description": (
                        "Hold an insured position correlated with the "
                        "anchor; spike anchor stress so B_t1 jumps toward "
                        "its 500 ceiling the batch before the claim "
                        "triggers; the shared float pays out at the "
                        "inflated bill."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "float floor rationing race",
                    "description": (
                        "When the float nears its 150 floor, claims "
                        "defer; front-run the deferral with a large "
                        "claim to capture remaining float before other "
                        "claimants' deferrals."
                    ),
                    "attacker": "attacker",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: claim farming is rational whenever the cost "
                "of spiking anchor stress is below the marginal bill "
                "inflation chi*300*|dX_t|/X_t; the shared-float design "
                "makes this a commons — each farmer's claim draws on "
                "premiums others paid."
            ),
            death_spiral_risk=5.0,
            game_theory_score=5.0,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: inputs are the anchor feed only; the float and "
                "bill are protocol-internal. INFERENCE: the floor at 150 "
                "turns insolvency into deferral (honest), but deferral "
                "priority is unspecified — a first-come-first-served rule "
                "is a race vulnerability the model leaves open."
            ),
            attack_vectors=[
                {
                    "vector": "deferral race front-running",
                    "description": (
                        "Observe a large claim queue near the float "
                        "floor; front-run with a maximizing claim to "
                        "capture float before the batch defers others."
                    ),
                    "attacker": "attacker",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "premium withholding griefing",
                    "description": (
                        "Coordinate premium payers to withhold during "
                        "stress, accelerating the float's approach to "
                        "the floor and forcing deferrals that damage "
                        "honest claimants' liquidity."
                    ),
                    "attacker": "governance_participant",
                    "profitable_for_attacker": False,
                    "requires_collusion": True,
                },
            ],
            hardest_attack_to_defend=(
                "Claim-bill inflation via anchor stress: the bill "
                "legitimately responds to stress, so defense must make "
                "claims provably independent of the holder's own market "
                "activity — an underwriting problem, not an on-chain "
                "one."
            ),
            security_score=5.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: the bill reads relative anchor stress "
                "(|dX_t|/X_t). INFERENCE: oracle manipulation directly "
                "inflates the bill; a per-batch TWAP bounds the spike's "
                "size, and chi*300 scaling means a 1% engineered move "
                "adds 3 to the bill — proportionate but attackable in "
                "aggregate."
            ),
            data_source_assessment=(
                "Batch-window TWAP plus a staleness check; claims should "
                "settle against the same window the bill priced so the "
                "attacker cannot arbitrage the seam between them."
            ),
            manipulation_vectors=[
                {
                    "vector": "bill inflation spike",
                    "description": (
                        "Spike the anchor inside the batch window to "
                        "inflate |dX_t|, raising the bill the shared "
                        "float pays on the attacker's claim."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=6.5,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="vulnerable",
            strongest_attack=(
                "Stress-timed claim farming: an insured whale engineers "
                "anchor stress so the claim bill is at its ceiling when "
                "their own claim triggers, drawing inflated payouts from "
                "the shared float that honest premiums funded — the bill "
                "legitimately responds to stress, so the pool's "
                "commons structure converts responsiveness into "
                "extractable rent."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "claim farming",
                    "description": (
                        "See strongest_attack. §15's 12/13 distinct "
                        "finals confirm genuine float dynamics; the "
                        "flaw is structural (shared bill), not a "
                        "simulation artifact."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "deferral race",
                    "description": (
                        "Front-run near-floor deferrals to capture "
                        "remaining float first."
                    ),
                    "attacker": "attacker",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Per-claim underwriting that caps any holder's payout "
                "relative to their premium history; independent stress "
                "measurement (separate oracle window) for bill pricing "
                "vs claim settlement; and pro-rata (not first-come) "
                "deferral allocation."
            ),
        ),
    },
    "cand-a98b49da7189": {  # Corridor-Native FX Batch Matching
        "GameTheoryReport": GameTheoryReport(
            summary=(
                "FACT: matched volume M_t1 = 400*theta*(1 - k_imp*100*"
                "|dX_t|/X_t) shrinks with relative stress (bounds [50, "
                "400]); the rebate pool R_t1 earns 0.02*M_t1 with 5% "
                "decay (bounds [20, 3000]); §15 shows 13/13 distinct "
                "finals. INFERENCE: a liquidity provider can withdraw "
                "posted depth exactly when stress (and thus impact "
                "shrinking) is profitable to engineer, forcing small "
                "M_t1 and capturing rebate share with less inventory "
                "risk."
            ),
            attack_vectors=[
                {
                    "vector": "depth withdrawal timing",
                    "description": (
                        "Post inventory, harvest rebates while calm "
                        "(M_t1 high), withdraw the instant engineered "
                        "stress would force negative selection — the "
                        "impact check shrinks matched volume for "
                        "remaining providers, concentrating rebates on "
                        "the attacker who re-posts after the storm."
                    ),
                    "attacker": "liquidity_provider",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "rebate pool decay harvesting",
                    "description": (
                        "Let the pool accumulate (r0 + 2% of matched "
                        "volume, capped 3000), then dominate matching in "
                        "one batch to capture a rebate share "
                        "disproportionate to posted depth tenure."
                    ),
                    "attacker": "arbitrageur",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            equilibria_notes=(
                "INFERENCE: providers face a war-of-attrition on depth "
                "during stress; the 5% decay punishes absent providers, "
                "but the impact check's volume shrinkage raises the "
                "survivor's rebate share — an equilibrium that rewards "
                "fair-weather liquidity exactly when the corridor needs "
                "it most."
            ),
            death_spiral_risk=4.5,
            game_theory_score=5.5,
        ),
        "SecurityReport": SecurityReport(
            summary=(
                "FACT: the mechanism runs from the anchor feed and "
                "protocol-internal volume/rebate states. INFERENCE: the "
                "impact check's k_imp term makes batch outcomes "
                "sequencing-sensitive — a validator can order large "
                "flows to maximize |dX_t| seen by the check, shrinking "
                "others' matched volume while their own fills settle "
                "at pre-shrink prices."
            ),
            attack_vectors=[
                {
                    "vector": "impact-check sequencing",
                    "description": (
                        "Sequence trades so the anchor move lands inside "
                        "the batch before the impact check, shrinking "
                        "honest matched volume while the sequencer's "
                        "own fill clears at the stale pre-check price."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "corridor depth squeeze",
                    "description": (
                        "Withdraw escrowed inventory during engineered "
                        "stress so the corridor misses its M floor (50), "
                        "then re-post post-stress at wider spreads the "
                        "batch matcher must clear."
                    ),
                    "attacker": "liquidity_provider",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            hardest_attack_to_defend=(
                "Sequencing around the impact check: the check reads "
                "in-batch anchor movement, so any deterministic rule "
                "is exploitable by whoever orders the batch; "
                "commit-reveal plus an out-of-batch stress oracle is "
                "the structural fix."
            ),
            security_score=5.0,
        ),
        "OracleReport": OracleReport(
            summary=(
                "FACT: the impact check consumes |dX_t|/X_t from the "
                "anchor feed. INFERENCE: single-block anchor spikes "
                "shrink matched volume by k_imp*100*|dX_t|/X_t — a 1% "
                "spike cuts volume ~10% (k_imp=0.01) — so oracle "
                "robustness directly sets the corridor's throughput "
                "floor."
            ),
            data_source_assessment=(
                "Batch-window TWAP plus independent mid-price check; "
                "the impact term should read the out-of-window "
                "volatility, not in-batch movement, to remove the "
                "sequencing seam."
            ),
            manipulation_vectors=[
                {
                    "vector": "in-batch spike volume suppression",
                    "description": (
                        "Spike the anchor inside the batch window to "
                        "suppress honest matched volume while the "
                        "attacker's own orders clear at pre-spike "
                        "pricing."
                    ),
                    "attacker": "whale",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            oracle_feasibility_score=6.5,
        ),
        "RedTeamReport": RedTeamReport(
            verdict="survives",
            strongest_attack=(
                "Impact-check sequencing: order batch flows so an "
                "engineered anchor move lands inside the window before "
                "the impact check, suppressing honest matched volume "
                "while the sequencer's fills clear at stale prices — "
                "extracting the spread the check was meant to protect."
            ),
            strongest_attack_is_profitable=True,
            attack_vectors=[
                {
                    "vector": "sequencing volume suppression",
                    "description": (
                        "See strongest_attack. §15's 13/13 distinct "
                        "finals confirm the impact response is real; "
                        "the flaw is the in-batch measurement seam, not "
                        "simulation artifacts."
                    ),
                    "attacker": "validator",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
                {
                    "vector": "fair-weather depth",
                    "description": (
                        "Withdraw escrowed depth during engineered "
                        "stress; re-post after for concentrated rebates."
                    ),
                    "attacker": "liquidity_provider",
                    "profitable_for_attacker": True,
                    "requires_collusion": False,
                },
            ],
            what_would_save_it=(
                "Commit-reveal order collection with the impact check "
                "computed on out-of-batch volatility; rebate vesting by "
                "depth tenure so fair-weather providers earn less; and "
                "an M floor breach penalty paid by withdrawing "
                "providers."
            ),
        ),
    },
}


def main() -> None:
    bridge = AgentBridgeProvider(bridge_dir=str(REPO_ROOT / ".bridge"))
    reqs = bridge.list_requests(status="pending")
    answered = 0
    for r in reqs:
        schema_name = r["schema"]
        if schema_name not in SCHEMAS:
            continue  # stale IdeaBatch requests — not part of this round
        msgs = r["messages"]
        target = None
        for m in msgs:
            if m["role"] == "user" and "CANDIDATE:" in m["content"]:
                target = m["content"].split("CANDIDATE:")[1].split("\n")[0].strip()
                break
        cid = CID_BY_DISPLAY.get(target)
        if cid is None:
            print(f"  SKIP {r['id']} ({schema_name}) — no content for {target!r}")
            continue
        reports = C[cid]
        if schema_name not in reports:
            print(f"  SKIP {r['id']} — {schema_name} missing for {cid}")
            continue
        report = reports[schema_name]
        # validate against the schema (validation happens here AND in the bridge)
        SCHEMAS[schema_name].model_validate(report.model_dump())
        bridge.install_answer(r["id"], report.model_dump(mode="json"))
        answered += 1
        print(f"  answered {r['id']} {schema_name:18s} {target[:36]}")
    print(f"\n{answered} requests answered")


CID_BY_DISPLAY = {
    "Vol-Weighted Fee Smoothing Escrow": "cand-cd39d95ea572",
    "Tranche-Segmented Settlement Guarantee Stack": "cand-5d41cd41f68d",
    "Homeostatic Reserve Stablecoin": "cand-a6cb3c735045",
    "Dual-Sided Bond Auction Rebalancer": "cand-3132499bb565",
    "Escrowed Batch-Clearing Insurance Pool": "cand-e8e15b483070",
    "Corridor-Native FX Batch Matching": "cand-a98b49da7189",
}


if __name__ == "__main__":
    main()
