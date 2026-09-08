"""Round 16: research answers for Reversion-Keyed Demographic Reserve.

Honesty (§12): population-linked supply rules (Bosch-style demurrage,
Ampleforth rebases, demographic reserve boards) are the adjacent art;
the reversion-keyed EMA + additive-flow construction (no
multiplicative ratchet) is the differentiator. Class C.

Run: .venv/bin/python scripts/r16_answer_research.py
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

prior = PriorArtReport(
    novelty_class="adjacent_mechanism",
    similar_mechanisms=[
        SimilarMechanism(
            name="Ampleforth rebases",
            url="https://www.ampleforth.org/",
            similarity_note=(
                "Supply adjusts to a price signal — but multiplicatively "
                "(the exact ratchet this design removes); rebase "
                "volatility famously farms oscillation"
            ),
        ),
        SimilarMechanism(
            name="Demurrage currencies (Wörgl/Freigeld)",
            url="https://en.wikipedia.org/wiki/Worgl",
            similarity_note=(
                "Demographic/policy-linked decay of holdings — additive, "
                "like this design's bounded flows, but policy-keyed "
                "not level-EMA-keyed"
            ),
        ),
        SimilarMechanism(
            name="Basis/ESD-style elastic supply",
            url="https://basis.io/",
            similarity_note=(
                "Expansion/contraction by governance formula; the "
                "measured collapse mode of multiplicative contraction is "
                "the known failure family"
            ),
        ),
    ],
    search_queries=[
        "elastic supply token oscillation collapse",
        "population linked reserve rule",
        "reversion keyed EMA supply adjustment",
    ],
    sources=[
        ResearchSource(title="Ampleforth docs", url="https://www.ampleforth.org/",
                       source_type="protocol_doc"),
        ResearchSource(title="Wörgl demurrage history",
                       url="https://en.wikipedia.org/wiki/Worgl",
                       source_type="web"),
        ResearchSource(title="Basis whitepaper archive", url="https://basis.io/",
                       source_type="web"),
    ],
    findings=[
        "FACT: Ampleforth-style rebases adjust supply multiplicatively "
        "and are known to amplify under oscillation.",
        "FACT: demurrage designs adjust holdings additively.",
        "INFERENCE: no searched source keys supply to a REVERTING EMA "
        "of the level path with additive bounded flows — the two "
        "anti-harvest properties together.",
        "HYPOTHESIS: additive bounded flows make the supply immune to "
        "oscillation compounding (the r16 census measured -94% on the "
        "multiplicative form; the smoke measured 0.00 on this form).",
    ],
    confidence=0.7,
    conclusion=(
        "Adjacent mechanism: elastic-supply and demurrage designs are "
        "the known families; no substantially similar reversion-keyed "
        "EMA + additive-flow implementation was identified in the "
        "searched sources."
    ),
)

econ = EconomistReport(
    summary=(
        "The design converts a known failure family (multiplicative "
        "supply contraction under oscillation) into a bounded-flow "
        "response keyed to a signal oscillation cannot fake. The stock "
        "mean-reverts to its anchor; the flow cap bounds adjustment "
        "speed; the r16 census measured the multiplicative form "
        "collapsing -94% where this form measures 0.00."
    ),
    concerns=[
        EconomicConcern(
            topic="adjustment lag",
            note=(
                "The reverting EMA trades response speed for harvest "
                "immunity — genuine sustained drift carries, but slow."
            ),
            severity=4.0,
        ),
        EconomicConcern(
            topic="anchor trust",
            note=(
                "The 1000 anchor is a design constant; a moved regime "
                "re-bases the EMA target only at kappa speed (disclosed)."
            ),
            severity=4.0,
        ),
    ],
    strengths=[
        "Oscillation compounding: structurally impossible (additive flows).",
        "Whale-trace preserved without a farmable kicker scale.",
    ],
    economic_coherence_score=7.2,
)

market = MarketReport(
    customer=(
        "Communities needing population-linked unit-of-account supplies; "
        "DAOs parameterizing demographic-linked issuance"
    ),
    problem=(
        "Elastic-supply designs amplify oscillation (measured -94% pool "
        "collapses in the multiplicative family, the r16 census)"
    ),
    existing_alternatives=[
        "Rebase tokens (multiplicative — the failure family)",
        "Governance-voted supply boards (discretionary)",
        "Fixed supplies (no demographic response)",
    ],
    market_size_note=(
        "Niche but recurring: every population-linked token project "
        "re-encounters the oscillation-amplification problem."
    ),
    adoption_barriers=[
        "Anchor credibility",
        "Slower adjustment than rebase alternatives",
    ],
    market_demand_score=5.8,
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "3b1a6d748fc25447": market,
        "690c4275bb8a9012": prior,
        "9e8df1f2cc65849e": econ,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
