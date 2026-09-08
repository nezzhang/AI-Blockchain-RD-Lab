"""Round 19: research answers for the wage-pool successor.

Prior art: productivity/compute-indexed payment pools exist (GPU
spot markets, index-linked contracts); the specific construction
here — single-magnet re-centering pool with a floor below the
deepest crash level — is the lab's own measured fix lineage.

Run: .venv/bin/python scripts/r19_answer_research.py
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

PRIOR = PriorArtReport(
    novelty_class="adjacent_mechanism",
    similar_mechanisms=[
        SimilarMechanism(
            name="Index-linked wage contracts (CPI escalators)",
            url="https://www.bls.gov/cpi/",
            similarity_note=(
                "Wages indexed to an external index are long-standing "
                "practice (COLA clauses); here the index is an "
                "on-chain level series and the pool re-centers with "
                "bounded flows"
            ),
        ),
        SimilarMechanism(
            name="GPU spot-price compute markets",
            url="https://vast.ai/pricing",
            similarity_note=(
                "Compute priced by a spot index; spot-following pools "
                "re-price instantly (no bounded re-basing), exposing "
                "them to the exact spike/lag tradeoffs this model "
                "bounds"
            ),
        ),
    ],
    search_queries=[
        "compute wage pool index linked mechanism",
        "bounded flow re-centering pool design",
        "productivity indexed payments protocol",
    ],
    sources=[
        ResearchSource(title="BLS CPI documentation",
                       url="https://www.bls.gov/cpi/",
                       source_type="gov_dataset"),
        ResearchSource(title="Vast.ai pricing documentation",
                       url="https://vast.ai/pricing",
                       source_type="web"),
    ],
    findings=[
        "FACT: index-linked wage escalators are long-standing "
        "contract practice.",
        "FACT: compute spot markets price by a spot index with "
        "instant re-pricing.",
        "INFERENCE: no searched source documents a bounded-flow, "
        "floor-below-crash-level re-centering pool — the specific "
        "construction this model's lineage measured its way to "
        "(r15 bandwidth finding, re-measured r19 at 120/240 windows).",
        "HYPOTHESIS: the single-magnet pool bounds both the spike "
        "pass-through and the re-basing lag at declared rates.",
    ],
    confidence=0.7,
    conclusion=(
        "Adjacent mechanism: index-linked payments are standard; the "
        "bounded re-centering pool with the floor placement discipline "
        "was not identified in the searched sources."
    ),
)

ECON = EconomistReport(
    summary=(
        "The pool chases a slow bounded-step EMA of the level with a "
        "symmetrically capped flow (±f_c/step): sustained regime "
        "moves re-base the pool at a bounded rate (the audit finding — "
        "a pool whose floor sat above the crash level pinned at 600 "
        "forever; this floor sits at 250, below the crash level, so "
        "the pool arrives); zero-mean oscillation leaves the slow EMA "
        "flat (no wash harvest); the delivery kicker preserves "
        "whale-trace at sub-farmable scale (worst battery edge 0.73 "
        "measured). The stress memory S_w is disclosure-only."
    ),
    concerns=[
        EconomicConcern(
            topic="bounded re-basing lag",
            note=(
                "The capped flow means the pool lags fast regime moves "
                "by construction — the r17 responsiveness class, "
                "disclosed per state (design lag, not extraction)."
            ),
            severity=4.0,
        ),
    ],
    strengths=[
        "Floor below crash level: the pool re-bases by construction.",
        "Symmetric cap: bounded both directions.",
    ],
    economic_coherence_score=7.2,
)

MARKET = MarketReport(
    customer="Compute networks paying providers against a level index",
    problem=(
        "Index-linked pools whose floors sit above deep crash levels "
        "pin and never re-base (measured standing 400 at 120/240-step "
        "windows, r19) — provider pay stays mispriced through the "
        "whole moved regime"
    ),
    existing_alternatives=[
        "Spot re-pricing (instant, unbounded)",
        "Governance-voted wage updates (discretionary)",
    ],
    market_size_note="Decentralized compute networks; infrastructure-grade.",
    adoption_barriers=["Bounded lag vs spot re-pricing", "Index credibility"],
    market_demand_score=6.1,
)


def main() -> None:
    p = AgentBridgeProvider()
    for rid, ans in [
        ("d32be653164ce7e4", PRIOR),
        ("3d6b5fae62bc5ffb", ECON),
        ("0f7ac7094cc529c8", MARKET),
    ]:
        p.install_answer(rid, ans.model_dump(mode="json"))
        print("installed", rid, type(ans).__name__)


if __name__ == "__main__":
    main()
