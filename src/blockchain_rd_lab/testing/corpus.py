"""Deterministic offline corpus generator (§24/§42).

§42's definition of success is `lab pipeline --count 100` producing the
full funnel offline. The hand-written fixture batches (16 ideas) cannot
supply that, so this module GENERATES the corpus deterministically:

- §24's 20 source domains, each with domain-specific mechanism
  templates (anchoring rule, control surface, measured quantity),
- a seeded PRNG picks + parameterizes templates so every generated
  mechanism is genuinely distinct (different anchor, control, and
  parameters — not dedup-defeating noise),
- output is IdeaDraft objects: the exact schema the Discovery Agent
  emits, so the normal normalize → dedup → store path gates everything
  exactly as in the LLM route (§2: code tests the proposal).

This is a TEST/DEMO corpus, NOT research output: it exercises the lab
at §42 scale offline. Novelty claims follow §12 discipline.
"""

from __future__ import annotations

from collections.abc import Iterator

# §24's 20 source domains with per-domain mechanism building blocks.
# Each domain contributes: mechanisms (name templates), the measured
# quantity (the anchor), and the control surface (what the rule moves).
from typing import Any

from blockchain_rd_lab.discovery import IdeaBatch, IdeaDraft

_DOMAINS: list[dict[str, Any]] = [
    {
        "name": "Monetary Economics",
        "mechanisms": ("Supply-Rule {anchor}", "{anchor} Steering Vault"),
        "anchors": ("GDP Deflator", "Broad Money Velocity", "Real Interest Gap"),
        "controls": ("monetary base", "reserve ratio"),
    },
    {
        "name": "Stablecoins",
        "mechanisms": ("{anchor} Reference Unit", "Dual-Collateral {control} Peg"),
        "anchors": ("CPI Basket", "Trade-Weighted FX", "Commodity Index"),
        "controls": ("mint throttle", "redemption fee"),
    },
    {
        "name": "Payments",
        "mechanisms": ("{anchor}-Routed Settlement", "Usage-Tiered {control} Channel"),
        "anchors": ("Interbank Rate", "Median Tx Fee", "Settlement Latency"),
        "controls": ("routing fee", "liquidity rebate"),
    },
    {
        "name": "Demographics",
        "mechanisms": ("{anchor} Dependency Rule", "Migration-Weighted {control}"),
        "anchors": ("Dependency Ratio", "Median Age", "Net Migration"),
        "controls": ("emission rate", "payout schedule"),
    },
    {
        "name": "AI Productivity",
        "mechanisms": ("{anchor} Denominated Debt", "Compute-Yield {control}"),
        "anchors": ("Model Inference Cost", "Training Compute", "AI Task Throughput"),
        "controls": ("lease rate", "collateral multiplier"),
    },
    {
        "name": "Energy",
        "mechanisms": ("{anchor}-Linked Supply", "Grid-Frequency {control}"),
        "anchors": ("Grid Frequency", "Renewable Output", "Nodal Price"),
        "controls": ("issuance", "staking yield"),
    },
    {
        "name": "Climate",
        "mechanisms": ("{anchor} Bond Curve", "Emission-Weighted {control}"),
        "anchors": ("Verified Emissions", "Carbon Intensity", "Habitat Acreage"),
        "controls": ("bond coupon", "fee burn"),
    },
    {
        "name": "Commodities",
        "mechanisms": ("{anchor} Vault Unit", "Harvest-Cycle {control}"),
        "anchors": ("Gold Lease Rate", "Oil Basis", "Harvest Yield"),
        "controls": ("vault fee", "delivery multiplier"),
    },
    {
        "name": "Insurance",
        "mechanisms": ("{anchor} Float Token", "Parametric {control} Pool"),
        "anchors": ("Cat Bond Spread", "Loss Ratio", "Flood Index"),
        "controls": ("premium float", "coverage multiple"),
    },
    {
        "name": "Prediction Markets",
        "mechanisms": ("{anchor} Forecast Unit", "Oracle-{control} Resolution"),
        "anchors": ("Forecast Error", "Event Odds", "Consensus Update"),
        "controls": ("resolution bond", "spread fee"),
    },
    {
        "name": "Labor",
        "mechanisms": ("{anchor}-Backed Escrow", "Task-Completion {control}"),
        "anchors": ("Wage Index", "Task Completion", "Skill Premium"),
        "controls": ("escrow release", "wage multiplier"),
    },
    {
        "name": "Global Trade",
        "mechanisms": ("{anchor} Corridor Token", "Trade-Lane {control}"),
        "anchors": ("Baltic Index", "Corridor Volume", "Tariff Rate"),
        "controls": ("corridor fee", "clearing multiplier"),
    },
    {
        "name": "Internet",
        "mechanisms": ("{anchor}-Priced Bandwidth", "Peering {control} Market"),
        "anchors": ("Transit Price", "Peering Ratio", "Packet Loss"),
        "controls": ("bandwidth fee", "peering rebate"),
    },
    {
        "name": "Biology",
        "mechanisms": ("{anchor} Royalty Stream", "Genomic {control} License"),
        "anchors": ("Sequence Value", "Trial Phase", "Patent Life"),
        "controls": ("royalty rate", "license fee"),
    },
    {
        "name": "Ecology",
        "mechanisms": ("{anchor} Credit Market", "Biodiversity {control}"),
        "anchors": ("Species Count", "Wetland Area", "Pollination Yield"),
        "controls": ("credit price", "restoration fund"),
    },
    {
        "name": "Game Theory",
        "mechanisms": ("{anchor} Commitment Game", "Escalation-{control} Rule"),
        "anchors": ("Cooperation Index", "Defection Rate", "Equilibrium Gap"),
        "controls": ("bond size", "penalty multiplier"),
    },
    {
        "name": "Information Theory",
        "mechanisms": ("{anchor}-Priced Storage", "Entropy {control} Ledger"),
        "anchors": ("Shannon Entropy", "KLD Divergence", "Channel Capacity"),
        "controls": ("storage fee", "compression reward"),
    },
    {
        "name": "Network Economics",
        "mechanisms": ("{anchor} Relay Market", "Metcalfe {control} Curve"),
        "anchors": ("Node Count", "Relay Uptime", "Betweenness Score"),
        "controls": ("relay fee", "uptime multiplier"),
    },
    {
        "name": "Financial Markets",
        "mechanisms": ("{anchor} Rebalance Rule", "Vol-Weighted {control}"),
        "anchors": ("VIX", "Swap Spread", "Liquidity Depth"),
        "controls": ("rebalance band", "margin multiplier"),
    },
    {
        "name": "Distributed Systems",
        "mechanisms": ("{anchor} Consensus Fee", "Finality-{control} Market"),
        "anchors": ("Block Interval", "Finality Delay", "Fork Rate"),
        "controls": ("consensus fee", "finality bond"),
    },
]


class _Mulberry32:
    """Small deterministic PRNG (same family as the Phase 4 generator)."""

    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = ((t ^ (t >> 15)) * t) & 0xFFFFFFFF
        t = (t ^ (t >> 7)) & 0xFFFFFFFF
        return ((t ^ (t >> 4)) & 0xFFFFFFFF) >> 0

    def pick(self, items: tuple[str, ...]) -> str:
        return items[self.next() % len(items)]


def _clamp_word(rng: _Mulberry32, low: float, high: float) -> float:
    span = int((high - low) * 1000)
    return round(low + (rng.next() % max(span, 1)) / 1000.0, 3)


def generate_draft(rng: _Mulberry32, domain: dict, index: int) -> IdeaDraft:
    """One distinct mechanism idea from a domain template."""
    mech_template = rng.pick(domain["mechanisms"])
    anchor = rng.pick(domain["anchors"])
    control = rng.pick(domain["controls"])
    # index guarantees name uniqueness across draws of the same template
    name = f"{mech_template.format(anchor=anchor, control=control.title())} {index:03d}"
    alpha = _clamp_word(rng, 0.1, 0.9)
    cap = _clamp_word(rng, 0.01, 0.10)

    oracle = "oracle-reported" if rng.next() % 2 == 0 else "self-reported"
    description = (
        f"A {domain['name'].lower()} mechanism where the {control} reacts to the "
        f"{anchor} as a {oracle} external quantity. Supply-side adjustments are "
        f"bounded so that no single report can move the {control} by more than "
        f"{cap:.1%} per step; the coupling strength is {alpha:.2f} of the measured "
        f"deviation from its long-run mean. When the {anchor} stalls, the rule "
        f"freezes and a governance vote is required to resume."
    )
    core = (
        f"S_t1 = S_t * (1 + clip(alpha * (X_t - X_smooth_t) / X_t, -cap, cap)); "
        f"X_smooth_t is an EMA of the {anchor} with a 0.8 weight; the {control} "
        f"adjusts only on confirmed reports, and {oracle} values older than one "
        f"period are discarded."
    )
    return IdeaDraft(
        name=name,
        category=domain["name"],
        domain=domain["name"],
        description=description,
        core_mechanism=core,
        problem=f"{domain['name']} mechanisms lack a rule that is verifiable and bounded.",
        innovation_claim=(
            "No substantially similar implementation was identified in the "
            "searched sources."
        ),
        inputs=[anchor, "Report Timestamp"],
        outputs=[f"Adjusted {control}", "Rule State"],
        oracle_required=(oracle == "oracle-reported"),
        blockchain_required=rng.next() % 3 != 0,  # §4: not everything needs a chain
        token_required=rng.next() % 2 == 0,
    )


def generate_corpus(count: int, seed: int = 24) -> Iterator[IdeaBatch]:
    """Yield IdeaBatch objects until `count` drafts are generated.

    Deterministic: the same (count, seed) always yields the same corpus.
    Batches of 5 (the configured per-batch size) cover the §34 loop.
    """
    if count < 1:
        return
    rng = _Mulberry32(seed)
    batch: list[IdeaDraft] = []
    for i in range(count):
        if i < len(_DOMAINS) * 3:
            # §24: guarantee every domain is visited before random draws
            domain = _DOMAINS[i % len(_DOMAINS)]
        else:
            domain = _DOMAINS[rng.next() % len(_DOMAINS)]
        batch.append(generate_draft(rng, domain, i))
        if len(batch) == 5:
            yield IdeaBatch(
                ideas=list(batch),
                source_agent="corpus-generator",
                domains_requested=[d["name"] for d in _DOMAINS],
            )
            batch = []
    if batch:
        yield IdeaBatch(
            ideas=list(batch),
            source_agent="corpus-generator",
            domains_requested=[d["name"] for d in _DOMAINS],
        )


def domain_names() -> list[str]:
    """The 20 §24 source domains covered by the generator."""
    return [d["name"] for d in _DOMAINS]
