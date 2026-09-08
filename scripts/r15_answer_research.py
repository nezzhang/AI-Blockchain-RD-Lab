"""Round 15: research answers for the Level-Recentered Bandwidth Bond Market.

Honesty (§12): level-tracking collateral pools are standard treasury
practice (rebalancing to an index); the single-magnet re-basing
construction (pool follows a slow level EMA so the stress deviation
CLOSES after permanent shifts) is the mechanism surface. Class C.

Run: .venv/bin/python scripts/r15_answer_research.py
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
            name="Index-rebalancing collateral pools (treasury practice)",
            url="https://www.icmagroup.org/",
            similarity_note=(
                "Rebalancing collateral toward an index level is standard "
                "treasury management; here the index is the bandwidth "
                "level and the rebalancing is on-chain and continuous"
            ),
        ),
        SimilarMechanism(
            name="Balancer-style weighted pools",
            url="https://docs.balancer.fi/",
            similarity_note=(
                "AMM pools that track target weights via arbitrage; the "
                "single-magnet EMA pool tracks a level via deterministic "
                "flows, not arbitrage incentives"
            ),
        ),
        SimilarMechanism(
            name="MakerDAO stability-fee / LIQ mechanisms",
            url="https://docs.makerdao.com/",
            similarity_note=(
                "Collateral pools with stress parameters; their params "
                "anchor to governance targets rather than re-basing to "
                "the collateral level itself"
            ),
        ),
    ],
    search_queries=[
        "collateral pool level rebasing mechanism",
        "bandwidth bond market relay peers",
        "single magnet pool tracking level EMA",
    ],
    sources=[
        ResearchSource(title="ICMA treasury practice",
                       url="https://www.icmagroup.org/", source_type="intl_org"),
        ResearchSource(title="Balancer documentation",
                       url="https://docs.balancer.fi/", source_type="protocol_doc"),
        ResearchSource(title="MakerDAO documentation",
                       url="https://docs.makerdao.com/", source_type="protocol_doc"),
    ],
    findings=[
        "FACT: index-rebalancing collateral management is standard "
        "institutional treasury practice.",
        "FACT: AMM pools track target weights via arbitrage; the "
        "mechanism here uses deterministic EMA flows instead.",
        "INFERENCE: no searched source implements a stress-slash design "
        "whose deviation closes by construction (pool follows the level "
        "EMA) — the searched pools anchor to governance targets, which "
        "is exactly the two-magnet flaw class the r15 round measured.",
        "HYPOTHESIS: single-magnet re-basing bounds slash cost to the "
        "shift's transient window, removing the standing-burn "
        "equilibrium that relatively enriches allocation holders.",
    ],
    confidence=0.7,
    conclusion=(
        "Adjacent mechanism: index-rebalancing collateral pools are "
        "standard treasury practice, but no substantially similar "
        "implementation was identified in the searched sources."
    ),
)

econ = EconomistReport(
    summary=(
        "A single-magnet pool (slow EMA of the level) makes the "
        "collateral's economics honest under permanent shifts: the "
        "pool re-bases, the stress deviation closes, and the slash is "
        "bounded to the re-basing transient. The predecessor's "
        "two-magnet equilibrium (22% from the level, burning 17.7/step "
        "forever while A/C doubled) is structurally gone — measured "
        "late-window stress 0.0000 after the fix."
    ),
    concerns=[
        EconomicConcern(
            topic="re-basing window slash cost",
            note=(
                "During the re-basing window the slash fires "
                "transiently; honest peers posting collateral at the "
                "shift moment bear a bounded cost — the price of "
                "persistence-correct semantics (disclosed)."
            ),
            severity=5.0,
        ),
        EconomicConcern(
            topic="allocation tracks the pool",
            note=(
                "A_t weighting 0.5*C_t ties relay allocation to the "
                "re-based pool; a falling level contracts allocation "
                "proportionally — honest, but a policy choice that "
                "shrinkage passes through to capacity."
            ),
            severity=4.0,
        ),
    ],
    strengths=[
        "No standing burn: the deviation closes by construction.",
        "No relative enrichment: allocation tracks the re-based pool.",
    ],
    economic_coherence_score=7.3,
)

market = MarketReport(
    customer=(
        "Relay/bandwidth marketplaces needing collateralized peer "
        "bonding; bandwidth buyers needing predictable peer capacity"
    ),
    problem=(
        "Two-magnet collateral pools settle between their anchors "
        "under permanent shifts and burn forever (the r15 measured "
        "flaw in the predecessor: standing 17.7/step, C_t drawn 179)"
    ),
    existing_alternatives=[
        "Fixed collateral schedules (no re-basing)",
        "Governance-voted pool parameters (two-magnet risk)",
        "Uncollateralized reputation systems",
    ],
    market_size_note=(
        "Relay-bandwidth marketplaces are a growing niche; honest "
        "re-basing collateral is a quality differentiator on "
        "mechanism-design grounds."
    ),
    adoption_barriers=[
        "Peers must accept transient slash during shift windows",
        "Level oracle integration (the bandwidth index)",
    ],
    market_demand_score=5.9,
)


def main() -> None:
    p = AgentBridgeProvider()
    mapping = {
        "5f10910d1343b6e6": econ,
        "8686c515ddb64927": prior,
        "cd3a01e4f1d606d1": market,
    }
    for rid, ans in mapping.items():
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
