"""Bridge answer for IdeaBatch 7e68ffa94530351e (marketxprediction pair).

Discovery batch: 5 ideas combining a market-driven mechanism with a
prediction-driven one, drawn from the requested domains (AI productivity,
financial markets, transaction fee markets).
"""

from __future__ import annotations

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.discovery import IdeaBatch, IdeaDraft

RID = "7e68ffa94530351e"

IDEAS = [
    {
        "name": "Forecast-Indexed Fee Smoothing Pool",
        "category": "monetary policy",
        "domain": "transaction fee markets",
        "description": (
            "Step 1: a fee smoothing pool holds a buffer of protocol fee "
            "revenue. Step 2: a prediction market runs continuous "
            "no-limit book auctions on the proposition 'median fee next "
            "epoch exceeds threshold T', with resolution by on-chain "
            "fee statistics. Step 3: the pool's smoothing intensity — how "
            "much buffer it injects or absorbs per epoch — is keyed to "
            "the implied congestion probability from that market rather "
            "than to spot congestion. Step 4: traders who stake the "
            "forecast wrong fund the buffer that compensates traders "
            "who face the realized outcome. Step 5: the pool publishes "
            "the implied probability and its action each epoch."
        ),
        "core_mechanism": (
            "A prediction market becomes the fee market's forward curve: "
            "instead of reacting to realized congestion, the smoothing "
            "pool buys its congestion signal in advance from staked "
            "forecasts. Forecast accuracy is rewarded by the market "
            "itself, and the pool's counter-cyclical buffer is pre-funded "
            "by the losing side of the forecast, so smoothing capacity "
            "exists before the congestion arrives."
        ),
        "problem": (
            "Fee smoothing mechanisms react to realized congestion, "
            "which is late: buffers refill after spikes instead of "
            "before them, and the smoothing signal is unfunded opinion "
            "rather than priced forecast."
        ),
        "innovation_claim": (
            "No substantially similar implementation was identified in "
            "the searched sources: a fee buffer whose injection rate is "
            "keyed to a continuously traded congestion-probability "
            "market that also funds the buffer from losing positions."
        ),
        "inputs": [
            "on-chain fee statistics per epoch",
            "forecast market positions",
            "buffer inventory",
        ],
        "outputs": ["epoch smoothing intensity", "published congestion probability"],
        "oracle_required": False,
        "blockchain_required": True,
        "token_required": False,
    },
    {
        "name": "Prediction-Settled Hashprice Hedge Board",
        "category": "derivatives",
        "domain": "AI productivity",
        "description": (
            "Step 1: compute suppliers (or AI-inference providers) post "
            "long/short positions on forward hashprice-equivalent compute "
            "price boards. Step 2: boards settle against a median of "
            "reported realized compute prices from registered suppliers, "
            "making the settlement reference a market statistic rather "
            "than a single oracle. Step 3: margin is marked to realized "
            "volatility of the settlement reference; volatile reference "
            "periods raise required margin deterministically. Step 4: "
            "suppliers whose realized revenue falls below their hedged "
            "band draw from counterparties' margin. Step 5: the board "
            "publishes the reference series and margin schedule."
        ),
        "core_mechanism": (
            "A market-priced hedge whose settlement reference is itself "
            "a market statistic: supplier-reported realized compute "
            "prices aggregate into the very index the hedge settles on. "
            "The forecast is a prediction market on the market's own "
            "future clearing price, so hedging demand and the reference "
            "price come from the same population, and margin scales with "
            "realized volatility of that reference."
        ),
        "problem": (
            "AI compute suppliers have no hedging venue for revenue "
            "per unit of work; existing derivative boards settle on "
            "single-source indices vulnerable to manipulation."
        ),
        "innovation_claim": (
            "No substantially similar implementation was identified in "
            "the searched sources: a median-of-supplier realized-price "
            "settlement reference with volatility-marked margin for "
            "compute-revenue hedges."
        ),
        "inputs": [
            "supplier-reported realized compute prices",
            "hedge positions and margin",
            "realized volatility of the reference",
        ],
        "outputs": ["settled hedge payouts", "published reference series"],
        "oracle_required": True,
        "blockchain_required": True,
        "token_required": False,
    },
    {
        "name": "Consensus-Odds Liquidity Rebate",
        "category": "incentive design",
        "domain": "financial markets",
        "description": (
            "Step 1: an exchange allocates a share of its taker-fee "
            "revenue to a rebate pool for makers. Step 2: alongside "
            "order books, a lightweight prediction book trades "
            "'next-window volume will exceed V' with binary settlement "
            "from exchange-published volume. Step 3: makers earn rebate "
            "multipliers when their quoted depth persists through "
            "windows the forecast market priced as high-demand. "
            "Step 4: the multiplier schedule is published per implied "
            "probability bucket, so deep quotes during forecast demand "
            "earn more than quotes in forecast slack. Step 5: the "
            "forecast book's losing side funds part of the rebate pool."
        ),
        "core_mechanism": (
            "The exchange buys forward demand information with real "
            "money: forecast traders stake on future volume, the losing "
            "side funds maker rebates, and the rebate schedule keys to "
            "the implied probability so that maker depth is most "
            "rewarded exactly when the market predicts it will be "
            "needed. Market-making becomes a forecast-aligned service "
            "instead of a flat subsidy."
        ),
        "problem": (
            "Maker rebates are typically flat and history-based, which "
            "over-subsidizes slack-period quoting and under-subsidizes "
            "depth when forward demand is high."
        ),
        "innovation_claim": (
            "No substantially similar implementation was identified in "
            "the searched sources: maker rebates whose multiplier "
            "schedule is keyed to a volume-forecast market that also "
            "funds the rebates."
        ),
        "inputs": [
            "taker fee revenue",
            "forecast book positions on future volume",
            "maker depth persistence measurements",
        ],
        "outputs": ["forecast-multiplied maker rebates", "published rebate schedule"],
        "oracle_required": False,
        "blockchain_required": True,
        "token_required": False,
    },
    {
        "name": "Adverse-Selection Taxed Prediction Clearing",
        "category": "market design",
        "domain": "financial markets",
        "description": (
            "Step 1: a prediction-clearing venue for tokenized claims "
            "charges a spread set from realized order-flow imbalance "
            "statistics. Step 2: when realized imbalance indicates "
            "informed flow (persistent one-sided pressure with "
            "subsequent reference moves), the spread widens "
            "deterministically for the aggressing side. Step 3: "
            "proceeds from the widened spread fund a liquidity-incentive "
            "pool paid to balanced two-sided flow. Step 4: the venue "
            "publishes the imbalance statistics and the spread schedule. "
            "Step 5: reference resolution uses the market's own "
            "time-weighted mid rather than last trade, bounding "
            "settlement manipulation."
        ),
        "core_mechanism": (
            "The market's realized flow statistics become the price of "
            "trading it: adverse selection detected in the market's own "
            "trade flow widens aggressor spreads and funds rebates for "
            "the balanced flow that repairs depth. The clearing rule "
            "and the fee rule read the same statistic, so informed "
            "pressure pays for its own externalities without any "
            "committee decision."
        ),
        "problem": (
            "Prediction venues suffer informed-flow leakage; flat fees "
            "subsidize extractive flow and under-reward depth-repairing "
            "flow."
        ),
        "innovation_claim": (
            "No substantially similar implementation was identified in "
            "the searched sources: a spread schedule set from realized "
            "order-flow imbalance with proceeds routed to balanced-flow "
            "rebates in the same venue."
        ),
        "inputs": [
            "order-flow imbalance series",
            "reference mid price series",
            "spread schedule parameters",
        ],
        "outputs": ["adaptive aggressor spreads", "balanced-flow rebate pool"],
        "oracle_required": False,
        "blockchain_required": True,
        "token_required": False,
    },
    {
        "name": "Belief-Weighted Volatility Target Fund",
        "category": "portfolio mechanism",
        "domain": "financial markets",
        "description": (
            "Step 1: a fund tracks a volatility target for its exposure "
            "to a basket of protocol assets. Step 2: prediction markets "
            "on future realized volatility (bucketed ranges) trade "
            "continuously; the fund holds small stakes that pay out when "
            "volatility lands in extreme buckets. Step 3: the fund's "
            "risk engine blends realized volatility with the "
            "market-implied bucket probabilities to set exposure. "
            "Step 4: when implied probability of stress buckets rises, "
            "the fund de-risks before realized volatility confirms the "
            "move, funded partly by the prediction payouts. Step 5: "
            "the blend weights and exposures are published per rebalance."
        ),
        "core_mechanism": (
            "Forward-looking market beliefs meet backward-looking "
            "realized statistics: the exposure rule is a deterministic "
            "blend of both, and the prediction stakes convert "
            "de-risking from a pure cost into a partially self-funding "
            "action — when the market's stress belief rises and the "
            "stress arrives, prediction payouts offset the cost of "
            "having been conservative."
        ),
        "problem": (
            "Volatility targeting reacts to realized volatility only; "
            "de-risking after confirmation is expensive and late, and "
            "existing designs have no priced forward signal to blend."
        ),
        "innovation_claim": (
            "No substantially similar implementation was identified in "
            "the searched sources: a volatility-target fund whose "
            "exposure blends realized volatility with bucketed "
            "volatility-forecast probabilities and holds compensating "
            "stakes in those forecasts."
        ),
        "inputs": [
            "realized volatility series",
            "implied bucket probabilities from forecast markets",
            "prediction stakes",
        ],
        "outputs": ["published exposure per rebalance", "self-funded de-risking"],
        "oracle_required": True,
        "blockchain_required": True,
        "token_required": False,
    },
]


def main() -> None:
    batch = IdeaBatch.model_validate(
        {
            "batch_id": "batch-r8-combine-01",
            "ideas": [IdeaDraft.model_validate(i) for i in IDEAS],
            "source_agent": "discovery",
            "domains_requested": [
                "AI productivity",
                "financial markets",
                "transaction fee markets",
            ],
        }
    )
    bridge = AgentBridgeProvider()
    payload = {
        "batch_id": batch.batch_id,
        "ideas": [i.model_dump() for i in batch.ideas],
        "source_agent": "discovery",
        "domains_requested": batch.domains_requested,
    }
    bridge.install_answer(RID, payload)
    print(f"installed {len(batch.ideas)} ideas for {RID}")


if __name__ == "__main__":
    main()
