"""Round 18: research answers for both successors (Class C honesty).

Three-Speed: adverse-selection premia are standard market-maker
practice (Glosten-Milgrom spread decomposition); the three-speed
persistent-displacement construction is the r13 lab primitive.
Symmetric-Cap: fee recycling/smoothing pools are standard (EIP-1559
base-fee mechanics recycle); the symmetric outflow cap is the fix
class for the measured uncapped-bleed family.

Run: .venv/bin/python scripts/r18_answer_research.py
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

A_PRIOR = PriorArtReport(
    novelty_class="adjacent_mechanism",
    similar_mechanisms=[
        SimilarMechanism(
            name="Glosten-Milgrom adverse-selection spreads",
            url="https://www.jstor.org/stable/1912771",
            similarity_note=(
                "Adverse-selection premia priced into quoted spreads — "
                "the academic foundation; here priced by a persistent "
                "regime-separation gate rather than microstructure "
                "inference"
            ),
        ),
        SimilarMechanism(
            name="Dynamic-collateral AMM fee switches",
            url="https://docs.uniswap.org/",
            similarity_note=(
                "Vol-scaled fee tiers respond to realized stress; they "
                "key single-window vol (heal-prone), not a persistent "
                "medium-vs-anchor separation"
            ),
        ),
    ],
    search_queries=[
        "adverse selection premium pricing mechanism",
        "persistent displacement fee gate EMA",
        "regime separation insurance pricing",
    ],
    sources=[
        ResearchSource(title="Glosten-Milgrom (J. Finance 1985)",
                       url="https://www.jstor.org/stable/1912771",
                       source_type="paper"),
        ResearchSource(title="Uniswap fee documentation",
                       url="https://docs.uniswap.org/",
                       source_type="protocol_doc"),
    ],
    findings=[
        "FACT: adverse-selection components of quoted spreads are "
        "foundational market-maker practice.",
        "FACT: dynamic fee switches key single-window realized vol.",
        "INFERENCE: no searched source prices adverse-selection cover "
        "by a medium-vs-ultra-slow-EMA separation gate — the "
        "persistent-displacement property measured in this lab's r13 "
        "construction.",
        "HYPOTHESIS: separation-keyed premia hold cover priced under "
        "moved regimes without false premia in smooth regimes.",
    ],
    confidence=0.7,
    conclusion=(
        "Adjacent mechanism: adverse-selection premia are standard; "
        "no substantially similar separation-keyed persistent-cover "
        "implementation was identified in the searched sources."
    ),
)

A_ECON = EconomistReport(
    summary=(
        "Cover priced by |medium EMA - ultra-slow anchor|: in smooth "
        "regimes the two EMAs track (premium ~base, no false cost); "
        "under a permanently moved regime the medium EMA stays "
        "displaced from the anchor (premium persists — protection "
        "remains priced while risk remains real); oscillation "
        "flattens both speeds (no wash harvest). The r13 successors "
        "measured heal ratios 0.93-1.0 under move-once-then-park; "
        "this model applies the same polarity to clearing risk."
    ),
    concerns=[
        EconomicConcern(
            topic="premium persistence cost",
            note=(
                "Persistent premia charge honest flow during the whole "
                "moved regime — the price of cover that does not heal "
                "away (disclosed intent)."
            ),
            severity=4.0,
        ),
    ],
    strengths=[
        "No anchor-heal: displacement persists by construction.",
        "Bounded premium (min(600, ...) cap).",
    ],
    economic_coherence_score=7.3,
)

A_MARKET = MarketReport(
    customer=(
        "Prediction-clearing venues needing adverse-selection cover "
        "that stays priced through regime moves"
    ),
    problem=(
        "Cover whose signal heals to its anchor under moved regimes "
        "(r18 measured: intensity heal 0.0 while the level stayed "
        "-60% moved — tail unpriced at maximal risk)"
    ),
    existing_alternatives=[
        "Single-window vol fees (heal-prone)",
        "Governance-voted risk parameters (discretionary)",
    ],
    market_size_note="All non-custodial clearing venues; niche but recurring.",
    adoption_barriers=["Persistent premia during moved regimes", "Anchor credibility"],
    market_demand_score=6.0,
)

B_PRIOR = PriorArtReport(
    novelty_class="adjacent_mechanism",
    similar_mechanisms=[
        SimilarMechanism(
            name="EIP-1559 base-fee recycling",
            url="https://eips.ethereum.org/EIPS/eip-1559",
            similarity_note=(
                "Fee-smoothing pools with capped adjustment rates — "
                "the cap discipline; here applied symmetrically to a "
                "reserve's inflow AND outflow"
            ),
        ),
        SimilarMechanism(
            name="Protocol treasury smoothing funds",
            url="https://docs.makerdao.com/",
            similarity_note=(
                "Reserves buffering fee flows; their outflows are "
                "governance-gated, not rate-capped symmetric"
            ),
        ),
    ],
    search_queries=[
        "fee recycle reserve mechanism",
        "symmetric flow cap treasury pool",
        "bounded outflow reserve design",
    ],
    sources=[
        ResearchSource(title="EIP-1559", url="https://eips.ethereum.org/EIPS/eip-1559",
                       source_type="protocol_doc"),
        ResearchSource(title="MakerDAO documentation",
                       url="https://docs.makerdao.com/", source_type="protocol_doc"),
    ],
    findings=[
        "FACT: fee-recycle and base-fee pools with capped adjustment "
        "rates are deployed practice.",
        "FACT: treasury outflows are typically governance-gated "
        "rather than rate-capped.",
        "INFERENCE: no searched source documents the specific failure "
        "mode this model fixes — an INFLOW-capped, OUTFLOW-uncapped "
        "pool draining to its floor under sustained sub-anchor "
        "regimes (r18 measured 509.7 standing).",
        "HYPOTHESIS: a symmetric cap bounds the regime-move tax to "
        "the declared rate.",
    ],
    confidence=0.7,
    conclusion=(
        "Adjacent mechanism: capped-rate fee pools are standard; the "
        "symmetric outflow cap as the fix for the measured uncapped-"
        "bleed family was not identified in the searched sources."
    ),
)

B_ECON = EconomistReport(
    summary=(
        "The reserve recycles fees with a SYMMETRIC rate cap: the "
        "same f_c bounds inflow and outflow, so a moved regime taxes "
        "the pool at a bounded rate instead of bleeding it to the "
        "floor (the r18 finding: uncapped outflow, 509.7 standing). "
        "A utilization index carries stress memory; demand-EMA-targeted "
        "reversion keeps capacity tracking demand."
    ),
    concerns=[
        EconomicConcern(
            topic="bounded drain still drains",
            note=(
                "The cap bounds the RATE, not the total: a long enough "
                "moved regime still draws the reserve toward its floor "
                "(bounded trajectory, disclosed)."
            ),
            severity=4.0,
        ),
    ],
    strengths=[
        "No min() asymmetry: bleed bounded by construction.",
        "Demand-following target (capacity tracks regime).",
    ],
    economic_coherence_score=7.2,
)

B_MARKET = MarketReport(
    customer="Protocols running fee-recycle reserves (L2 sequencers, relay nets)",
    problem=(
        "Inflow-capped, outflow-uncapped reserve designs bleed to "
        "their floor under sustained sub-anchor regimes (r18 measured)"
    ),
    existing_alternatives=["Governance-gated outflows", "Uncapped recycling"],
    market_size_note="Every fee-smoothing protocol; infrastructure-grade fix.",
    adoption_barriers=["Lower max recycle rate than uncapped designs"],
    market_demand_score=6.1,
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "1f558cb23cd9ffad": A_MARKET,
        "702a1a7969499df0": A_PRIOR,
        "a6e2841ae23b9c59": A_ECON,
        "62c86bcb8b30268d": B_MARKET,
        "f3078fd9a5419003": B_PRIOR,
        "9cfb78622510f622": B_ECON,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
