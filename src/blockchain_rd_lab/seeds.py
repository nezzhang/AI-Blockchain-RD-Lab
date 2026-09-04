"""Canonical experiment seed ideas (§25).

Seeded ideas enter the funnel as ORDINARY candidates with no privileges
(§24: "Do not prematurely select the Population idea. It must compete
fairly with all other candidates."). They are HYPOTHESES the lab must
attempt to prove or disprove.
"""

from __future__ import annotations

from blockchain_rd_lab.discovery import NormalizedIdea
from blockchain_rd_lab.discovery.normalize import keyword_tokens, name_key

POPULATION_MONEY = NormalizedIdea(
    name="Population-Linked Supply",
    name_key=name_key("Population-Linked Supply"),
    keywords=keyword_tokens(
        "Population-Linked Supply monetary economics token supply tracks verified "
        "global population changes births deaths migration"
    ),
    category="monetary economics",
    domain="demographics",
    description=(
        "Token supply expands and contracts with oracle-reported changes in "
        "verified global population. Each epoch, an oracle committee reports "
        "births, deaths, and net migration; the protocol mints or burns "
        "supply proportional to the reported delta. This is Experiment #001 "
        "(MASTER BUILD PROMPT §25): the lab must attempt to prove or disprove "
        "it, NOT assume it is a good idea."
    ),
    core_mechanism=(
        "S(t+1) = S(t) * (1 + alpha * dP/P) where dP/P is the oracle-reported "
        "relative population change per epoch and alpha is the coupling "
        "strength. Births, deaths, and migration feed dP. Unknowns the lab "
        "must investigate: alpha sensitivity, smoothing, lag, caps, floors, "
        "oracle frequency, revision handling, and conflicting-source disputes."
    ),
    problem=(
        "Fixed-supply tokens embed deflationary bias; discretionary inflation "
        "lacks an objective anchor. Population is a slow, externally verifiable "
        "macro variable — but whether that makes a sound monetary anchor is "
        "exactly what must be tested."
    ),
    innovation_claim=(
        "No substantially similar implementation was identified in the "
        "searched sources."
    ),
    inputs=["global_population", "births", "deaths", "migration"],
    outputs=["supply_delta", "epoch_supply"],
    oracle_required=True,
    blockchain_required=True,
    token_required=True,
    source_batch="seed-experiment-001",
)

EXPERIMENT_SEEDS: dict[str, list[NormalizedIdea]] = {
    "population-money": [POPULATION_MONEY],
}
