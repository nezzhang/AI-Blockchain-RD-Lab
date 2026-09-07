"""Bridge answers: red-team reports for the 14 r8 combination candidates.

Authored as genuine adversarial research per §9 (DESTROY THE IDEA) —
each report references the model's actual equations (v1 forms stored
per candidate). Verdicts are honest: several candidates carry real
profitable attacks (vulnerable), a few survive with bounded residuals.
§20 gate discipline: fatal only when the strongest attack is also
profitable and unfixable.
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

# ---------------------------------------------------------------------------
# Per-candidate adversarial analysis. Attacks must be *about the actual
# mechanism equations* — these models all react to |dX_t|/X_t and X_t
# level terms, so the recurring attack families are:
#   - statistic gaming (manufacture the vol/level signal)
#   - funding extraction (draw pools in calm regimes then trigger)
#   - saturation/corridor attacks at clip bounds
# Each candidate gets 4 reports (game theory, security, oracle, red team)
# with candidate-specific vectors named distinctly.
# ---------------------------------------------------------------------------

A: dict[str, dict[str, dict]] = {
    "Fee-Spike Mutual for Rollup Batches": {
        "game_theory": dict(
            summary="Members pay premiums proportional to spike intensity "
            "s_t = sqrt(max(0, |dX|/X - band)). A colluding majority of "
            "batch posters can suppress reported fee spikes below the band "
            "while quietly settling off-protocol, keeping premiums at "
            "minimum while extracting reserve capacity in a final coordinated "
            "spike window.",
            attack_vectors=[
                dict(
                    vector="calm-band suppression then spike harvest",
                    description="Colluders report/induce calm windows to "
                    "keep s_t = 0 (premiums minimal, reserve accumulating), "
                    "then coordinate simultaneous batch posting to blow "
                    "through the band once and reimburse off the accumulated "
                    "reserve in one window.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The mutual's premium P_t1 mean-reverts around "
            "1000 with 0.05*(X-1000) level drift; a level-pumping whale "
            "raises everyone's premiums but only marginally (0.05*X per "
            "step is small vs. the 8*s_t term) — level manipulation is not "
            "the cheap attack here.",
            death_spiral_risk=4.0,
            game_theory_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The reserve R_t accrues mu=20/step in calm and pays "
            "kappa*s_t*P_t1/40 on spikes. Attack surface: the fee-statistics "
            "oracle that defines the band. A compromised fee feed that "
            "reports calm indefinitely drains nothing but starves payouts "
            "when real spikes hit — members find the reserve structurally "
            "short exactly when they need it.",
            attack_vectors=[
                dict(
                    vector="fee-feed understatement to starve payouts",
                    description="A captured fee oracle reports sub-band "
                    "levels during a genuine congestion event; s_t reads 0, "
                    "no reimbursement accrues, members bear full spike cost "
                    "while premiums were collected throughout.",
                    attacker="oracle_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="fee-feed understatement — the entire "
            "payout path depends on one statistic the insurer doesn't "
            "produce itself",
            security_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="The model consumes X_t/dX_t as a fee-market proxy — "
            "in production this is an attested batch-fee series. Median-of-"
            "quorum attestation is assumed; single-feed capture flips both "
            "the premium pricing and the payout trigger.",
            data_source_assessment="Attested per-window fee levels from "
            "rollup sequencers; the r7-corrected model treats realized "
            "relative volatility as the fee proxy, which is defensible for "
            "the battery but needs fee-level data in production.",
            manipulation_vectors=[
                dict(
                    vector="sequencer fee-report capture",
                    description="The sequencer (or a dominant attester) "
                    "tilts reported fee levels to keep s_t below band "
                    "during their own congestion-driven extraction.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="calm-band suppression then spike harvest: "
            "colluding batch posters minimize premiums across calm windows "
            "(s_t=0, reserve grows +20/step) then trigger one coordinated "
            "spike window to reimburse off accumulated reserve — the mutual "
            "monetizes patience for the attackers",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="calm-band suppression then spike harvest",
                    description="Multi-window premium minimization followed "
                    "by a single coordinated band blow-through harvests the "
                    "reserve accumulated by honest members' premiums.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="reserve drawdown caps per member per window "
            "(rationing) and premium loading for correlated-exposure "
            "clusters, so a coordinated cohort cannot harvest more than "
            "its own contribution",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Drawdown-Underwritten Liquidity Corridor": {
        "game_theory": dict(
            summary="Underwriter capacity U_t tracks 1000 + min(600, "
            "0.04*(X-1000)) - 2*D_t1. The drawdown D is an EWMA of "
            "sqrt(|dX|/X)*900 — a whale can pump the corridor level X up "
            "(raising U toward 1600) and then crash it in a sustained "
            "sequence to pin D at its 900 cap, forcing conversion of the "
            "entire underwriter tranche at the pre-agreed conversion price.",
            attack_vectors=[
                dict(
                    vector="pump-then-drown drawdown conversion",
                    description="Whale pumps X to inflate U (more capacity "
                    "to harvest), then executes a sustained crash sequence "
                    "that pins D_t1 at 900 and forces maximum conversion at "
                    "the pre-agreed price, capturing the spread between "
                    "market depth value and conversion price.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The 0.1 EWMA on U smooths conversion so the "
            "attack takes ~10 steps of sustained drawdown — expensive but "
            "the payout (full tranche conversion) can exceed the cost of "
            "moving the market if corridor depth is thin.",
            death_spiral_risk=6.0,
            game_theory_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The conversion price is static in the model — the "
            "hardest surface. Any static conversion price becomes a "
            "one-touch barrier option for a determined whale once corridor "
            "depth x conversion discount exceeds crash cost.",
            attack_vectors=[
                dict(
                    vector="conversion-price barrier sniping",
                    description="Repeatedly pushing the corridor to the "
                    "conversion band edge and harvesting conversions "
                    "whenever realized depth exceeds the static conversion "
                    "price's fair value.",
                    attacker="arbitrageur",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="static conversion price vs. moving "
            "realized depth value",
            security_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Corridor drawdown statistics come from the venue's own "
            "depth feed — self-referential data. A venue insider with "
            "depth-report influence can shape D directly.",
            data_source_assessment="Realized corridor depth series; "
            "internally produced, so venue governance is the trust root.",
            manipulation_vectors=[
                dict(
                    vector="depth-report shading",
                    description="Understating realized depth keeps D low "
                    "(no conversion), overstating it triggers conversions "
                    "on demand — either direction extracts value from "
                    "underwriters.",
                    attacker="governance",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="pump-then-drown drawdown conversion: inflate "
            "underwriter capacity by pumping the corridor level, then pin "
            "drawdown at its cap to force full tranche conversion at the "
            "static pre-agreed price — the whale buys a one-touch barrier "
            "payoff the tranche funds",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="pump-then-drown drawdown conversion",
                    description="Two-phase whale attack harvesting the "
                    "conversion tranche at a static price.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="depth-report shading",
                    description="Venue-side depth manipulation steering "
                    "conversion timing.",
                    attacker="governance",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="conversion price re-marked each window from "
            "the same drawdown series (dynamic barrier), plus per-window "
            "conversion volume caps",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Counter-Cyclical Fee Sink Insurer": {
        "game_theory": dict(
            summary="The sink K accumulates via 0.05*(1000 + 6*(1200-V)/10 "
            "+ min(200, 0.01*(X-1000))) and disburses when V > 1000. A "
            "governance whale can sustain artificial calm (keep V below "
            "1000) to starve the sink, then trigger turbulence to draw "
            "disbursements at the capped 0.05 rate — extracting bounded "
            "value per step.",
            attack_vectors=[
                dict(
                    vector="calm-starve then turbulence-draw cycling",
                    description="Alternate induced calm (sink accumulates "
                    "slowly) with induced turbulence (disbursements flow "
                    "to fee-capped senders the attacker controls via small-"
                    "sender positioning).",
                    attacker="governance_participant",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="V is an EWMA with alpha=0.15 of sqrt(v)*3500 "
            "— regime manipulation costs sustained market moving, and the "
            "min(200, ...) level cap bounds the level-harvest to 200 units; "
            "the attack is mostly value-neutral for the attacker.",
            death_spiral_risk=3.0,
            game_theory_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Disbursement targets 'small senders' — the identity "
            "boundary is the attack surface. Sybil small-sender farms can "
            "capture disbursements meant for organic retail if 'small' is "
            "defined by per-address volume alone.",
            attack_vectors=[
                dict(
                    vector="sybil small-sender farm",
                    description="Split a whale's flow across many addresses "
                    "each below the small-sender threshold; each farmed "
                    "address receives capped effective-fee support funded "
                    "by the sink.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="per-address small-sender definitions "
            "vs. sybil splitting",
            security_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Regime detection uses realized fee volatility from the "
            "chain's own fee statistics — public, tamper-resistant at "
            "moderate cost, but a sequencer can shape fee volatility "
            "directly through their own transaction inclusion policy.",
            data_source_assessment="On-chain realized fee series; "
            "manipulation requires sequencer-level transaction ordering "
            "power, which is realistic for a dominant sequencer.",
            manipulation_vectors=[
                dict(
                    vector="sequencer fee-volatility shaping",
                    description="Inclusion-policy manipulation to hold "
                    "realized fee volatility below the median, keeping the "
                    "sink in accumulation mode while extracting in "
                    "priority-fee side channels.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="sybil small-sender farm: split whale flow "
            "across farmed addresses below the small-sender threshold to "
            "capture effective-fee support meant for organic retail — the "
            "disbursement design monetizes identity gaming",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="sybil small-sender farm",
                    description="Per-address threshold definitions are "
                    "sybil-farmable; bounded per address but unbounded in "
                    "aggregate.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="per-entity (not per-address) qualification "
            "with proof-of-personhood or history-weighted sender scoring, "
            "plus aggregate per-epoch disbursement caps",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Relay Congestion Cover Mesh": {
        "game_theory": dict(
            summary="C_t1 = EWMA of 1000 + beta*sqrt(|dX|/X)*400. Mesh "
            "payouts flow when C > 1000. A relay operator can fabricate "
            "congestion (or induce it through selective route degradation) "
            "to draw burst compensation funded by mesh fees.",
            attack_vectors=[
                dict(
                    vector="fabricated congestion compensation farming",
                    description="Operators over-report congestion (with "
                    "sybil client attestations) to sustain C above 1000 and "
                    "draw pay*max(0, C-1000)/20 per step from the mesh "
                    "pool.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Staking decay on discrepancy deters solo "
            "fabrication, but the decay rate (implicit) vs. payout rate "
            "(pay=120) determines farm viability; the mesh pool also "
            "mean-reverts to 1000, bounding total extractable value per "
            "epoch.",
            death_spiral_risk=3.5,
            game_theory_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Client-side attestation is the anti-sybil core. "
            "Without device diversity requirements, a large operator "
            "fabricates both the operator report and corroborating client "
            "measurements.",
            attack_vectors=[
                dict(
                    vector="dual-side attestation forgery",
                    description="Operator runs sybil clients that attest "
                    "to fabricated congestion, satisfying the client-"
                    "corroboration check while farming compensation.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="forged client-side attestation at "
            "scale by the party that controls the served routes",
            security_score=4.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Congestion attestation aggregates operator + client "
            "measurements — the classic two-source problem where one "
            "party controls both source populations.",
            data_source_assessment="Route-level measurements; the "
            "defensible design requires independent probe networks whose "
            "economics the mesh doesn't currently fund.",
            manipulation_vectors=[
                dict(
                    vector="probe-network absence exploitation",
                    description="No funded independent probe layer exists; "
                    "congestion statistics default to interested-party "
                    "reports.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=4.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="dual-side attestation forgery: the operator "
            "controls both the route and the attesting client population, "
            "so 'client-corroborated' congestion is self-corroboration — "
            "compensation farming is bounded only by the mesh pool's "
            "mean reversion",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="dual-side attestation forgery",
                    description="Self-corroborating congestion reports "
                    "farm burst compensation.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="an independently funded probe network with "
            "staked diversity requirements, plus compensation bounded by "
            "independently measured throughput deltas",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Volatility-Sized Settlement Escrow": {
        "game_theory": dict(
            summary="Tranche T_t1 = 900*(1 + 150*sqrt(v)/100) responds to "
            "volatility. A whale manufacturing volatility on the pair "
            "raises required cover AND the spread W simultaneously — the "
            "attacker pays the wider spread but collects on any default "
            "they can induce inside the settlement window.",
            attack_vectors=[
                dict(
                    vector="volatility-manufactured default straddle",
                    description="Whale induces pair volatility (raising "
                    "tranche requirements and spread), then engineers a "
                    "counterparty default inside the window to capture the "
                    "cover tranche at its volatility-inflated size.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="T is a direct function of current-step "
            "volatility (no memory), so the attack only needs a single-"
            "window vol burst timed with the default — cheap relative to "
            "the payout at inflated tranche size.",
            death_spiral_risk=5.0,
            game_theory_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The default-completion leg is a one-shot payout with "
            "no verification depth — a colluded fake default (counterparty "
            "agrees to 'fail') converts the tranche to attacker funds.",
            attack_vectors=[
                dict(
                    vector="colluded fake default",
                    description="Both escrow legs controlled by the "
                    "attacker: one side 'defaults', the cover tranche "
                    "completes the settlement to the attacker's own "
                    "counterparty at the volatility-inflated size.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="distinguishing engineered defaults "
            "from organic ones when both legs share a beneficial owner",
            security_score=4.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Pair volatility from oracle-reported price series — "
            "standard oracle surface, but the tranche sizes off single-"
            "window vol, so a single manipulated print inflates required "
            "cover.",
            data_source_assessment="Realized pair-price series from "
            "oracles; window-based vol is noisy and manipulable at the "
            "margin.",
            manipulation_vectors=[
                dict(
                    vector="single-print vol inflation",
                    description="One manipulated price print inside the "
                    "vol window inflates sqrt(v) and with it the tranche "
                    "size an attacker's fake default can capture.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="colluded fake default at volatility-inflated "
            "tranche size: control both settlement legs, manufacture a vol "
            "burst to size the cover up, then 'default' one leg and capture "
            "the tranche — the cover pays the attacker's own counterparty",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="colluded fake default",
                    description="Two-leg control converts the cover into a "
                    "self-payment.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="single-print vol inflation",
                    description="Oracle print manipulation to inflate the "
                    "payout tranche.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="beneficial-ownership checks on both escrow "
            "legs, EWMA (not single-window) tranche sizing, and default "
            "verification with a challenge window",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Forecast-Indexed Fee Smoothing Pool": {
        "game_theory": dict(
            summary="Buffer B pre-funds when implied probability q > 0.3. "
            "A belief whale pushes q up (cheap in a thin book), the pool "
            "injects intensity keyed to the inflated belief, and the "
            "whale's own transactions capture the smoothed fees.",
            attack_vectors=[
                dict(
                    vector="belief-whale buffer farming",
                    description="Push the forecast book's implied "
                    "probability above neutral, causing the buffer to "
                    "inject smoothing exactly when the attacker's own "
                    "high-fee transactions execute.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="q is bounded [0.05, 0.95] and the buffer "
            "drains only 5% below neutral, so the farm is bounded per "
            "window; but the injection rate (30 per belief unit) is "
            "harvestable repeatedly.",
            death_spiral_risk=3.0,
            game_theory_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The forecast book needs per-address position caps — "
            "the model doesn't encode them. Without caps, one wallet "
            "becomes the implied probability.",
            attack_vectors=[
                dict(
                    vector="uncapped position dominance",
                    description="A single forecast position large enough "
                    "to set q unilaterally makes the smoothing intensity "
                    "attacker-controlled.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="forecast-market microstructure — "
            "position caps vs. whale sub-division",
            security_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Resolution from on-chain fee statistics — the same "
            "honest surface as the fee sink. The forward-looking signal "
            "lives in the book, not oracles.",
            data_source_assessment="Realized fee percentiles from chain "
            "data; book quotes are venue-internal.",
            manipulation_vectors=[
                dict(
                    vector="book-quote flash manipulation",
                    description="Momentary book quotes that set q during "
                    "the epoch-snapshot window without holding risk "
                    "overnight.",
                    attacker="arbitrageur",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="belief-whale buffer farming: uncapped "
            "forecast positions let one wallet set the implied congestion "
            "probability, steering buffer injections toward their own "
            "fee-paying transactions",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="belief-whale buffer farming",
                    description="See analysis; bounded per window but "
                    "repeatable every epoch.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="per-address position caps on the forecast "
            "book, TWAP-style implied-probability snapshots (not point-in-"
            "time), and injection proportional to realized (not implied) "
            "congestion",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Prediction-Settled Hashprice Hedge Board": {
        "game_theory": dict(
            summary="Hedge exposure H tracks 1000 + drift*100*sqrt(v); "
            "margin G marks to floor + xi*sqrt(v) + |dH|. A supplier cartel "
            "inflating the settlement median collects on short hedges "
            "while their own revenue rises — double-dipping.",
            attack_vectors=[
                dict(
                    vector="supplier-median inflation double dip",
                    description="Cartel over-reports realized compute "
                    "prices: the settlement index rises (their shorts pay "
                    "off) AND their actual compute revenue rises with "
                    "market prices they've moved.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Median-of-supplier settlement blunts minority "
            "capture; a majority cartel breaks it, but a majority cartel "
            "in a competitive supply market is economically self-defeating "
            "(they suppress their own margins).",
            death_spiral_risk=4.0,
            game_theory_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Margin marking G_t1 = clip(floor + 900*sqrt(v) + "
            "|H_t1-H_t|) — an attacker manufacturing volatility inflates "
            "required margin on competitors while their own hedge collects.",
            attack_vectors=[
                dict(
                    vector="margin-squeeze volatility manufacture",
                    description="Manufactured reference volatility raises "
                    "all traders' margin requirements, forcing leveraged "
                    "competitors out while the attacker's positioned "
                    "hedge accrues value.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="volatility of the settlement "
            "reference is attacker-influenceable while margin marks to it",
            security_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Median-of-supplier realized prices as settlement "
            "reference — inherits oracle slashing discipline only if "
            "reporter bonds exist (the model doesn't encode them).",
            data_source_assessment="Supplier-reported prices with median "
            "aggregation; no bond/slash layer in the current model.",
            manipulation_vectors=[
                dict(
                    vector="unbonded reporter tilting",
                    description="Without reporter bonds, a minority of "
                    "high-report suppliers shifts the median upward "
                    "persistently at zero cost.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="supplier-median inflation double dip: a "
            "majority cartel over-reports compute prices to collect on "
            "short hedges while raising their own market revenue — but "
            "the majority requirement in a competitive supply market makes "
            "this self-defeating and margin-marked positions bound the "
            "extraction",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="supplier-median inflation double dip",
                    description="Requires a majority cartel; cost of "
                    "sustaining it exceeds hedge payouts in competitive "
                    "supply.",
                    attacker="validator",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="unbonded reporter tilting",
                    description="Minority tilting is bounded by median "
                    "aggregation but should carry bonds.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="reporter bonds slashed on median deviation "
            "(inherited from oracle-design discipline) would close the "
            "minority-tilting residual",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Consensus-Odds Liquidity Rebate": {
        "game_theory": dict(
            summary="Rebate multiplier r_t1 = 1 + 2.5*(q-0.4). A whale "
            "pushing q up earns multiplied rebates on their own quoted "
            "depth — the venue pays the attacker to manufacture demand "
            "forecasts.",
            attack_vectors=[
                dict(
                    vector="self-dealing forecast rebate farming",
                    description="Whale holds forecast positions pushing q "
                    "above neutral while quoting deep maker depth; "
                    "rebates multiplied by their own manufactured belief "
                    "flow back to them.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="Rebate qualification requires depth "
            "persistence through the window — genuine capital at risk — "
            "which bounds the farm to the rebate share of the fee pool "
            "per epoch; the attack is profitable but bounded.",
            death_spiral_risk=2.5,
            game_theory_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The venue's fee-revenue share funding rebates is "
            "honest; the security surface is forecast position caps and "
            "wash-quote detection (self-trading depth).",
            attack_vectors=[
                dict(
                    vector="wash-quote depth inflation",
                    description="Self-traded depth satisfies persistence "
                    "checks while carrying no real market-making risk.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="wash-quote persistence at the "
            "multiplied rebate tiers",
            security_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Volume-forecast resolution from published venue "
            "volume — self-referential but auditable.",
            data_source_assessment="Venue-published per-window volume; "
            "public and replayable.",
            manipulation_vectors=[
                dict(
                    vector="volume wash to move the forecast strike",
                    description="Wash volume near the forecast threshold "
                    "flips the resolution bucket to collect forecast "
                    "payouts while wash costs are near zero on "
                    "self-matched orders.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="self-dealing forecast rebate farming: "
            "manufacture the volume belief with forecast positions, quote "
            "depth through the same windows, collect multiplied rebates "
            "funded by the losing side of your own manufactured forecast",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="self-dealing forecast rebate farming",
                    description="Bounded per epoch but structurally "
                    "profitable absent wash detection.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="wash-quote depth inflation",
                    description="Wash quotes satisfy persistence "
                    "requirements risk-free.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="wash-trade detection gating rebate "
            "qualification, per-address forecast caps, and rebates "
            "denominated only in realized (not forecast) taker flow",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Adverse-Selection Taxed Prediction Clearing": {
        "game_theory": dict(
            summary="Imbalance I_t1 tracks 1000 + 5000*dX/X; aggressor "
            "spread widens with |I-1000|. A wash-flow attacker can "
            "oscillate flow to keep I far from 1000, widening spreads on "
            "everyone while farming the balanced-flow rebate pool with "
            "two-sided wash flow.",
            attack_vectors=[
                dict(
                    vector="wash-oscillation rebate farming",
                    description="Alternate one-sided wash bursts (widening "
                    "aggressor spreads for real traders, funding the "
                    "rebate pool) with perfectly balanced wash flow that "
                    "qualifies for the rebates.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The rebate pool Pb mean-reverts to 1000 + "
            "0.6*(A-1000)*4 — the attacker funds their own rebate via "
            "their own widened spread payments only partially; the "
            "imbalance EMA (lambda=0.25) gives genuine two-sided flow "
            "cheap qualification. The design prices the attack correctly "
            "but doesn't eliminate it.",
            death_spiral_risk=3.0,
            game_theory_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Settlement by time-weighted mid bounds last-trade "
            "manipulation — the strongest single design choice here. "
            "Remaining surface: persistence requirements for balanced-"
            "flow qualification.",
            attack_vectors=[
                dict(
                    vector="persistence-gaming balanced flow",
                    description="Deterministically timed two-sided wash "
                    "flow satisfies naive persistence windows while "
                    "carrying no information-repair value.",
                    attacker="arbitrageur",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="distinguishing depth-repairing flow "
            "from choreographed two-sided wash",
            security_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Reference resolution by venue-internal time-weighted "
            "mid — no external oracle, honest and auditable.",
            data_source_assessment="Venue-internal price series; "
            "manipulation requires sustained market moving, not report "
            "capture.",
            manipulation_vectors=[
                dict(
                    vector="TWAP-window boundary gaming",
                    description="Positioning flow just outside the "
                    "time-weighted window so the mid excludes the "
                    "attacker's own price impact.",
                    attacker="arbitrageur",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=7.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="wash-oscillation rebate farming: one-sided "
            "wash bursts widen aggressor spreads and fund the rebate pool, "
            "then balanced wash flow qualifies for those rebates — the "
            "venue's anti-adverse-selection mechanism becomes a wash-"
            "flow subsidy absent choreography detection",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="wash-oscillation rebate farming",
                    description="See game-theory analysis; structurally "
                    "profitable bounded by the pool per epoch.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="persistence-gaming balanced flow",
                    description="Choreographed persistence windows "
                    "qualify risk-free.",
                    attacker="arbitrageur",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="flow-pattern classifiers (deterministic) "
            "for rebate qualification, and rebates proportional to "
            "measured post-trade depth repair rather than balance alone",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Belief-Weighted Volatility Target Fund": {
        "game_theory": dict(
            summary="Exposure de-risks as blended risk V rises. A whale "
            "manufacturing belief-market stress prices drives the fund's "
            "de-risking (selling pressure the whale front-runs).",
            attack_vectors=[
                dict(
                    vector="belief-driven de-risking front-run",
                    description="Push the implied-stress component of V "
                    "up, front-run the fund's deterministic de-risking "
                    "sales, buy back at the induced discount.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The 0.12 EWMA on exposure makes de-risking "
            "gradual (predictable), which is precisely what makes it "
            "front-runnable. A no-hysteresis linear rule is the weakness.",
            death_spiral_risk=4.0,
            game_theory_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The fund's exposure rule is public and deterministic "
            "— transparency becomes the attack surface (MEV on rebalance "
            "windows).",
            attack_vectors=[
                dict(
                    vector="rebalance-window MEV extraction",
                    description="Deterministic rebalancing epochs are "
                    "sandwich-attack windows on the fund's own trades.",
                    attacker="arbitrageur",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="predictable deterministic "
            "rebalancing in adversarial execution environments",
            security_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Blended risk uses realized vol (chain data) + "
            "implied stress (belief market) — the belief component is "
            "the manipulable one.",
            data_source_assessment="Realized vol honest; implied stress "
            "from an unbounded belief book.",
            manipulation_vectors=[
                dict(
                    vector="belief-book stress spoofing",
                    description="Thin belief-book positions spike the "
                    "implied-stress input, steering exposure rules.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="belief-driven de-risking front-run: "
            "manufacture stress beliefs, front-run the fund's predictable "
            "EWMA de-risking, harvest the induced discount — the fund's "
            "deterministic transparency is the attack surface",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="belief-driven de-risking front-run",
                    description="Predictable rule + belief manipulation = "
                    "MEV harvest.",
                    attacker="whale",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="rebalance-window MEV extraction",
                    description="Sandwich windows on rebalances.",
                    attacker="arbitrageur",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="hysteresis bands on exposure changes, "
            "randomized rebalance timing, belief-book position caps, and "
            "execution via TWAP/participation-of-volume rather than "
            "discrete epochs",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Disagreement-Weighted Oracle Quorum": {
        "game_theory": dict(
            summary="Reporters stake on their own median deviation; "
            "weights re-derive from calibration. A sandbagger deliberately "
            "reports slightly-deviant values while staking 'I will deviate' "
            "— collecting the disagreement reward for correctly "
            "predicting their own deviation while keeping influence "
            "marginally reduced.",
            attack_vectors=[
                dict(
                    vector="calibration sandbagging",
                    description="Report deviant values with matching "
                    "deviation stakes: the stake pays out (self-predicted "
                    "deviation), the weight penalty is small, and the "
                    "median tilts persistently.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The weight responds to sqrt(|median - "
            "anchor|) — a small persistent tilt costs little weight while "
            "deviation stakes pay per interval. The equilibrium favors "
            "sustained sandbagging over honest reporting.",
            death_spiral_risk=3.5,
            game_theory_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Median EWMA-tracks the anchor with 0.3 correction — "
            "the median itself is attackable by a reporter coalition "
            "moving the EWMA steadily.",
            attack_vectors=[
                dict(
                    vector="slow-median capture",
                    description="A patient coalition tilts the EWMA-"
                    "tracked median at 0.3-rate per step, staying below "
                    "single-interval deviation thresholds while the "
                    "published rate drifts.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="slow persistent median drift below "
            "per-interval thresholds",
            security_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="This IS the oracle design — self-staking quorum. "
            "The core innovation (deviation-priced influence) has a "
            "sandbagging hole the model doesn't close.",
            data_source_assessment="Reporter reports + anchor series; "
            "incentives well-specified except sandbagging.",
            manipulation_vectors=[
                dict(
                    vector="calibration sandbagging",
                    description="See game-theory analysis — the deviation "
                    "market pays for self-predicted deviation.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="calibration sandbagging: reporters stake "
            "on their own deviation, deliberately deviate, collect the "
            "disagreement payout, and keep most of their weight — the "
            "mechanism pays for the very corruption it prices",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="calibration sandbagging",
                    description="Self-predicted deviation farming.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="slow-median capture",
                    description="Coalition EWMA drift below thresholds.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="directional accuracy weighting (deviation "
            "toward the anchor rewards, away punishes) and stake payouts "
            "only for deviations the reporter did NOT predict",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Prediction-Fee Fallback Oracle": {
        "game_theory": dict(
            summary="The fee ladder F climbs when book open interest O "
            "thins below 600; O mean-reverts to floor + 150*sqrt(v) + "
            "min(400, level term). A griefer withdrawing book liquidity "
            "forces fallback-mode fees on all senders — paid by users, "
            "not the griefer.",
            attack_vectors=[
                dict(
                    vector="book-thinning fallback griefing",
                    description="Pull prediction-book liquidity to thin "
                    "O below the floor, forcing the fee ladder up for "
                    "every sender while the griefer's own flow waits "
                    "outside the rail.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The griefer pays opportunity cost (foregone "
            "book yield) but externalizes larger fee costs to senders — "
            "a classic negative-externality grief; not directly profitable "
            "for the attacker but value-destructive.",
            death_spiral_risk=4.0,
            game_theory_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="The open-interest floor (150) is the anti-"
            "manipulation core; the attack is sustaining thinness "
            "cheaply. Underwriters of the book earn spread — a thin book "
            "is costly to sustain but a coordinated exit can achieve it.",
            attack_vectors=[
                dict(
                    vector="coordinated book exit attack",
                    description="Multiple LPs coordinate simultaneous "
                    "withdrawal; the floor binds, fees spike, and the "
                    "attackers re-enter to capture elevated fallback fees "
                    "as book owners.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="the ladder's fee revenue funds "
            "sender cover — attackers owning the book AND the fallback "
            "fees harvest both sides",
            security_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Staleness detection requires reporter diversity the "
            "model assumes. The fallback prediction quote with an OI "
            "floor is the strongest rung — manipulation cost scales with "
            "potential damage.",
            data_source_assessment="Primary feed + quorum + OI-floored "
            "book; layered and honest.",
            manipulation_vectors=[
                dict(
                    vector="primary-feed staleness forcing",
                    description="A reporter majority withholds reports to "
                    "force fallback mode and harvest elevated conversion "
                    "fees via book ownership.",
                    attacker="oracle_provider",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="survives",
            strongest_attack="coordinated book exit attack: LPs thin the "
            "book to force fallback fees, then re-enter to capture them "
            "— but the OI floor forces the attackers to hold real "
            "capital at the thin-book prices, and sender cover funded by "
            "the elevated fees compensates the harmed party",
            strongest_attack_is_profitable=False,
            attack_vectors=[
                dict(
                    vector="coordinated book exit attack",
                    description="Requires collusion + capital at risk at "
                    "thin prices; net EV marginal.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=False,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="book-thinning fallback griefing",
                    description="Non-profit grief, externally damaging.",
                    attacker="liquidity_provider",
                    profitable_for_attacker=False,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="fee-ladder revenue routed to sender cover "
            "rather than book owners closes the re-entry harvest",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Report-Bonded Forecast Fee Meter": {
        "game_theory": dict(
            summary="Bonds B forfeit when band error exceeds mis_band; "
            "the stabilization pool compensates caught applications. A "
            "reporter can deliberately mis-band (paying the forfeit) to "
            "direct compensation toward applications they own.",
            attack_vectors=[
                dict(
                    vector="compensation-directed mis-banding",
                    description="Reporter deliberately mis-bands; half "
                    "the forfeit flows to 'caught applications' the "
                    "reporter controls — the forfeit becomes a transfer "
                    "to themselves at 50% efficiency.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The 50/50 forfeit split means self-directed "
            "compensation recovers half the forfeit — unprofitable alone, "
            "but a reporter controlling BOTH the mis-banding and majority "
            "compensated flow converts it into a positive-sum drain.",
            death_spiral_risk=3.0,
            game_theory_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="Compensation qualification (which applications "
            "'were caught above their band') needs deterministic rules "
            "the model doesn't specify — that boundary is the attack.",
            attack_vectors=[
                dict(
                    vector="compensation qualification gaming",
                    description="Applications positioning at band edges "
                    "maximize their 'caught' classification probability, "
                    "farming the stabilization pool.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="adversarial positioning at band "
            "boundaries to qualify for compensation",
            security_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Attested batch-fee reports with banded bonds — the "
            "honest core; band granularity is the practical limit.",
            data_source_assessment="Reporter bonds at banded forecasts; "
            "auditable and slashed.",
            manipulation_vectors=[
                dict(
                    vector="band-edge statistical exploitation",
                    description="Positioning fee exposure exactly at band "
                    "edges maximizes compensation events per unit of "
                    "real risk.",
                    attacker="arbitrageur",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.5,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="compensation-directed mis-banding: a "
            "reporter who also controls the caught applications converts "
            "their own bond forfeit into self-compensation at 50% "
            "efficiency, and band-edge positioning farms the stabilization "
            "pool",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="compensation-directed mis-banding",
                    description="Self-directed compensation converts "
                    "forfeits to transfers.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="compensation qualification gaming",
                    description="Band-edge positioning maximizes caught "
                    "classification.",
                    attacker="attacker",
                    profitable_for_attacker=True,
                    requires_collusion=False,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="compensation proportional to independently "
            "verified fee exposure (not band classification), and "
            "reporter/application beneficial-ownership separation checks",
            evidence_level="HYPOTHESIS",
        ),
    },
    "Attestation-Locked Prediction Settlement": {
        "game_theory": dict(
            summary="Bonds A decay toward 1000 and slash when divergence "
            "exceeds tolerance; slashed value funds market liquidity. A "
            "colluding operator majority controls the median AND the "
            "settlement the median feeds — double capture.",
            attack_vectors=[
                dict(
                    vector="operator-majority settlement capture",
                    description="Majority operators tilt flow attestations "
                    "to settle prediction markets they hold positions in; "
                    "slashing falls on minority dissenters.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            equilibria_notes="The challenge window with bond-backed "
            "disputes is the honest check — but if challenges must come "
                    "from operators (the model's §33 note), the majority "
                    "censors them; external attestations are the fix the "
                    "open questions already name.",
            death_spiral_risk=4.5,
            game_theory_score=5.5,
            evidence_level="HYPOTHESIS",
        ),
        "security": dict(
            summary="40% of slashing funds market liquidity — a clever "
            "incentive alignment, but it means successful manipulation "
            "is partly self-funding (the manipulators' slash funds the "
            "liquidity they trade against).",
            attack_vectors=[
                dict(
                    vector="self-funding manipulation recycling",
                    description="Operators manipulate, get slashed, but "
                    "the slash funds the very market liquidity their "
                    "positions trade in — partial cost recovery.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            hardest_attack_to_defend="slash-recycling when the slashed "
            "value flows back to attacker-adjacent liquidity",
            security_score=5.0,
            evidence_level="HYPOTHESIS",
        ),
        "oracle": dict(
            summary="Median cross-checks + challenge window = solid "
            "layered design; the operator-only challenge admission is "
            "the gap.",
            data_source_assessment="Operator attestations with median "
            "cross-checks; challenge-window disputes.",
            manipulation_vectors=[
                dict(
                    vector="challenge-window censorship",
                    description="Operator-majority admission control "
                    "suppresses external challenges during settlement.",
                    attacker="governance",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            oracle_feasibility_score=6.0,
            evidence_level="HYPOTHESIS",
        ),
        "red_team": dict(
            verdict="vulnerable",
            strongest_attack="operator-majority settlement capture with "
            "challenge-window censorship: a colluding majority tilts "
            "attested flows to settle their own positions, suppresses "
            "challenges through admission control, and recovers part of "
            "the slash via the liquidity funding it feeds",
            strongest_attack_is_profitable=True,
            attack_vectors=[
                dict(
                    vector="operator-majority settlement capture",
                    description="Majority collusion on flow medians "
                    "settles prediction markets adversarially.",
                    attacker="validator",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
                dict(
                    vector="challenge-window censorship",
                    description="Admission control suppresses honest "
                    "challenges.",
                    attacker="governance",
                    profitable_for_attacker=True,
                    requires_collusion=True,
                    evidence_level="HYPOTHESIS",
                ),
            ],
            what_would_save_it="externally admissible challenges with "
            "their own bond class, and slash proceeds routed to "
            "challengers rather than market liquidity",
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
        spec = A[name][SCHEMA_TO_KIND[schema]]
        cls = {
            "GameTheoryReport": GameTheoryReport,
            "SecurityReport": SecurityReport,
            "OracleReport": OracleReport,
            "RedTeamReport": RedTeamReport,
        }[schema]
        payload = cls.model_validate(spec).model_dump()
        bridge.install_answer(d["id"], payload)
        installed += 1
    print(f"installed {installed} red-team answers")


if __name__ == "__main__":
    main()
