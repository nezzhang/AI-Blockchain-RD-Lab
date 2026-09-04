"""Fixture idea batches for offline discovery demos and tests.

24 ideas spanning the 20 §24 discovery domains, including deliberate
near-duplicate pairs so `lab discover --provider mock` demonstrates the
dedup gate deterministically. Content is deterministic hand-written data —
these are *fixtures*, not research output.
"""

from __future__ import annotations

from blockchain_rd_lab.discovery import IdeaBatch, IdeaDraft


def _idea(**kw) -> IdeaDraft:
    return IdeaDraft(**kw)


FIXTURE_BATCHES: list[IdeaBatch] = [
    IdeaBatch(
        ideas=[
            _idea(
                name="Demographic Reserve Rule",
                category="monetary economics",
                domain="demographics",
                description=(
                    "Monetary base expands only when the dependency ratio "
                    "crosses set bands, coupling money creation to the age "
                    "structure of participants verified by census oracles."
                ),
                core_mechanism=(
                    "DeltaM = alpha * (dependency_ratio - band_center) "
                    "clamped by floors and caps each epoch."
                ),
                problem="Money supply ignores demographic reality",
                inputs=["dependency_ratio", "census_reports"],
                outputs=["base_money_delta"],
                oracle_required=True,
            ),
            _idea(
                name="Demographic Reserve Rule",  # EXACT duplicate (name-key)
                category="monetary economics",
                domain="demographics",
                description=(
                    "Monetary base expands when dependency ratio bands are "
                    "crossed, using census oracles for verification of age "
                    "structure of participants."
                ),
                core_mechanism="DeltaM = alpha * (dep_ratio - center), clamped.",
                problem="Money supply ignores demographic reality",
                inputs=["dependency_ratio"],
                outputs=["base_money_delta"],
                oracle_required=True,
            ),
            _idea(
                name="Carbon-Weighted Gas Fees",
                category="energy",
                domain="climate",
                description=(
                    "Transaction gas is priced by the verified carbon "
                    "intensity of the validator set's energy mix, so dirty "
                    "periods become expensive and clean periods cheap."
                ),
                core_mechanism=(
                    "GasPrice = base * (1 + beta * carbon_intensity_t), "
                    "carbon reported by metered energy oracles."
                ),
                problem="Blockchains ignore their energy externalities",
                inputs=["carbon_intensity", "validator_energy_mix"],
                outputs=["gas_price"],
                oracle_required=True,
                blockchain_required=True,
            ),
            _idea(
                name="Habitat Bond Curve",
                category="ecology",
                domain="ecology",
                description=(
                    "Conservation bonds whose redemption value grows with "
                    "satellite-verified habitat area restored, paying out "
                    "only on measured ecological outcomes."
                ),
                core_mechanism=(
                    "Redemption = principal * (1 + gamma * verified_area_delta); "
                    "satellite imagery adjudicates."
                ),
                problem="Conservation funding lacks outcome accountability",
                inputs=["satellite_habitat_area"],
                outputs=["redemption_value"],
                oracle_required=True,
            ),
        ],
        domains_requested=["demographics", "climate", "ecology"],
    ),
    IdeaBatch(
        ideas=[
            _idea(
                name="Prediction-Coupled Insurance Float",
                category="insurance",
                domain="prediction markets",
                description=(
                    "An insurance mutual reprices coverage each epoch from "
                    "live prediction-market odds on the insured event, "
                    "aligning float returns with crowd-updated risk."
                ),
                core_mechanism=(
                    "Premium(t+1) = Premium(t) * g(market_odds_t) with "
                    "float collateral staked by LPs."
                ),
                problem="Insurance pricing lags true risk",
                inputs=["market_odds", "claim_history"],
                outputs=["premium", "float_yield"],
                oracle_required=True,
            ),
            _idea(
                name="Labor-Backed Escrow",
                category="labor",
                domain="labor",
                description=(
                    "Freelance wages are escrowed in a pooled contract and "
                    "released by verified work-completion attestations, "
                    "letting earned-but-unpaid labor collateralize short-term credit."
                ),
                core_mechanism=(
                    "Escrow releases on multisig work verification; pool "
                    "lends against verified receivables."
                ),
                problem="Unpaid invoices lock worker liquidity",
                inputs=["work_attestations", "invoice_records"],
                outputs=["escrow_release", "credit_line"],
                oracle_required=True,
            ),
            _idea(
                name="Trade-Corridor Clearing Tokens",
                category="payments",
                domain="global trade",
                description=(
                    "Bilateral trade corridors mint corridor-specific "
                    "clearing credits backed by verified export volumes, "
                    "netting cross-border payments without global stablecoins."
                ),
                core_mechanism=(
                    "Credit supply = k * verified_export_volume; netting "
                    "clears corridor balances nightly."
                ),
                problem="Cross-border settlement is slow and costly",
                inputs=["customs_data", "export_volumes"],
                outputs=["corridor_credit"],
                oracle_required=True,
            ),
            _idea(
                name="Bandwidth Futures Market",
                category="network economics",
                domain="internet",
                description=(
                    "ISP peering agreements are replaced by an on-chain "
                    "bandwidth futures market where routes are purchased "
                    "ahead of congestion windows."
                ),
                core_mechanism=(
                    "Futures settle on metered throughput oracles; spot "
                    "market clears overflow."
                ),
                problem="Peering negotiation is opaque and slow",
                inputs=["throughput_meters"],
                outputs=["route_futures"],
                oracle_required=True,
            ),
        ],
        domains_requested=["prediction markets", "labor", "global trade", "internet"],
    ),
    IdeaBatch(
        ideas=[
            _idea(
                name="AI-Compute Denominated Debt",
                category="financial markets",
                domain="AI productivity",
                description=(
                    "Loans denominated in units of verified AI training "
                    "compute, so repayment tracks the falling price of "
                    "intelligence rather than fiat inflation."
                ),
                core_mechanism=(
                    "Debt quoted in compute-hours; settlement converts via "
                    "compute price oracles."
                ),
                problem="Monetary units ignore productivity deflation",
                inputs=["compute_price_index"],
                outputs=["debt_units"],
                oracle_required=True,
            ),
            _idea(
                name="Commodity-Volatility Stable Unit",
                category="stablecoins",
                domain="commodities",
                description=(
                    "A synthetic unit whose value targets a basket of "
                    "commodity price volatilities, stabilized by volatility "
                    "harvesting rather than collateral pegging."
                ),
                core_mechanism=(
                    "Unit targets sqrt(vol basket); rebalancing harvests "
                    "vol spread as yield."
                ),
                problem="Stablecoins import single-asset risk",
                inputs=["commodity_vol_index"],
                outputs=["stable_unit"],
                oracle_required=True,
            ),
            _idea(
                name="Gene-Sequence Royalty Stream",
                category="biology",
                domain="biology",
                description=(
                    "Synthesized gene sequences carry embedded royalty "
                    "streams paid per verified commercial use, sequenced "
                    "through auditable licensing oracles."
                ),
                core_mechanism=(
                    "Per-use micro-royalties metered by licensing oracles "
                    "into a stream split across contributors."
                ),
                problem="Bio IP royalties are unenforceable",
                inputs=["license_events"],
                outputs=["royalty_stream"],
                oracle_required=True,
            ),
            _idea(
                name="Sybil-Resistant Airdrop Market",
                category="game theory",
                domain="game theory",
                description=(
                    "Airdrop allocations are determined by a secondary "
                    "market in sealed reputation bids, making Sybil farming "
                    "unprofitable by construction."
                ),
                core_mechanism=(
                    "Sealed-bid reputation auction allocates the airdrop; "
                    "bid cost exceeds Sybil farm value."
                ),
                problem="Airdrops attract mercenary Sybils",
                inputs=["reputation_scores"],
                outputs=["allocation"],
                oracle_required=False,
            ),
        ],
        domains_requested=["AI productivity", "commodities", "biology", "game theory"],
    ),
    IdeaBatch(
        ideas=[
            _idea(
                name="Entropy-Priced Storage",
                category="distributed systems",
                domain="information theory",
                description=(
                    "Decentralized storage rent is priced by the entropy of "
                    "stored data chunks, rewarding deduplication at the "
                    "protocol level."
                ),
                core_mechanism=(
                    "Rent = base * H(chunk); identical chunks converge to "
                    "near-zero marginal price."
                ),
                problem="Storage pricing ignores redundancy waste",
                inputs=["chunk_hashes"],
                outputs=["rent_quote"],
                oracle_required=False,
            ),
            _idea(
                name="Insurance-Backed Validator Slashing Pool",
                category="security",
                domain="distributed systems",
                description=(
                    "Validator slashings are covered by a mutual insurance "
                    "pool priced by each validator's realized fault history, "
                    "turning slashing risk into a tradable premium."
                ),
                core_mechanism=(
                    "Premium = f(fault_history); pool mutualizes slashing "
                    "losses above deductible."
                ),
                problem="Slashing risk concentrates on small validators",
                inputs=["fault_history"],
                outputs=["premium", "coverage"],
                oracle_required=False,
            ),
            _idea(
                name="Demographic Dependency Reserve Rule",  # NEAR-duplicate of batch 1 idea 1
                category="monetary economics",
                domain="demographics",
                description=(
                    "Monetary base expands only when the dependency ratio "
                    "crosses set bands, using census oracles to verify age "
                    "structure of participants."
                ),
                core_mechanism="DeltaM = alpha * (dep_ratio - band_center), clamped.",
                problem="Money supply ignores demographic reality",
                inputs=["dependency_ratio"],
                outputs=["base_money_delta"],
                oracle_required=True,
            ),
            _idea(
                name="Orthogonal idea: Toll-Lane Finality",
                category="payments",
                domain="distributed systems",
                description=(
                    "Finality speed becomes a purchasable lane: slow lanes "
                    "are nearly free, fast lanes pay validators directly, "
                    "separating consensus from fee markets."
                ),
                core_mechanism=(
                    "Lane fees auctioned per slot; validators opt into "
                    "fast-lane service SLAs."
                ),
                problem="One finality speed for all needs",
                inputs=[],
                outputs=["lane_fee"],
                oracle_required=False,
            ),
        ],
        domains_requested=["information theory", "distributed systems", "demographics"],
    ),
]

def fixture_responses() -> list[str]:
    """Serialized JSON responses (one per batch) for MockLLMProvider."""
    import json

    return [
        json.dumps({"ideas": [i.model_dump() for i in batch.ideas]})
        for batch in FIXTURE_BATCHES
    ]
