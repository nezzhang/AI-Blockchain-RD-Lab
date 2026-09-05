"""§18 Mechanism Combinator: an engine that proposes mechanism COMBINATIONS.

Combination ideas come from semantic similarity and economic compatibility
— never random mashups. The engine is pure, deterministic code:

1. It mines the stored candidate corpus for pairwise mechanism families
   (name + category + core-mechanism keywords).
2. It scores every cross-family pair by semantic bridge strength
   (shared vocabulary) and economic complementarity (one family's
   output domain can feed the other's control domain).
3. It emits CombinationHints that the Discovery Agent turns into
   combination ideas via the existing `combination_hint` prompt path.

§2 discipline: the combinator PROPOSES; discovery normalizes, dedups,
and validates as usual. The combinator decides nothing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Mechanism family vocabulary: domain → the token families that signal it.
# Deterministic, hand-curated from §17's supply-lab list and §16's
# stablecoin track. Extended freely; absence of a family = no signal.
FAMILY_VOCAB: dict[str, frozenset[str]] = {
    "market-driven": frozenset({"market", "price", "float", "volatility", "trade"}),
    "usage-driven": frozenset({"usage", "fee", "gas", "activity", "tx", "volume"}),
    "economic-driven": frozenset({"gdp", "inflation", "output", "interest", "demand"}),
    "demographic-driven": frozenset({"demographic", "population", "birth", "migration"}),
    "productivity-driven": frozenset({"productivity", "ai", "compute", "hashrate", "labor"}),
    "energy-driven": frozenset({"energy", "power", "grid", "electricity", "renewable"}),
    "climate-driven": frozenset({"climate", "carbon", "emission", "weather", "habitat"}),
    "commodity-driven": frozenset({"commodity", "gold", "oil", "reserve", "harvest"}),
    "insurance-driven": frozenset({"insurance", "float", "premium", "risk", "coverage"}),
    "prediction-driven": frozenset({"prediction", "forecast", "market", "oracle", "event"}),
    "network-driven": frozenset({"network", "node", "staking", "relay", "peer"}),
    "stablecoin-infra": frozenset({
        "stablecoin", "settlement", "payment", "fx", "liquidity",
        "collateral", "routing", "merchant", "channel", "wallet",
    }),
    "governance": frozenset({"governance", "vote", "council", "treasury", "parameter"}),
    "oracle-design": frozenset({"oracle", "report", "feed", "attestation", "witness"}),
}

# Economic compatibility: control flows that make mechanistic sense.
# (upstream family feeds its measured quantity into downstream control)
_COMPATIBLE: dict[str, frozenset[str]] = {
    "market-driven": frozenset({"stablecoin-infra", "governance", "usage-driven"}),
    "usage-driven": frozenset({"market-driven", "governance", "stablecoin-infra"}),
    "economic-driven": frozenset({"market-driven", "governance", "stablecoin-infra"}),
    "demographic-driven": frozenset({"economic-driven", "governance", "stablecoin-infra"}),
    "productivity-driven": frozenset({"economic-driven", "market-driven", "usage-driven"}),
    "energy-driven": frozenset({"market-driven", "usage-driven", "climate-driven"}),
    "climate-driven": frozenset({"energy-driven", "commodity-driven", "governance"}),
    "commodity-driven": frozenset({"market-driven", "stablecoin-infra", "economic-driven"}),
    "insurance-driven": frozenset({"prediction-driven", "market-driven", "stablecoin-infra"}),
    "prediction-driven": frozenset({"oracle-design", "market-driven", "insurance-driven"}),
    "network-driven": frozenset({"usage-driven", "governance", "market-driven"}),
    "stablecoin-infra": frozenset({"oracle-design", "governance", "market-driven"}),
    "governance": frozenset({"market-driven", "stablecoin-infra"}),
    "oracle-design": frozenset({"stablecoin-infra", "prediction-driven", "market-driven"}),
}


class MechanismFamily(BaseModel):
    """A cluster of stored candidates sharing a driving-domain vocabulary."""

    model_config = ConfigDict(frozen=True)

    family: str
    member_ids: tuple[str, ...] = Field(default_factory=tuple)
    keywords: frozenset[str] = Field(default_factory=frozenset)

    def hint_text(self) -> str:
        ids = ", ".join(self.member_ids[:3])
        kws = ", ".join(sorted(self.keywords)[:6])
        return f"{self.family} (e.g. {ids}; vocabulary: {kws})"


class CombinationHint(BaseModel):
    """A proposed combination for the Discovery Agent (§18)."""

    model_config = ConfigDict(frozen=True)

    family_a: str
    family_b: str
    bridge_strength: float
    compatibility: float
    score: float
    rationale: str
    example_a: str = ""
    example_b: str = ""

    def hint_text(self) -> str:
        return (
            f"Combine a {self.family_a} mechanism with a {self.family_b} "
            f"mechanism. Economic bridge: {self.rationale}"
        )


class CombinatorSummary(BaseModel):
    """Outcome of one combinator run."""

    model_config = ConfigDict(validate_assignment=True)

    families_found: int = 0
    pairs_considered: int = 0
    hints_emitted: int = 0
