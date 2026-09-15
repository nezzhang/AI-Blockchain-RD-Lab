"""§17 supply driver registry.

Each driver defines a category of token supply signal, its oracle
data source, a deterministic supply function mapping state to a
mint/burn rate, known manipulation vectors (§25), and economic
compatibility tags used by the combinator for non-random matching.

All supply functions are PURE: same (state, params) → same float.
No randomness, no LLM calls, no wall-clock reads. Determinism is
the contract.

r39: initial 13-driver registry per §17 categories.
"""

from __future__ import annotations

import enum
import math
from collections.abc import Callable
from dataclasses import dataclass, field


class DriverCategory(enum.StrEnum):
    """The 13 §17 supply driver categories."""

    MARKET = "market-driven"
    USAGE = "usage-driven"
    ECONOMIC = "economic-driven"
    DEMOGRAPHIC = "demographic-driven"
    PRODUCTIVITY = "productivity-driven"
    ENERGY = "energy-driven"
    CLIMATE = "climate-driven"
    COMMODITY = "commodity-driven"
    INSURANCE = "insurance-driven"
    PREDICTION = "prediction-driven"
    NETWORK = "network-driven"
    AI = "ai-driven"
    HYBRID = "hybrid"


# Type alias: a supply function takes a state dict and returns a
# signed float (positive = mint pressure, negative = burn pressure,
# zero = neutral). The state dict keys are driver-specific.
SupplyFunction = Callable[[dict[str, float]], float]


@dataclass(frozen=True)
class SupplyDriver:
    """One supply driver definition.

    Attributes:
        category: which §17 bucket this falls in.
        name: short human-readable identifier.
        signal_source: what oracle/data feeds this driver.
        supply_fn: pure function mapping state → mint/burn rate.
        manipulation_vectors: known attack surfaces per §25.
        compatibility_tags: used by the combinator for semantic
            matching against mechanism descriptions.
        offline_scoreable: whether this driver can be meaningfully
            scored without live oracle data (the §2 caveat).
    """

    category: DriverCategory
    name: str
    signal_source: str
    supply_fn: SupplyFunction = field(compare=False)
    # Deterministic states used by scoring to test documented supply paths.
    burn_probe_states: tuple[dict[str, float], ...] = ()
    mint_probe_states: tuple[dict[str, float], ...] = ()
    manipulation_vectors: tuple[str, ...] = ()
    compatibility_tags: frozenset[str] = frozenset()
    offline_scoreable: bool = True


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    """Deterministic clamp — no NaN propagation."""
    if math.isnan(value):
        return 0.0
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Driver implementations
# Each supply_fn reads specific keys from the state dict. Missing keys
# default to 0.0 (the honest absence convention from the lab's scoring).
# ---------------------------------------------------------------------------


def _market_supply(state: dict[str, float]) -> float:
    """Mint pressure proportional to trading volume above baseline;
    burn when volume drops below."""
    vol = state.get("trading_volume", 0.0)
    baseline = state.get("volume_baseline", 1.0)
    if baseline <= 0:
        return 0.0
    return _clamp((vol - baseline) / baseline)


def _usage_supply(state: dict[str, float]) -> float:
    """Mint proportional to active user growth rate."""
    users = state.get("active_users", 0.0)
    prev = state.get("prev_active_users", 1.0)
    if prev <= 0:
        return 0.0
    return _clamp((users - prev) / prev)


def _economic_supply(state: dict[str, float]) -> float:
    """Counter-cyclical: mint during contraction, burn during
    expansion. Signal = GDP growth proxy."""
    gdp_growth = state.get("gdp_growth_rate", 0.0)
    return _clamp(-gdp_growth)  # inverted


def _demographic_supply(state: dict[str, float]) -> float:
    """Mint proportional to population growth in served corridors."""
    pop = state.get("corridor_population", 0.0)
    prev_pop = state.get("prev_corridor_population", 1.0)
    if prev_pop <= 0:
        return 0.0
    return _clamp((pop - prev_pop) / prev_pop, lo=-0.1, hi=0.5)


def _productivity_supply(state: dict[str, float]) -> float:
    """Burn proportional to productivity gains (deflationary bias
    when the network becomes more efficient)."""
    prod = state.get("productivity_index", 1.0)
    prev_prod = state.get("prev_productivity_index", 1.0)
    if prev_prod <= 0:
        return 0.0
    return _clamp(-(prod - prev_prod) / prev_prod)


def _energy_supply(state: dict[str, float]) -> float:
    """Mint linked to renewable energy production as proof-of-useful-work."""
    energy = state.get("renewable_energy_mwh", 0.0)
    target = state.get("energy_target_mwh", 1.0)
    if target <= 0:
        return 0.0
    return _clamp(energy / target - 1.0)


def _climate_supply(state: dict[str, float]) -> float:
    """Burn pressure when climate risk indices rise (insurance-cost signal)."""
    risk = state.get("climate_risk_index", 0.0)
    return _clamp(-risk)


def _commodity_supply(state: dict[str, float]) -> float:
    """Mint/burn pegged to a commodity basket deviation from target."""
    price = state.get("commodity_basket_price", 100.0)
    target = state.get("commodity_target_price", 100.0)
    if target <= 0:
        return 0.0
    return _clamp((price - target) / target)


def _insurance_supply(state: dict[str, float]) -> float:
    """Mint when insurance claims ratio rises (liquidity injection for
    corridor stability)."""
    claims = state.get("claims_ratio", 0.0)
    return _clamp(claims, lo=0.0, hi=1.0)


def _prediction_supply(state: dict[str, float]) -> float:
    """Burn when prediction market confidence is high (less need for
    incentive); mint when uncertain."""
    confidence = state.get("prediction_confidence", 0.5)
    return _clamp(0.5 - confidence)


def _network_supply(state: dict[str, float]) -> float:
    """Metcalfe-scaled: mint proportional to log(network_size) growth."""
    nodes = state.get("network_nodes", 1.0)
    prev = state.get("prev_network_nodes", 1.0)
    if prev <= 0 or nodes <= 0:
        return 0.0
    return _clamp(math.log(nodes) - math.log(prev))


def _ai_supply(state: dict[str, float]) -> float:
    """Burn proportional to AI agent throughput (efficiency deflation)."""
    throughput = state.get("ai_throughput_ops", 0.0)
    baseline = state.get("ai_baseline_ops", 1.0)
    if baseline <= 0:
        return 0.0
    return _clamp(-(throughput - baseline) / baseline)


def _hybrid_supply(state: dict[str, float]) -> float:
    """Weighted average of usage + network signals. The hybrid driver
    exists to test whether combining two compatible drivers produces
    a better game-theoretic equilibrium than either alone."""
    u = _usage_supply(state)
    n = _network_supply(state)
    w_usage = state.get("hybrid_weight_usage", 0.6)
    return _clamp(u * w_usage + n * (1.0 - w_usage))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DRIVER_REGISTRY: tuple[SupplyDriver, ...] = (
    SupplyDriver(
        category=DriverCategory.MARKET,
        name="market-volume",
        signal_source="on-chain DEX volume oracle",
        supply_fn=_market_supply,
        burn_probe_states=({"trading_volume": 0.0, "volume_baseline": 1.0},),
        mint_probe_states=({"trading_volume": 2.0, "volume_baseline": 1.0},),
        manipulation_vectors=(
            "wash trading inflates volume signal",
            "flash-loan volume spikes trigger false mint",
        ),
        compatibility_tags=frozenset({"exchange", "dex", "trading", "fee"}),
    ),
    SupplyDriver(
        category=DriverCategory.USAGE,
        name="usage-growth",
        signal_source="unique sender count per epoch",
        supply_fn=_usage_supply,
        burn_probe_states=({"active_users": 0.0, "prev_active_users": 100.0},),
        mint_probe_states=({"active_users": 200.0, "prev_active_users": 100.0},),
        manipulation_vectors=(
            "sybil accounts inflate user count",
            "dust transactions create false activity",
        ),
        compatibility_tags=frozenset({"payment", "remittance", "escrow", "fx"}),
    ),
    SupplyDriver(
        category=DriverCategory.ECONOMIC,
        name="counter-cyclical-gdp",
        signal_source="GDP growth oracle (World Bank / IMF feed)",
        supply_fn=_economic_supply,
        burn_probe_states=({"gdp_growth_rate": 0.5},),
        mint_probe_states=({"gdp_growth_rate": -0.5},),
        manipulation_vectors=(
            "GDP revision lag creates stale signal",
            "government data manipulation",
        ),
        compatibility_tags=frozenset({"macro", "stability", "reserve"}),
        offline_scoreable=False,
    ),
    SupplyDriver(
        category=DriverCategory.DEMOGRAPHIC,
        name="corridor-population",
        signal_source="UN population estimates for served corridors",
        supply_fn=_demographic_supply,
        burn_probe_states=({"corridor_population": 50.0, "prev_corridor_population": 100.0},),
        mint_probe_states=({"corridor_population": 150.0, "prev_corridor_population": 100.0},),
        manipulation_vectors=(
            "population data revised retroactively",
            "demographic collapse edge case (§25)",
        ),
        compatibility_tags=frozenset({"remittance", "corridor", "fx", "population"}),
        offline_scoreable=False,
    ),
    SupplyDriver(
        category=DriverCategory.PRODUCTIVITY,
        name="productivity-deflation",
        signal_source="transactions-per-second efficiency metric",
        supply_fn=_productivity_supply,
        burn_probe_states=({"productivity_index": 2.0, "prev_productivity_index": 1.0},),
        mint_probe_states=({"productivity_index": 0.5, "prev_productivity_index": 1.0},),
        manipulation_vectors=(
            "artificial load inflation to suppress burn",
        ),
        compatibility_tags=frozenset({"efficiency", "scaling", "throughput"}),
    ),
    SupplyDriver(
        category=DriverCategory.ENERGY,
        name="renewable-energy-pow",
        signal_source="verified renewable energy production oracle",
        supply_fn=_energy_supply,
        burn_probe_states=({"renewable_energy_mwh": 0.0, "energy_target_mwh": 1.0},),
        mint_probe_states=({"renewable_energy_mwh": 2.0, "energy_target_mwh": 1.0},),
        manipulation_vectors=(
            "oracle reports unverifiable off-grid energy",
            "double-counting across chains",
        ),
        compatibility_tags=frozenset({"proof-of-work", "green", "energy"}),
        offline_scoreable=False,
    ),
    SupplyDriver(
        category=DriverCategory.CLIMATE,
        name="climate-risk-burn",
        signal_source="climate risk index oracle",
        supply_fn=_climate_supply,
        burn_probe_states=({"climate_risk_index": 1.0},),
        mint_probe_states=({"climate_risk_index": -1.0},),
        manipulation_vectors=(
            "index provider capture",
            "geographic cherry-picking",
        ),
        compatibility_tags=frozenset({"insurance", "risk", "climate"}),
        offline_scoreable=False,
    ),
    SupplyDriver(
        category=DriverCategory.COMMODITY,
        name="commodity-basket-peg",
        signal_source="basket-of-commodities price oracle",
        supply_fn=_commodity_supply,
        burn_probe_states=({"commodity_basket_price": 50.0, "commodity_target_price": 100.0},),
        mint_probe_states=({"commodity_basket_price": 150.0, "commodity_target_price": 100.0},),
        manipulation_vectors=(
            "oracle front-running on basket rebalance",
            "single-commodity flash crash cascades",
        ),
        compatibility_tags=frozenset({"stablecoin", "peg", "commodity", "reserve"}),
        offline_scoreable=False,
    ),
    SupplyDriver(
        category=DriverCategory.INSURANCE,
        name="claims-ratio-mint",
        signal_source="on-chain insurance claims pool ratio",
        supply_fn=_insurance_supply,
        burn_probe_states=(),
        mint_probe_states=({"claims_ratio": 0.8},),
        manipulation_vectors=(
            "false claims inflate ratio",
            "collusion between claimant and assessor",
        ),
        compatibility_tags=frozenset({"insurance", "escrow", "risk", "pool"}),
    ),
    SupplyDriver(
        category=DriverCategory.PREDICTION,
        name="uncertainty-mint",
        signal_source="prediction market resolution confidence",
        supply_fn=_prediction_supply,
        burn_probe_states=({"prediction_confidence": 0.9},),
        mint_probe_states=({"prediction_confidence": 0.1},),
        manipulation_vectors=(
            "whale manipulation of prediction markets",
            "oracle dispute stalling resolution",
        ),
        compatibility_tags=frozenset({"prediction", "oracle", "market"}),
    ),
    SupplyDriver(
        category=DriverCategory.NETWORK,
        name="metcalfe-growth",
        signal_source="unique node count per epoch",
        supply_fn=_network_supply,
        burn_probe_states=({"network_nodes": 5.0, "prev_network_nodes": 10.0},),
        mint_probe_states=({"network_nodes": 100.0, "prev_network_nodes": 10.0},),
        manipulation_vectors=(
            "eclipse attacks hide real node count",
            "virtual nodes inflate metcalfe signal",
        ),
        compatibility_tags=frozenset({"network", "scaling", "nodes", "p2p"}),
    ),
    SupplyDriver(
        category=DriverCategory.AI,
        name="ai-throughput-deflation",
        signal_source="AI agent operation count per epoch",
        supply_fn=_ai_supply,
        burn_probe_states=({"ai_throughput_ops": 100.0, "ai_baseline_ops": 1.0},),
        mint_probe_states=({"ai_throughput_ops": 0.0, "ai_baseline_ops": 1.0},),
        manipulation_vectors=(
            "no-op AI calls inflate throughput",
            "agent collusion to suppress burn rate",
        ),
        compatibility_tags=frozenset({"ai", "agent", "automation", "throughput"}),
    ),
    SupplyDriver(
        category=DriverCategory.HYBRID,
        name="usage-network-hybrid",
        signal_source="composite: unique senders + node count",
        supply_fn=_hybrid_supply,
        burn_probe_states=({
            "active_users": 0.0, "prev_active_users": 100.0,
            "network_nodes": 5.0, "prev_network_nodes": 10.0,
        },),
        mint_probe_states=({
            "active_users": 200.0, "prev_active_users": 100.0,
            "network_nodes": 100.0, "prev_network_nodes": 10.0,
        },),
        manipulation_vectors=(
            "inherits sybil risk from usage driver",
            "inherits virtual-node risk from network driver",
        ),
        compatibility_tags=frozenset({"payment", "remittance", "network", "fx"}),
    ),
)


def get_driver(name: str) -> SupplyDriver | None:
    """Look up a driver by name. Returns None if not found."""
    for d in DRIVER_REGISTRY:
        if d.name == name:
            return d
    return None


def drivers_for_tags(tags: set[str]) -> list[SupplyDriver]:
    """Return all drivers whose compatibility_tags intersect with
    the given tag set, sorted deterministically by name."""
    matched = [d for d in DRIVER_REGISTRY if d.compatibility_tags & tags]
    return sorted(matched, key=lambda d: d.name)
