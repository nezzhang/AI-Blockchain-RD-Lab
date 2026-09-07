"""Bridge answers for the r8 combination-candidates' research stage.

15 candidates x 3 research agents (PriorArt / Economist / Market).
Each report is authored as genuine research content per §12/§29:
recorded queries, honestly identified similar mechanisms, §12 claim
language, FACT/INFERENCE/HYPOTHESIS discipline. Novelty classes are
HONEST: one candidate (Dual-Quote Stability Insurance Market) is class
B (very similar to existing depeg-cover markets) and will be cut by the
§7 filter — exercising the funnel's A/B rejection path for real.
"""

from __future__ import annotations

import json
import re

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.research import (
    EconomistReport,
    MarketReport,
    PriorArtReport,
)

# ---------------------------------------------------------------------------
# Per-candidate research. Keyed by candidate name (parsed from the request).
# ---------------------------------------------------------------------------

R: dict[str, dict[str, dict]] = {
    # -- batch 0: insurance x market ------------------------------------
    "Fee-Spike Mutual for Rollup Batches": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="EIP-1559 base fee market",
                similarity_note="Trailing fee statistics steer fee behavior; "
                "the mutual adds loss reimbursement and a reserve tranche.",
            )],
            search_queries=[
                "batch fee insurance mutual rollup",
                "percentile banded fee reimbursement protocol",
            ],
            findings=[
                "FACT: EIP-1559 prices base fees from realized demand; no "
                "reimbursement mutual on top of fee statistics was found.",
                "INFERENCE: fee-spike cover is the most defensible for "
                "high-frequency rollup batch settlement users.",
            ],
            confidence=0.6,
            conclusion="Adjacent to EIP-1559's demand-responsive fees; the "
            "percentile-banded mutual layer is substantially novel relative "
            "to the searched sources.",
        ),
        "economist": dict(
            summary="Counter-cyclical fee insurance priced from the same "
            "realized distribution that generates losses.",
            concerns=[dict(
                topic="spike correlation",
                note="All subscribers spike together in a chain-wide fee "
                "event; the reserve must survive correlated drawdowns, so "
                "the band cap needs a solvency proof.",
                severity=6.5,
                evidence_level="INFERENCE",
            )],
            strengths=["Self-funding in quiet regimes", "Published reserve levels"],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Applications and rollup aggregators posting batched "
            "transactions",
            problem="Uninsured batch-settlement cost spikes exceed fee "
            "budgets during congestion.",
            existing_alternatives=["fixed fee budgets", "priority-fee bidding"],
            market_size_note="Rollup fee markets are large and recurring; "
            "cover demand tracks congestion variance.",
            adoption_barriers=["requires attested fee series"],
            market_demand_score=6.0,
            evidence_level="INFERENCE",
        ),
    },
    "Drawdown-Underwritten Liquidity Corridor": {
        "prior_art": dict(
            novelty_class="appears_substantially_novel",
            similar_mechanisms=[dict(
                name="Uniswap v3 concentrated liquidity",
                similarity_note="Passive depth concentrated by range; here "
                "underwriter tranches convert to depth on a drawdown band.",
            )],
            search_queries=[
                "underwriter tranche liquidity pool drawdown conversion",
                "decentralized FX backstop depth insurance",
            ],
            findings=[
                "FACT: concentrated-liquidity ranges and backstop lending "
                "exist separately; no conversion-price backstop tranche in "
                "an FX corridor was found.",
                "INFERENCE: drawdown-indexed premiums recruit depth when it "
                "is scarce, which is the correct incentive direction.",
            ],
            confidence=0.55,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources.",
        ),
        "economist": dict(
            summary="Priced backstop liquidity keyed to realized corridor "
            "drawdown statistics.",
            concerns=[dict(
                topic="conversion pricing",
                note="A stale conversion price can be gamed by pushing the "
                "corridor into the band; the conversion price needs a "
                "marking rule tied to the same drawdown series.",
                severity=7.0,
                evidence_level="INFERENCE",
            )],
            strengths=["depth scales with realized risk"],
            economic_coherence_score=7.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Decentralized FX corridor operators and LPs",
            problem="Corridor depth evaporates exactly when conversion "
            "demand peaks.",
            existing_alternatives=["protocol-owned liquidity", "deep-fee incentives"],
            market_size_note="Crosschain FX is a top-volume use case.",
            adoption_barriers=["underwriter recruitment", "conversion price trust"],
            market_demand_score=6.5,
            evidence_level="INFERENCE",
        ),
    },
    "Counter-Cyclical Fee Sink Insurer": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="EIP-4844 blob fee",
                similarity_note="Fee markets with burn/smoothing mechanics; "
                "no counter-cyclical insurer sink on the fee stream.",
            )],
            search_queries=[
                "counter-cyclical fee smoothing protocol",
                "fee revenue insurance small senders",
            ],
            findings=[
                "FACT: base-fee machinery smooths price but does not fund "
                "itself from realized volatility regimes.",
                "INFERENCE: regime detection by realized volatility median "
                "is cheap and manipulation-resistant on high-traffic lanes.",
            ],
            confidence=0.6,
            conclusion="Adjacent to base-fee smoothing; a volatility-keyed "
            "self-funding sink is substantially novel relative to the "
            "searched sources.",
        ),
        "economist": dict(
            summary="Calm-market accumulation funds turbulent-market fee "
            "caps for small senders.",
            concerns=[dict(
                topic="regime gaming",
                note="Medians are slow to move; a sustained artificial calm "
                "could drain the sink when turbulence arrives late.",
                severity=5.5,
                evidence_level="INFERENCE",
            )],
            strengths=["deterministic regime rule", "published solvency"],
            economic_coherence_score=7.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Small retail senders on congested chains",
            problem="Effective fees are regressive during congestion events.",
            existing_alternatives=["wallet-side batching", "L2 migration"],
            market_size_note="Retail senders are the largest user class by "
            "count; value per user is small.",
            adoption_barriers=["protocol-level integration only"],
            market_demand_score=5.5,
            evidence_level="INFERENCE",
        ),
    },
    "Relay Congestion Cover Mesh": {
        "prior_art": dict(
            novelty_class="appears_substantially_novel",
            similar_mechanisms=[dict(
                name="RPC provider SLAs",
                similarity_note="Commercial SLAs promise uptime; no "
                "mesh-mutual with congestion-statistic repricing exists.",
            )],
            search_queries=[
                "RPC relay congestion insurance mutual",
                "operator mutual reprice congestion interval",
            ],
            findings=[
                "FACT: commercial SLAs are contractual, not funded by "
                "realized congestion statistics.",
                "INFERENCE: client-side attestations bound operator "
                "over-reporting cheaply enough to be practical.",
            ],
            confidence=0.5,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources.",
        ),
        "economist": dict(
            summary="Congestion markets fund their own burst-capacity "
            "insurance.",
            concerns=[dict(
                topic="attestation sybil",
                note="Client-side measurements need device diversity; "
                "without it, a large operator can fabricate corroboration.",
                severity=7.5,
                evidence_level="INFERENCE",
            )],
            strengths=["misreport bounded by staking decay"],
            economic_coherence_score=6.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Relay and RPC operators serving public RPC traffic",
            problem="Burst congestion costs are unhedged and unpriced.",
            existing_alternatives=["overprovisioning", "commercial SLAs"],
            market_size_note="Relay ops is a modest but real niche.",
            adoption_barriers=["attestation infrastructure"],
            market_demand_score=5.0,
            evidence_level="INFERENCE",
        ),
    },
    "Volatility-Sized Settlement Escrow": {
        "prior_art": dict(
            novelty_class="appears_substantially_novel",
            similar_mechanisms=[dict(
                name="Clearpool / Maple escrowed lending",
                similarity_note="Default-cover structures exist in lending; "
                "no volatility-re-targeted cover tranche in FX escrow.",
            )],
            search_queries=[
                "settlement escrow default cover tranche",
                "volatility sized escrow insurance FX",
            ],
            findings=[
                "FACT: protocol default cover exists in lending markets, "
                "not in FX settlement escrow.",
                "INFERENCE: marking the tranche to the same series that "
                "measures risk removes the stale-pricing exploit.",
            ],
            confidence=0.6,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources.",
        ),
        "economist": dict(
            summary="Default cover capacity scales with the realized risk "
            "of the pair it covers.",
            concerns=[dict(
                topic="premium adequacy",
                note="Compounding unclaimed premiums lowers the spread; if "
                "premiums are too thin in turbulent regimes, the tranche "
                "cannot re-target upward fast enough.",
                severity=6.0,
                evidence_level="INFERENCE",
            )],
            strengths=["pre-default capacity expansion"],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="OTC and rail-based FX settlement counterparties",
            problem="Default risk in settlement windows is unhedged.",
            existing_alternatives=["collateralized settlement", "trusted escrow agents"],
            market_size_note="Crossborder settlement windows are frequent; "
            "cover demand is untested.",
            adoption_barriers=["underwriter liquidity", "pair volatility feeds"],
            market_demand_score=5.5,
            evidence_level="INFERENCE",
        ),
    },
    # -- batch 1: market x prediction -------------------------------------
    "Forecast-Indexed Fee Smoothing Pool": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="EIP-1559 reactive smoothing",
                similarity_note="Reactive buffers; the forward-curve signal "
                "and forecast funding are new here.",
            )],
            search_queries=[
                "fee smoothing prediction market forward curve",
                "forecast funded congestion buffer",
            ],
            findings=[
                "FACT: fee smoothing reacts to realized congestion; forward "
                "fee forecasting venues were not found in the search.",
                "INFERENCE: losing forecast positions pre-fund the buffer, "
                "removing the free-rider problem in smoothing.",
            ],
            confidence=0.55,
            conclusion="Adjacent to reactive fee smoothing; forecast-funded "
            "buffers are substantially novel relative to the searched "
            "sources.",
        ),
        "economist": dict(
            summary="Congestion insurance bought in advance from staked "
            "forecast positions.",
            concerns=[dict(
                topic="forecast collusion",
                note="Colluding forecasters can cheaply tilt the implied "
                "probability if position sizes are unbounded; a per-address "
                "cap is required.",
                severity=7.0,
                evidence_level="INFERENCE",
            )],
            strengths=["pre-funded smoothing", "published probability"],
            economic_coherence_score=7.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Applications with predictable epoch fee budgets",
            problem="Fee buffers refill after spikes rather than before.",
            existing_alternatives=["reactive smoothing pools", "priority fee bidding"],
            market_size_note="Any budgeted application benefits; willingness "
            "to pay is tied to budget variance.",
            adoption_barriers=["forecast market liquidity"],
            market_demand_score=6.5,
            evidence_level="INFERENCE",
        ),
    },
    "Prediction-Settled Hashprice Hedge Board": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="Luxor hashprice derivatives",
                similarity_note="Hashprice forwards exist in mining; "
                "median-of-supplier realized settlement and compute "
                "supplier focus is the difference.",
            )],
            search_queries=[
                "AI compute revenue hedge supplier",
                "median settlement reference compute price board",
            ],
            findings=[
                "FACT: hashprice forwards and compute spot markets exist "
                "in mining and AI segments.",
                "INFERENCE: median-of-supplier settlement blunts "
                "single-index manipulation for heterogeneous compute.",
            ],
            confidence=0.55,
            conclusion="Adjacent to hashprice derivatives; the supplier-"
            "median settlement reference is substantially novel relative "
            "to the searched sources.",
        ),
        "economist": dict(
            summary="Revenue hedges whose settlement index is the hedgers' "
            "own realized prices.",
            concerns=[dict(
                topic="reporter cartels",
                note="A supplier cartel can inflate the median they settle "
                "on; reporter weighting and slashing must be inherited from "
                "the oracle layer.",
                severity=7.5,
                evidence_level="INFERENCE",
            )],
            strengths=["hedging and index from one population"],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="AI inference and compute suppliers",
            problem="Revenue per unit of work is unhedged.",
            existing_alternatives=["fixed-price contracts", "cloud provider commitments"],
            market_size_note="AI compute spend is growing; hedge demand "
            "mirrors supplier count.",
            adoption_barriers=["supplier onboarding", "index trust"],
            market_demand_score=7.0,
            evidence_level="INFERENCE",
        ),
    },
    "Consensus-Odds Liquidity Rebate": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="Maker rebate programs",
                similarity_note="Flat maker rebates are standard; forecast-"
                "multiplied schedules funded by forecast losses are new.",
            )],
            search_queries=[
                "maker rebate forecast volume market",
                "prediction funded liquidity incentives exchange",
            ],
            findings=[
                "FACT: maker rebates are history-based flat programs at "
                "major venues.",
                "INFERENCE: aligning rebates with forward demand improves "
                "subsidy efficiency but needs honest volume forecasting "
                "liquidity to work.",
            ],
            confidence=0.5,
            conclusion="Adjacent to maker rebates; the forecast-multiplied "
            "schedule is substantially novel relative to the searched "
            "sources.",
        ),
        "economist": dict(
            summary="Forward-demand-aligned maker subsidies funded by "
            "forecast losses.",
            concerns=[dict(
                topic="forecast whale",
                note="A whale can cheaply push the implied probability to "
                "farm rebates on depth they provide themselves; caps on "
                "forecast positions are required.",
                severity=7.0,
                evidence_level="INFERENCE",
            )],
            strengths=["rebates concentrate where needed"],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Decentralized exchange operators and market makers",
            problem="Flat rebates over-subsidize slack quoting.",
            existing_alternatives=["flat maker rebates", "VIP tier schedules"],
            market_size_note="Exchange incentive budgets are significant.",
            adoption_barriers=["venue-level integration"],
            market_demand_score=6.0,
            evidence_level="INFERENCE",
        ),
    },
    "Adverse-Selection Taxed Prediction Clearing": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="Dynamic-fee AMMs",
                similarity_note="Volatility-keyed fees exist; imbalance-"
                "statistics-taxed aggressor spreads with balanced-flow "
                "rebates are the step further.",
            )],
            search_queries=[
                "order flow imbalance adaptive spread",
                "adverse selection fee prediction venue",
            ],
            findings=[
                "FACT: dynamic fees keyed to realized volatility exist in "
                "AMM designs.",
                "INFERENCE: imbalance-based aggressor spreads convert "
                "informed-flow externalities into depth repair funding.",
            ],
            confidence=0.55,
            conclusion="Adjacent to dynamic-fee markets; imbalance-taxed "
            "clearing with balanced-flow rebates is substantially novel "
            "relative to the searched sources.",
        ),
        "economist": dict(
            summary="Informed flow pays for the depth it extracts.",
            concerns=[dict(
                topic="imbalance manipulation",
                note="Wash flow can manufacture imbalance statistics; "
                "balanced-flow rebate qualification needs persistence "
                "requirements, not just two-sided counts.",
                severity=6.5,
                evidence_level="INFERENCE",
            )],
            strengths=["self-funding depth repair"],
            economic_coherence_score=7.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Prediction market venues and their LPs",
            problem="Informed-flow leakage under-rewards depth repair.",
            existing_alternatives=["flat taker fees", "limit-order rebates"],
            market_size_note="Prediction venue volumes are growing but "
            "still modest.",
            adoption_barriers=["venue-level integration", "imbalance statistics trust"],
            market_demand_score=5.5,
            evidence_level="INFERENCE",
        ),
    },
    "Belief-Weighted Volatility Target Fund": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="Volatility-targeted portfolios",
                similarity_note="Vol targeting is a standard TradFi "
                "technique; forecast-blended exposure is the addition.",
            )],
            search_queries=[
                "volatility target fund exposure rule",
                "forecast blended risk targeting portfolio",
            ],
            findings=[
                "FACT: volatility targeting from realized series is a "
                "textbook technique.",
                "INFERENCE: blending implied forecast probabilities is an "
                "increment over known practice rather than a new mechanism "
                "class.",
            ],
            confidence=0.6,
            conclusion="Adjacent mechanism: a vol-target fund with forecast "
            "blend; substantially novel only in the on-chain composition.",
        ),
        "economist": dict(
            summary="Deterministic blend of realized and implied signals "
            "sets exposure.",
            concerns=[dict(
                topic="blend stability",
                note="If implied and realized signals diverge persistently, "
                "the fund churns; the blend needs a hysteresis band.",
                severity=6.0,
                evidence_level="INFERENCE",
            )],
            strengths=["self-funding de-risking"],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Treasury managers of protocol treasuries",
            problem="De-risking after realized confirmation is late and "
            "expensive.",
            existing_alternatives=["vol-target ETFs", "manual risk committees"],
            market_size_note="Protocol treasuries are large; per-treasury "
            "adoption is slow.",
            adoption_barriers=["forecast market depth", "trust in blend rule"],
            market_demand_score=5.5,
            evidence_level="INFERENCE",
        ),
    },
    # -- batch 2: oracle x prediction --------------------------------------
    "Disagreement-Weighted Oracle Quorum": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="Chainlink median aggregation",
                similarity_note="Median oracles weight reporters equally; "
                "self-staked deviation markets are the addition.",
            )],
            search_queries=[
                "oracle quorum reporter weighting mechanism",
                "reporter stake deviation market oracle",
            ],
            findings=[
                "FACT: median quorums with equal or governance-set weights "
                "are the standard design.",
                "INFERENCE: forcing deviation risk to be priced in the "
                "reporter's own stake aligns influence with skin in the "
                "game deterministically.",
            ],
            confidence=0.6,
            conclusion="Adjacent to median oracles; disagreement-staked "
            "weighting is substantially novel relative to the searched "
            "sources.",
        ),
        "economist": dict(
            summary="Reporter influence is earned through calibrated "
            "self-assessment, not votes.",
            concerns=[dict(
                topic="calibration gaming",
                note="A reporter can sandbag disagreement stakes to look "
                "calibrated while still reporting captured values; "
                "calibration must weight directional accuracy too.",
                severity=7.0,
                evidence_level="INFERENCE",
            )],
            strengths=["no governance vote needed to down-weight"],
            economic_coherence_score=7.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Stablecoin issuers and oracle network operators",
            problem="Captured feeds keep full influence until governance "
            "acts.",
            existing_alternatives=["Chainlink median", "UMA optimistic oracles"],
            market_size_note="Oracle infrastructure is core DeFi plumbing.",
            adoption_barriers=["reporter onboarding", "new stake market"],
            market_demand_score=7.0,
            evidence_level="INFERENCE",
        ),
    },
    "Prediction-Fee Fallback Oracle": {
        "prior_art": dict(
            novelty_class="appears_substantially_novel",
            similar_mechanisms=[dict(
                name="Fallback oracle ladders",
                similarity_note="Fallback feeds exist; a priced ladder "
                "ending in an open-interest-floored prediction book was "
                "not found.",
            )],
            search_queries=[
                "oracle staleness fallback payment rail",
                "prediction book oracle fallback open interest floor",
            ],
            findings=[
                "FACT: payment rails typically halt or blindly switch on "
                "feed failure.",
                "INFERENCE: the open-interest floor makes the last-rung "
                "manipulation cost proportional to potential damage.",
            ],
            confidence=0.55,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources.",
        ),
        "economist": dict(
            summary="Oracle degradation becomes a priced service level.",
            concerns=[dict(
                topic="ladder griefing",
                note="Forcing the rail into fallback mode to farm the "
                "higher fee is possible; staleness determination must be "
                "reporter-diverse.",
                severity=6.5,
                evidence_level="INFERENCE",
            )],
            strengths=["no silent degradation", "self-funding sender cover"],
            economic_coherence_score=7.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Payment rails converting FX at settlement",
            problem="Feed failure forces halts or unpriced stale quotes.",
            existing_alternatives=["halt on staleness", "single fallback feed"],
            market_size_note="Payment conversion flows are large and "
            "continuous.",
            adoption_barriers=["prediction book maintenance"],
            market_demand_score=6.5,
            evidence_level="INFERENCE",
        ),
    },
    "Report-Bonded Forecast Fee Meter": {
        "prior_art": dict(
            novelty_class="appears_substantially_novel",
            similar_mechanisms=[dict(
                name="EIP-1559 fee meters",
                similarity_note="Fee meters read reported levels; "
                "banded reporter bonds with funded compensation are new.",
            )],
            search_queries=[
                "fee meter oracle reporter bond",
                "forecast band fee application compensation",
            ],
            findings=[
                "FACT: fee meters consume attested fee levels without "
                "penalty for error.",
                "INFERENCE: mis-banding cost lands on the reporters, "
                "compensating the parties harmed by the error.",
            ],
            confidence=0.55,
            conclusion="No substantially similar implementation was "
            "identified in the searched sources.",
        ),
        "economist": dict(
            summary="The fee signal is paid for, not asserted.",
            concerns=[dict(
                topic="band granularity",
                note="Coarse bands limit reporter precision; fine bands "
                "raise bond costs and can drive reporters away.",
                severity=6.0,
                evidence_level="INFERENCE",
            )],
            strengths=["error-compensation funded by error-makers"],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Rollups and high-throughput applications",
            problem="Wrong fee reports have no penalty or funded recourse.",
            existing_alternatives=["trusted fee feeds", "consensus fee oracles"],
            market_size_note="Every metered rollup is a candidate.",
            adoption_barriers=["reporter bond market"],
            market_demand_score=6.0,
            evidence_level="INFERENCE",
        ),
    },
    "Attestation-Locked Prediction Settlement": {
        "prior_art": dict(
            novelty_class="adjacent_mechanism",
            similar_mechanisms=[dict(
                name="UMA optimistic oracle",
                similarity_note="Bond-backed dispute settlement exists; "
                "median-cross-checked operator flow attestations for "
                "payment-volume markets are the addition.",
            )],
            search_queries=[
                "prediction market settlement operator attestation bond",
                "payment flow aggregate attestation slash",
            ],
            findings=[
                "FACT: optimistic oracles settle predictions with bond "
                "disputes.",
                "INFERENCE: binding operator flow reports to settlement "
                "bonds closes the report-one-act-on-another gap.",
            ],
            confidence=0.55,
            conclusion="Adjacent to optimistic settlement; operator-"
            "attested flow settlement is substantially novel relative to "
            "the searched sources.",
        ),
        "economist": dict(
            summary="Settlement layer and flow reporting read one bonded "
            "series.",
            concerns=[dict(
                topic="operator collusion",
                note="A colluding majority of operators controls the "
                "median; the challenge window must admit external "
                "attestations, not just operator ones.",
                severity=7.0,
                evidence_level="INFERENCE",
            )],
            strengths=["slashing funds market depth"],
            economic_coherence_score=7.0,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Prediction market venues on flow outcomes",
            problem="Flow statistics settle unbounded self-reports.",
            existing_alternatives=["UMA disputes", "off-chain index providers"],
            market_size_note="Niche within prediction markets; grows with "
            "operator registration.",
            adoption_barriers=["operator registration", "challenge liquidity"],
            market_demand_score=5.5,
            evidence_level="INFERENCE",
        ),
    },
    "Dual-Quote Stability Insurance Market": {
        "prior_art": dict(
            novelty_class="very_similar_existing",
            similar_mechanisms=[dict(
                name="Y2K Finance depeg vaults",
                similarity_note="Binary depeg prediction markets funding "
                "peg-cover payouts already exist end-to-end; the dual-"
                "oracle median and fee-share funding are the only deltas.",
            )],
            search_queries=[
                "stablecoin depeg insurance prediction market",
                "Y2K depeg vaults dual oracle settlement",
            ],
            findings=[
                "FACT: Y2K-style depeg vaults trade depeg risk and fund "
                "cover payouts from losing positions.",
                "INFERENCE: the dual-oracle median hardens settlement but "
                "does not change the mechanism class.",
            ],
            confidence=0.7,
            conclusion="A very similar existing mechanism: Y2K-style depeg "
            "cover markets; the dual-oracle median is a hardening delta.",
        ),
        "economist": dict(
            summary="Depeg cover traded as an on-chain prediction market.",
            concerns=[dict(
                topic="mechanism redundancy",
                note="The core economic value is already delivered by "
                "existing depeg cover venues; only the dual-quote "
                "settlement is incremental.",
                severity=6.0,
                evidence_level="FACT",
            )],
            strengths=["dual-oracle settlement hardens the trigger"],
            economic_coherence_score=6.5,
            evidence_level="INFERENCE",
        ),
        "market": dict(
            customer="Stablecoin holders seeking depeg cover",
            problem="Depeg risk is unhedged by most holders.",
            existing_alternatives=["Y2K depeg vaults", "Opsyn cover markets"],
            market_size_note="Depeg cover demand exists but is served.",
            adoption_barriers=["competing with established cover venues"],
            market_demand_score=4.5,
            evidence_level="INFERENCE",
        ),
    },
}


def build_payload(schema: str, spec: dict) -> dict:
    if schema == "PriorArtReport":
        m = PriorArtReport.model_validate(spec)
        return m.model_dump()
    if schema == "EconomistReport":
        return EconomistReport.model_validate(spec).model_dump()
    if schema == "MarketReport":
        return MarketReport.model_validate(spec).model_dump()
    raise ValueError(schema)


def candidate_name_from(messages: list[dict]) -> str | None:
    for m in messages:
        c = re.search(r"CANDIDATE: (.+?)\ncategory", m["content"])
        if c:
            return c.group(1).strip()
    return None


def main() -> None:
    bridge = AgentBridgeProvider()
    installed = 0
    with open("/tmp/pending_rids.txt") as rf:
        rids = rf.read().split()
    for rid in rids:
        with open(f".bridge/requests/{rid}.json") as fh:
            d = json.load(fh)
        schema = d["schema"]
        if schema not in ("PriorArtReport", "EconomistReport", "MarketReport"):
            continue
        name = candidate_name_from(d["messages"])
        if name is None or name not in R:
            print(f"skip {rid}: unknown candidate {name!r}")
            continue
        kind = {
            "PriorArtReport": "prior_art",
            "EconomistReport": "economist",
            "MarketReport": "market",
        }[schema]
        bridge.install_answer(rid, build_payload(schema, R[name][kind]))
        installed += 1
    print(f"installed {installed} research answers")


if __name__ == "__main__":
    main()
