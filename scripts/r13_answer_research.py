"""Round 13: research answers (PriorArt/Economist/Market x 2 successors).

Honesty (§12): the persistent-regime gate is a three-speed EMA
construction — dual/multi-speed EMA separation is standard TA (MACD is
two-speed); the INSURANCE POLARITY application (protection keyed to a
persistent displacement that refuses to heal while the regime stays
moved) is the novel surface. Class C (adjacent mechanism), stated.

Run: .venv/bin/python scripts/r13_answer_research.py
"""

from __future__ import annotations

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.research import (
    EconomicConcern,
    EconomistReport,
    MarketReport,
    PriorArtReport,
    ResearchSource,
    SimilarMechanism,
)

ORACLE = "Persistent-Trend Prediction-Fee Oracle"
JOULE = "Persistent-Drift Joule Escrow"

PRIOR = {
    ORACLE: PriorArtReport(
        novelty_class="adjacent_mechanism",
        similar_mechanisms=[
            SimilarMechanism(
                name="MACD multi-speed EMA divergence",
                url="https://www.investopedia.com/terms/m/macd.asp",
                similarity_note=(
                    "Multi-speed EMA separation is standard technical "
                    "analysis; here a medium/ultra-slow separation gates "
                    "an insurance premium, not a trading signal"
                ),
            ),
            SimilarMechanism(
                name="Term-structure / regime-shift volatility pricing",
                url="https://www.cmegroup.com/education/",
                similarity_note=(
                    "Markets price tail cover up after regime shifts "
                    "(vol clustering persistence); this is the algorithmic "
                    "counterpart keyed to on-chain level data"
                ),
            ),
            SimilarMechanism(
                name="Dynamic hedging fee models (e.g. option margining)",
                url="https://www.optionsclearing.com/",
                similarity_note=(
                    "Margin/fee schedules reprice on measured regime "
                    "change, typically via discrete bands rather than a "
                    "persistent EMA displacement gate"
                ),
            ),
        ],
        search_queries=[
            "persistent EMA displacement regime gate fee premium",
            "multi-speed EMA separation insurance pricing oracle",
            "crash regime tail cover repricing mechanism",
        ],
        sources=[
            ResearchSource(title="MACD reference",
                           url="https://www.investopedia.com/terms/m/macd.asp",
                           source_type="web"),
            ResearchSource(title="CME education on regime pricing",
                           url="https://www.cmegroup.com/education/",
                           source_type="web"),
            ResearchSource(title="OCC margin methodology",
                           url="https://www.optionsclearing.com/",
                           source_type="intl_org"),
        ],
        findings=[
            "FACT: multi-speed EMA separation (MACD) is a standard "
            "technical-analysis construction.",
            "FACT: volatility clustering (regime persistence) is "
            "empirical market structure; cover repricing after shifts "
            "is standard practice in listed derivatives margining.",
            "INFERENCE: no searched source keys a collateral/fee "
            "premium to persistent medium-vs-ultra-slow EMA displacement "
            "on a price level — the anchored-trend designs in protocol "
            "docs reprice on disputes or band events, not on "
            "regime-persistence gates.",
            "HYPOTHESIS: the insurance polarity (gate must NOT heal "
            "while the regime stays moved) is what distinguishes this "
            "from TA signals, which do decay by design.",
        ],
        confidence=0.7,
        conclusion=(
            "Adjacent mechanism: multi-speed EMA separation is standard "
            "in technical analysis and regime-based repricing is "
            "standard in derivatives margining, but no substantially "
            "similar implementation was identified in the searched "
            "sources."
        ),
    ),
    JOULE: PriorArtReport(
        novelty_class="adjacent_mechanism",
        similar_mechanisms=[
            SimilarMechanism(
                name="MACD multi-speed EMA divergence",
                url="https://www.investopedia.com/terms/m/macd.asp",
                similarity_note=(
                    "Same multi-speed construction; here it gates an "
                    "escrow slash alarm with a ratcheting tolerance"
                ),
            ),
            SimilarMechanism(
                name="Chainlink deviation/threshold alerting",
                url="https://docs.chain.link/",
                similarity_note=(
                    "Off-chain alerting on price deviation exists; "
                    "sustained-regime slash premia on posted escrow do "
                    "not (they fire on discrete threshold events)"
                ),
            ),
            SimilarMechanism(
                name="Performance-bond penalty schedules (construction)",
                url="https://www.fmi.org/",
                similarity_note=(
                    "Penalty bonds escalate on sustained non-delivery; "
                    "the persistent-regime EMA gate is the continuous "
                    "counterpart"
                ),
            ),
        ],
        search_queries=[
            "persistent drift escrow slash alarm regime",
            "energy delivery performance bond sustained default penalty",
            "multi-speed EMA regime gate protocol",
        ],
        sources=[
            ResearchSource(title="MACD reference",
                           url="https://www.investopedia.com/terms/m/macd.asp",
                           source_type="web"),
            ResearchSource(title="Chainlink docs",
                           url="https://docs.chain.link/",
                           source_type="protocol_doc"),
            ResearchSource(title="Performance bond practices",
                           url="https://www.fmi.org/", source_type="web"),
        ],
        findings=[
            "FACT: performance-bond penalty schedules escalate on "
            "sustained non-delivery in construction/energy industries.",
            "FACT: threshold alerting on price deviation exists in "
            "oracle infrastructure (discrete events).",
            "INFERENCE: a sustained-regime slash premium keyed to "
            "persistent EMA displacement was not identified in searched "
            "protocol docs or literature.",
            "HYPOTHESIS: ratcheting tolerance (shrinking with escrow "
            "turnover) plus a persistent gate bounds false-alarm cost "
            "while keeping healed-window default timing unprofitable.",
        ],
        confidence=0.68,
        conclusion=(
            "Adjacent mechanism: performance-bond escalation and "
            "deviation alerting both exist, but no substantially "
            "similar implementation was identified in the searched "
            "sources."
        ),
    ),
}

ECON = {
    ORACLE: EconomistReport(
        summary=(
            "Pricing cover on persistent regime displacement makes the "
            "fee track what tail-risk hedgers actually face: a "
            "crashed-and-parked market pays crash-level fees "
            "indefinitely, smooth growth pays near-base, oscillation "
            "pays nothing beyond the kicker. The ultra-slow anchor "
            "keeps the two EMAs together under smooth growth — no "
            "structural drift premium — while insurance polarity "
            "guarantees the gate stays open while the regime stays "
            "moved."
        ),
        concerns=[
            EconomicConcern(
                topic="regime recovery latency",
                note=(
                    "After a genuine recovery, the medium EMA must "
                    "climb back to the ultra-slow anchor before the "
                    "premium decays — cover buyers overpay during the "
                    "recovery leg; bounded by kappa_l and the 1300x "
                    "gate coefficient."
                ),
                severity=5.5,
            ),
            EconomicConcern(
                topic="anchor drift under sustained growth",
                note=(
                    "Very long growth regimes leave the ultra-slow EMA "
                    "permanently lagging; a slow structural drift "
                    "sustains a small permanent gate premium — an "
                    "honest cost of persistence semantics, bounded by "
                    "kappa_u's ratio to growth rate."
                ),
                severity=4.5,
            ),
        ],
        strengths=[
            "No heal: the measured r13 flaw (cover at 7% of peak while "
            "level stayed -60% moved) is structurally closed — "
            "displacement persists while the regime persists.",
            "No false alarms under smooth growth or wash oscillation "
            "(the two EMAs travel together).",
        ],
        economic_coherence_score=7.4,
    ),
    JOULE: EconomistReport(
        summary=(
            "Keying the slash alarm to persistent regime displacement "
            "restores the escrow's core economic function: defaults "
            "timed to 'healed' windows stay priced, because the alarm "
            "cannot heal while the regime stays moved. Delivery "
            "resumption AT THE NEW LEVEL is what closes the alarm — "
            "the provider's actual obligation is repriced, not "
            "forgiven."
        ),
        concerns=[
            EconomicConcern(
                topic="persistent-alarm overcharge",
                note=(
                    "Providers delivering fine at the new level still "
                    "pay the alarm premium until the medium EMA "
                    "reconverges with the regime anchor; the ratcheting "
                    "tolerance (chi) bounds but does not eliminate this "
                    "— an honest cost of persistence, disclosed."
                ),
                severity=5.0,
            ),
        ],
        strengths=[
            "Healed-window default timing is unprofitable by "
            "construction (alarm persists while displacement does).",
            "Energy price reprices at the new regime rather than "
            "healing — delivery economics stay honest.",
        ],
        economic_coherence_score=7.2,
    ),
}

MARKET = {
    ORACLE: MarketReport(
        customer=(
            "Tail-risk hedgers and perp/option desks needing "
            "regime-priced cover; oracle consumers needing honest "
            "fee quotes under moved regimes"
        ),
        problem=(
            "Anchored-trend fee oracles sell tail cover at "
            "anchor-normal premium right after permanent crashes — "
            "the r13 measured flaw: 7% of crash premium while the "
            "level stayed -60% moved"
        ),
        existing_alternatives=[
            "Fixed-schedule vol Surface updates (discrete banding)",
            "Perp funding-rate markets (indirect regime pricing)",
            "OTC desk quotes (opaque, manual)",
        ],
        market_size_note=(
            "Derivatives-margin and cover-fee demand is "
            "order-of-magnitude millions notional; the niche is honest "
            "regime persistence in quoted fees."
        ),
        adoption_barriers=[
            "Cover buyers prefer familiar discrete banding",
            "Three-speed calibration requires historical regime data",
        ],
        market_demand_score=6.0,
    ),
    JOULE: MarketReport(
        customer=(
            "Energy/compute delivery marketplaces needing sustained-"
            "default protection; escrowed infrastructure providers"
        ),
        problem=(
            "Drift alarms keyed to anchored trends heal under moved "
            "regimes — defaults timed to healed windows escape the "
            "slash premium (r13 measured: alarm fires 4 steps then "
            "heals)"
        ),
        existing_alternatives=[
            "Discrete performance-bond penalty schedules",
            "Manual SLA enforcement",
            "Threshold alerting + human review",
        ],
        market_size_note=(
            "Escrowed compute/energy delivery is a growing but niche "
            "segment; persistence semantics is a quality differentiator."
        ),
        adoption_barriers=[
            "Providers must accept persistent alarms during regime "
            "transitions",
            "Integration with delivery telemetry",
        ],
        market_demand_score=5.8,
    ),
}


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "0004dc2f0a3ccc94": PRIOR[JOULE],
        "48ef9846cfd211ec": ECON[JOULE],
        "742fe8b6ebe1a456": ECON[ORACLE],
        "ba12f9635c2a7eae": MARKET[ORACLE],
        "c7442c872d1ba907": MARKET[JOULE],
        "ccff3789af5d3301": PRIOR[ORACLE],
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
