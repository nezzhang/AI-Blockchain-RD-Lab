"""r49: harden the §19 scores — fill the 5 no-agent dimensions for the finalists.

The scorer imputes technical_feasibility / capital_efficiency / network_effects
/ communication / viral_potential at the 5.0 floor for every candidate
(AUDITING.md weakness #1). This script drives the r49 dimension-assessment
path through the §30 bridge: for each finalist it runs `assess_candidate`,
which fails closed on each unanswered bridge request; the operator's authored
judgment (JUDGMENTS below) is installed — VALIDATED against DimensionAssessment
(§2) and recorded as a §22 agent run — and the loop resumes until the
candidate's no-agent dimensions are all filled. save_candidate (r48) recomputes
the composite from the fuller dimension set.

Every judgment is evidence_level=INFERENCE, confidence <= 0.8: calibrated
operator readings of the stored dossiers, NOT measurements. Rationales are
mechanism-specific so a dossier reader can check the reasoning. Scores are
allowed below the 5.0 midpoint where the dimension is genuinely weak.

Run: .venv/bin/python scripts/r49_assess_finalists.py
"""

# ruff: noqa: E501  (judgment rationales are long-form evidence prose, kept on
# one line per (dimension, candidate) cell for diffability)

from __future__ import annotations

import re

from blockchain_rd_lab.agents.base import LLMError
from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus
from blockchain_rd_lab.scoring.assessment import assess_candidate

_DIM_RE = re.compile(r"DIMENSION UNDER ASSESSMENT: (\w+)")


def _dim_of(request: dict) -> str:
    for m in request.get("messages", []):
        if m.get("role") == "system":
            match = _DIM_RE.search(m.get("content", ""))
            if match:
                return match.group(1)
    raise ValueError(f"no dimension in request {request.get('id')}")



# ---------------------------------------------------------------------------
# Operator judgments: {candidate_id: {dimension: (score, confidence, rationale)}}
# Authored against the stored dossiers. All INFERENCE, confidence <= 0.8.
# ---------------------------------------------------------------------------

JUDGMENTS: dict[str, dict[str, tuple[float, float, str]]] = {
    "cand-9200b07691c3": {  # Separation-Keyed Fee Smoothing Escrow
        "technical_feasibility": (7.0, 0.7, "Two EMAs, a clip on retention, and mirrored escrow inflow/outflow caps are plain deterministic on-chain arithmetic; no exotic crypto or heavy state beyond the two moving averages."),
        "capital_efficiency": (5.5, 0.6, "The escrow is capital by design: retention holds 0.1-0.9 of flow in the pool as the smoothing buffer, so capital is deliberately locked; the mirrored caps keep it bounded but not minimal."),
        "network_effects": (6.0, 0.6, "Smoothing quality scales with corridor flow: more volume tightens the fast/slow EMA separation estimate and deepens the buffer, so it serves heavy corridors better than thin ones."),
        "communication": (5.5, 0.6, "The headline (an escrow smooths fees) is easy, but the load-bearing idea — keying retention to the SIGNED fast/slow separation so resonance averages out — takes real explanation; the r20 ratchet history shows why the naive version failed."),
        "viral_potential": (4.5, 0.5, "Infrastructure fee smoothing spreads by integration into settlement venues, not by user word-of-mouth; no consumer-facing hook."),
    },
    "cand-0d8552635f8c": {  # Disagreement-Weighted Oracle Quorum
        "technical_feasibility": (5.5, 0.6, "Requires staking, a per-interval median, a disagreement prediction market with resolution, and trailing per-reporter calibration weights — a real stack of interacting parts, each buildable but nontrivial together."),
        "capital_efficiency": (5.0, 0.6, "Every reporter must lock slashable stake plus post deviation positions in the disagreement market; honesty is prepaid with locked capital, which is the design's cost."),
        "network_effects": (7.0, 0.7, "More reporters improve the median and deepen the disagreement market, and better calibration attracts more reporters — a genuine two-sided feedback where quorum integrity grows with participation."),
        "communication": (7.0, 0.7, "Reporters stake on their own deviation risk and the realized median resolves the stake: a crisp, memorable self-reference that is easy to state even if the calibration machinery is detailed."),
        "viral_potential": (6.0, 0.6, "A self-disciplining quorum is a strong pitch to protocols burned by governance-managed or captured feeds; spreads by integration among oracle consumers."),
    },
    "cand-e74d830a9479": {  # Demand-Index Escalation Ladder for FX Batches
        "technical_feasibility": (7.0, 0.7, "The demand index is derived entirely from on-chain queue depth (no oracle), the escalation schedule is a lookup, and the refund reserve is simple accounting — self-measuring keeps the build small."),
        "capital_efficiency": (6.0, 0.6, "Escalation premiums cycle through a reserve that refunds congested-epoch settlers rather than sitting as idle protocol capital; the locked float is transient, not permanent."),
        "network_effects": (6.0, 0.6, "More batch volume makes the queue-depth index a better scarcity signal and the reserve deeper, so the corridor prices congestion more accurately as it is used more."),
        "communication": (6.5, 0.7, "Price congestion by a published queue-depth index, then refund the escalations to the people who paid them — a clean two-beat story with no oracle to explain."),
        "viral_potential": (5.5, 0.6, "Targets the felt pain of cross-border FX cost and opacity; near-free off-peak settlement is an attractive, easily-demonstrated hook."),
    },
    "cand-ce333ff19e9e": {  # Forecast-Indexed Fee Smoothing Pool
        "technical_feasibility": (5.0, 0.6, "A continuous no-limit prediction market resolving on on-chain fee statistics, plus smoothing keyed to its implied probability, is real prediction-market infrastructure — the heaviest build among the finalists."),
        "capital_efficiency": (6.5, 0.7, "The smoothing buffer is pre-funded by the losing side of the forecast market rather than by idle protocol capital — the buffer exists before congestion arrives and is paid for by forecasters, a genuinely efficient funding path."),
        "network_effects": (6.5, 0.6, "More forecasters sharpen the implied-probability signal and deepen market liquidity, which keys the smoothing better — forecast quality and pool quality reinforce each other."),
        "communication": (6.5, 0.7, "A prediction market as the fee market's forward curve — the pool buys its congestion signal in advance from staked forecasts — is a vivid, accurate one-line analogy."),
        "viral_potential": (5.5, 0.6, "A fee-forecast market can attract speculators who bring liquidity, and the forward signal is useful beyond the pool; but it is a derivative niche, not a consumer product."),
    },
    "cand-f9682eb6fc72": {  # Prediction-Settled Hashprice Hedge Board
        "technical_feasibility": (5.5, 0.6, "Forward positions, settlement against a median of supplier-reported realized prices, and vol-marked margin are each standard derivatives machinery, but the endogenous settlement reference makes the board moderately intricate."),
        "capital_efficiency": (5.5, 0.6, "Margin marked to realized volatility scales locked capital with actual reference risk rather than a static haircut — efficient in calm periods, but margin is still locked collateral."),
        "network_effects": (6.5, 0.6, "Hedging needs both longs and shorts, and the settlement reference improves as more suppliers report realized prices — liquidity and reference quality compound together."),
        "communication": (5.5, 0.6, "A hedge board for compute price that settles on the market's own reported realized prices is crisp to AI-compute suppliers but 'hashprice-equivalent forward boards' is opaque to a general audience."),
        "viral_potential": (6.0, 0.6, "AI-compute revenue hedging is a live, growing pain with no incumbent venue; a working board could spread quickly inside that niche."),
    },
    "cand-e0c80c26b7f3": {  # Quote-Deviation Slashed FX Reference Feed
        "technical_feasibility": (7.0, 0.7, "Bonded quotes, a median, deviation-scaled slashing, and recycling slashed value to grants are all well-understood on-chain primitives with known implementations."),
        "capital_efficiency": (5.0, 0.6, "Each reporter locks a bond as prepaid deviation risk; that locked collateral is the cost of the integrity guarantee and is not put to other work."),
        "network_effects": (6.5, 0.6, "More bonded reporters make the median harder to move and the endogenous discipline stronger, so the feed's robustness grows with the reporter set."),
        "communication": (7.0, 0.7, "Deviation is prepaid through bonds rather than disputed after the fact — a very crisp one-liner that captures the whole design."),
        "viral_potential": (6.0, 0.6, "Oracle manipulation is a widely felt DeFi pain; a self-disciplined reference feed anchored to its own corridor's realized prices is an easy story to spread among integrators."),
    },
    "cand-3132499bb565": {  # Dual-Sided Bond Auction Rebalancer
        "technical_feasibility": (6.5, 0.6, "Two simultaneous auctions clearing at a crossed spread with a seasoning-bounded rebalance size are standard auction mechanics; no novel cryptography or oracle dependence."),
        "capital_efficiency": (6.0, 0.6, "Bounding each round's rebalance by seasoning depth means the treasury never has to clear its whole deviation at once — capital is deployed incrementally rather than held for worst-case."),
        "network_effects": (5.5, 0.6, "Auction clears improve with bidder depth, so more participating capital tightens the crossed spread; a real but moderate liquidity feedback."),
        "communication": (4.5, 0.5, "Dual-sided auction clearing at a crossed spread with seasoning-bounded rounds is jargon-dense; there is no simple one-line pitch a non-specialist would retain."),
        "viral_potential": (4.0, 0.5, "Treasury rebalancing is back-office infrastructure with no user-facing surface; it spreads by slow institutional adoption, not organically."),
    },
    "cand-a98b49da7189": {  # Corridor-Native FX Batch Matching
        "technical_feasibility": (6.5, 0.6, "Escrowed two-sided inventory, a deterministic batch matcher at mid-market, an impact check, and a rebate pool are all proven DEX/batch-auction components."),
        "capital_efficiency": (5.5, 0.6, "Liquidity providers lock escrowed inventory in both legs, but the batch matcher and spread-funded rebate pool put that capital to continuous work rather than leaving it idle."),
        "network_effects": (7.0, 0.7, "Batch matching is a textbook liquidity network effect: more orders per batch mean better mid-market fills, which attract more order flow and more posted inventory."),
        "communication": (6.0, 0.6, "Batch-clear corridor FX at mid-market against escrowed inventory is a familiar batch-auction story that payments and DEX audiences already understand."),
        "viral_potential": (5.5, 0.6, "Cross-border corridor cost and locked-liquidity pain is real and the batch-clearing pattern is proven elsewhere, giving it a credible adoption path."),
    },
    "cand-e8e15b483070": {  # Escrowed Batch-Clearing Insurance Pool
        "technical_feasibility": (7.0, 0.7, "An escrowed partitioned pool, deterministic exposure-weighted claim allocation, and a solvency check that defers the batch are simple, fully deterministic accounting with no external dependencies."),
        "capital_efficiency": (7.0, 0.7, "The design is about capital precision: partitioning stops solvent members' capital subsidizing correlated drains, and the solvency tie forces explicit recapitalization instead of silent overdraft."),
        "network_effects": (6.0, 0.6, "Pool depth and risk-spreading improve with membership, so more members make the partitions more resilient; a steady positive feedback."),
        "communication": (6.5, 0.7, "Correlated claims cannot silently drain the shared float — the pain and the fix are both easy to state and immediately land with anyone who has watched an insurance pool fail."),
        "viral_potential": (5.0, 0.5, "Insurance is trust-driven and spreads slowly, but a solvency-guaranteed pool is a strong pitch to exactly the cautious capital that avoids opaque pools."),
    },
    "cand-5d41cd41f68d": {  # Tranche-Segmented Settlement Guarantee Stack
        "technical_feasibility": (5.5, 0.6, "Risk-weighted collateral tranches plus a solvency check that dynamically reallocates guarantee fees is structured-finance tranching on-chain — buildable, but the risk-weighting and reallocation logic is the most intricate accounting here."),
        "capital_efficiency": (6.5, 0.6, "Capitalization is matched to queued exposure per tranche and risk migrates to the tranches priced to hold it — capital sits where the risk is rather than pooled blindly."),
        "network_effects": (5.5, 0.6, "The stack deepens as more capital joins the senior and first-loss tranches, improving the guarantee's capacity; a moderate capital-depth feedback."),
        "communication": (4.5, 0.5, "Tranche segmentation with risk-weighted dynamic fee reallocation is structured-finance jargon with no simple public-facing formulation; the hardest finalist to explain plainly."),
        "viral_potential": (4.0, 0.5, "Settlement guarantee stacks serve institutional settlement, an adoption-driven niche with essentially no organic spread."),
    },
}


def main() -> None:
    cfg = load_config()
    db = LabDatabase(REPO_ROOT / cfg.storage.database)
    bridge = AgentBridgeProvider(bridge_dir=cfg.providers["bridge"].bridge_dir)
    bridge.purge_pending()  # drop the CLI's orphaned first request

    finalists = db.list_candidates(status=CandidateStatus.FINALIST, limit=None)
    finalists.sort(key=lambda c: (-(c.overall_score or 0.0), c.name))

    for cand in finalists:
        judg = JUDGMENTS.get(cand.id)
        if judg is None:
            print(f"  SKIP {cand.id} {cand.name} (no authored judgments)")
            continue
        dossier = REPO_ROOT / "reports" / "finalists" / f"{cand.id}.md"
        excerpt = dossier.read_text(encoding="utf-8")[:3000] if dossier.exists() else ""
        # Drive the real bridge fail-closed loop: assess raises PENDING per
        # unanswered dimension; we install the authored judgment (validated
        # against DimensionAssessment by install_answer, §2) and resume.
        for _ in range(20):  # at most len(no_agent dims) + slack halts
            try:
                filled = assess_candidate(cand, bridge, db, dossier_excerpt=excerpt)
                print(f"  {cand.id} {cand.name[:40]}: +{len(filled)} dims -> {cand.overall_score}")
                break
            except LLMError as exc:
                pending = bridge.list_requests(status="pending")
                assert pending, "halt raised but no pending request"
                for req in pending:
                    dim = _dim_of(req)
                    if dim not in judg:
                        raise SystemExit(
                            f"no judgment authored for {cand.id}:{dim}"
                        ) from exc
                    score, conf, rationale = judg[dim]
                    bridge.install_answer(
                        req["id"],
                        {
                            "dimension": dim,
                            "score": score,
                            "confidence": conf,
                            "rationale": rationale,
                            "evidence_level": "INFERENCE",
                        },
                    )
        else:
            raise SystemExit(f"{cand.id}: did not converge after 20 halts")


if __name__ == "__main__":
    main()
