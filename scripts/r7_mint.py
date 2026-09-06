"""Round 7 part 2: mint the 6 successor candidates (lineage recorded).

Each successor carries the ORIGINAL mechanism intent (the idea was
never the problem — the EVIDENCE was), with an explicit lineage
claim naming its superseded predecessor and the correction purpose:
a model honoring the battery input contract (X_t anchor level ~1000,
dX_t delta, states seed at 1000, clip bounds bracketing that scale)
so §15 stress runs exercise real dynamics.

Status: RESEARCHING (prior-art research on the IDEA stands; the
research stage replays it free from stored bridge answers; formalization
starts the fresh evidence chain).
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

SUCCESSORS: list[dict[str, str | list[str] | bool]] = [
    {
        "name": "Vol-Weighted Fee Smoothing Escrow",
        "category": "transaction fee markets",
        "predecessor": "cand-7f4c2dee85e7",
        "problem": (
            "Volatile transaction fees make gas costs unpredictable and "
            "complicate batch settlement budgets"
        ),
        "core_mechanism": (
            "An escrow contract collects fees into a smoothed pool whose "
            "release rate responds to realized volatility: when measured "
            "volatility rises, more of each fee is retained to back "
            "settlement; when volatility decays, retained buffer releases "
            "to proposers, so per-transaction effective cost stays smooth"
        ),
        "description": (
            "Batch transactions pay into an escrowed fee pool. A "
            "volatility-weighted drawdown rule converts measured anchor "
            "volatility into a retention fraction and a release rate, "
            "smoothing effective fees across volatility regimes without "
            "a trusted price feed."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "queue depth"],
        "outputs": ["retention fraction", "release rate"],
    },
    {
        "name": "Tranche-Segmented Settlement Guarantee Stack",
        "category": "settlement guarantees",
        "predecessor": "cand-cb4d584867ed",
        "problem": (
            "Settlement guarantee pools concentrate risk: first-loss "
            "tranches absorb all shocks and senior capital earns un-risked yield"
        ),
        "core_mechanism": (
            "Guarantee capital is segmented into tranches with "
            "risk-weighted collateral; a solvency check compares "
            "tranche capitalization against queued settlement exposure "
            "and dynamically adjusts the guarantee fee each tranche "
            "charges, so risk migrates to the tranches priced to hold it"
        ),
        "description": (
            "A settlement guarantee stack prices each tranche's exposure "
            "per batch; a deterministic solvency rule reallocates "
            "guarantee fees across tranches when queued exposure grows, "
            "keeping total capitalization matched to total exposure."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "queued exposure"],
        "outputs": ["tranche guarantee fee", "solvency ratio"],
    },
    {
        "name": "Homeostatic Reserve Stablecoin",
        "category": "stablecoins",
        "predecessor": "cand-c17ab7a0f74e",
        "problem": (
            "Algorithmic stablecoins need a reserve rule that contracts "
            "supply in stress without a reflexive death spiral"
        ),
        "core_mechanism": (
            "A homeostatic controller adjusts the per-block reserve "
            "requirement and expansion rate as a function of the "
            "distance between the anchor price level and its long-run "
            "mean: deviations contract issuance and raise the reserve "
            "ratio; convergence releases expansion, so the controller "
            "always pulls the level back toward the mean"
        ),
        "description": (
            "The stablecoin's controller reads the anchor level and its "
            "delta, computes a mean-reversion pressure, and sets "
            "issuance and reserve requirements homeostatically — "
            "contraction under deviation, expansion under convergence."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "reserve ratio"],
        "outputs": ["issuance rate", "reserve requirement"],
    },
    {
        "name": "Dual-Sided Bond Auction Rebalancer",
        "category": "stablecoin routing",
        "predecessor": "cand-636a97854ac8",
        "problem": (
            "Treasury portfolios drift from target allocations; single-"
            "sided auctions rebalance slowly and at stale prices"
        ),
        "core_mechanism": (
            "Two simultaneous auctions (sell the overweight side, buy "
            "the underweight side) clear at a crossed spread; the "
            "rebalance size per round is bounded by a seasoning "
            "parameter so the treasury never needs to clear its whole "
            "deviation in one auction"
        ),
        "description": (
            "Each rebalancing round runs a dual-sided auction: capacity "
            "is set by seasoning depth, the sell side clears at the "
            "bid, the buy side at the ask, and realized slippage feeds "
            "back into the next round's capacity."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "deviation"],
        "outputs": ["rebalance capacity", "slippage"],
    },
    {
        "name": "Escrowed Batch-Clearing Insurance Pool",
        "category": "insurance",
        "predecessor": "cand-ef024f8bb596",
        "problem": (
            "On-chain insurance pools pay correlated claims from a "
            "shared float, draining solvent members' capital"
        ),
        "core_mechanism": (
            "Claims clear in batches against an escrowed, partitioned "
            "pool: a deterministic partition rule allocates each "
            "member's share of the batch claim bill by exposure weight, "
            "and a solvency check defers the batch when the shared "
            "float falls below a floor, so correlated claims cannot "
            "overdraw the pool silently"
        ),
        "description": (
            "Batched claims split the bill across exposure-weighted "
            "partitions of an escrowed pool; a solvency tie defers "
            "clearing when the float is short, forcing explicit "
            "re-capitalization instead of silent overdraft."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "claim bill"],
        "outputs": ["member share", "solvency floor distance"],
    },
    {
        "name": "Corridor-Native FX Batch Matching",
        "category": "payments",
        "predecessor": "cand-642ea9f42170",
        "problem": (
            "Cross-border FX corridors settle through correspondent "
            "chains with locked liquidity and opaque spreads"
        ),
        "core_mechanism": (
            "Corridor liquidity providers post escrowed inventory in "
            "both legs; a deterministic batch matcher clears corridor "
            "orders at a mid-market rate, an impact check bounds the "
            "per-batch price impact against posted depth, and a rebate "
            "pool pays providers from the matched spread"
        ),
        "description": (
            "FX corridor orders batch-clear against posted two-sided "
            "escrow; the impact check defers oversized batches and the "
            "rebate pool compensates posted inventory from captured "
            "spread."
        ),
        "inputs": ["X_t anchor price level", "dX_t anchor change", "order flow"],
        "outputs": ["impact bound", "rebate rate"],
    },
]


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    minted = 0
    for spec in SUCCESSORS:
        pred = db.get_candidate(str(spec["predecessor"]))
        assert pred is not None, f"predecessor {spec['predecessor']} missing"
        cand = Candidate(
            name=str(spec["name"]),
            category=str(spec["category"]),
            description=str(spec["description"]),
            core_mechanism=str(spec["core_mechanism"]),
            problem=str(spec["problem"]),
            innovation_claim=(
                f"Successor of {pred.id} (superseded r7 evidence-quality "
                f"correction: {pred.name}). The mechanism intent is "
                "unchanged; this candidate re-enters the funnel to build "
                "honest §15 evidence under the battery input contract "
                "(X_t anchor level ~1000, dX_t delta, states seeded at "
                "1000, clip bounds bracketing that scale), replacing "
                "vacuous/cycle-evidence scoring."
            ),
            inputs=list(spec["inputs"]),  # type: ignore[arg-type]
            outputs=list(spec["outputs"]),  # type: ignore[arg-type]
            oracle_required=False,
            blockchain_required=True,
            token_required=False,
            source_agent="discovery",
        )
        # prior research on the IDEA stands — start at RESEARCHED
        cand.status = CandidateStatus.RESEARCHING
        db.save_candidate(cand)
        minted += 1
        print(f"  {cand.id} <- {pred.id}  {cand.name[:46]}")
    print(f"\n{minted} successors minted (RESEARCHING)")


if __name__ == "__main__":
    main()
