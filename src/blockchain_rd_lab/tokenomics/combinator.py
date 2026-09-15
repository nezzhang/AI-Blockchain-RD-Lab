"""§17/§18 mechanism combinator.

Combines stored candidate mechanisms with supply drivers using
tag-based semantic/economic compatibility — NOT random generation
(§18: "Do not generate combinations randomly only. Use semantic
similarity and economic compatibility.").

The combinator extracts tags from a candidate's description and
stored data, matches them against driver compatibility_tags, and
produces ranked TokenDesign candidates scored by fit quality.

r39: initial implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from blockchain_rd_lab.tokenomics.supply_drivers import (
    DRIVER_REGISTRY,
    SupplyDriver,
    drivers_for_tags,
)

# Words that signal economic/semantic affinity between a mechanism
# description and a supply driver. This is the "semantic similarity"
# §18 requires — a deterministic keyword overlap, not an LLM embedding.
_MECHANISM_KEYWORDS: dict[str, set[str]] = {
    "escrow": {"escrow", "retention", "hold", "lock", "collateral"},
    "fee": {"fee", "smoothing", "cost", "spread", "premium"},
    "fx": {"fx", "foreign exchange", "cross-border", "remittance",
           "corridor", "currency", "exchange rate"},
    "payment": {"payment", "transfer", "settlement", "disbursement"},
    "stability": {"stable", "anchor", "regime", "peg", "smooth",
                  "dampen", "absorb"},
    "network": {"network", "node", "peer", "p2p", "topology"},
    "insurance": {"insurance", "claim", "risk", "pool", "coverage"},
    "ai": {"ai", "agent", "automated", "machine learning", "model"},
}


def extract_mechanism_tags(description: str) -> set[str]:
    """Extract compatibility tags from a mechanism description using
    deterministic keyword matching. Lowercased, no regex surprises."""
    text = description.lower()
    tags: set[str] = set()
    for tag, keywords in _MECHANISM_KEYWORDS.items():
        for kw in keywords:
            # word-boundary match to avoid substring false positives
            if re.search(rf"\b{re.escape(kw)}\b", text):
                tags.add(tag)
                break
    return tags


@dataclass(frozen=True)
class TokenDesign:
    """One candidate token design: a mechanism paired with a supply driver.

    Attributes:
        mechanism_id: the candidate this design targets.
        mechanism_name: human-readable mechanism name.
        driver: the matched supply driver.
        tag_overlap: how many mechanism tags matched the driver.
        compatibility_score: 0.0-1.0, higher = better fit.
    """

    mechanism_id: str
    mechanism_name: str
    driver: SupplyDriver
    tag_overlap: int
    compatibility_score: float

    @property
    def design_id(self) -> str:
        """Deterministic identifier for this design."""
        return f"{self.mechanism_id}+{self.driver.name}"


def combine(
    mechanism_id: str,
    mechanism_name: str,
    description: str,
    *,
    max_designs: int = 5,
) -> list[TokenDesign]:
    """Produce ranked token designs for a mechanism.

    The combinator:
    1. Extracts semantic tags from the mechanism description.
    2. Finds all drivers whose compatibility_tags intersect.
    3. Scores each match by tag overlap / max possible overlap.
    4. Returns the top `max_designs` sorted by score descending,
       then by driver name ascending (deterministic tiebreak).

    If no tags match any driver, returns an empty list — the
    honest absence convention. The report layer renders this as
    "no compatible supply driver found" rather than forcing a
    random pairing (§18).
    """
    tags = extract_mechanism_tags(description)
    if not tags:
        return []

    matched = drivers_for_tags(tags)
    designs: list[TokenDesign] = []
    for driver in matched:
        overlap = len(tags & driver.compatibility_tags)
        # r40 (the lab's own audit, F2): the score was
        # overlap / max(|mechanism|, |driver|) — an asymmetric,
        # non-standard measure whose denominator is constant for
        # every driver smaller than the mechanism tag set, and
        # penalizes by breadth alone for larger ones (a broad
        # 8-tag driver matching 4 TIED a focused 4-tag driver
        # matching 3). Jaccard — intersection / union — is the symmetric
        # standard: unmatched tags on EITHER side reduce the
        # score, so focus and coverage both count.
        union = len(tags | driver.compatibility_tags)
        score = overlap / union if union else 0.0
        designs.append(TokenDesign(
            mechanism_id=mechanism_id,
            mechanism_name=mechanism_name,
            driver=driver,
            tag_overlap=overlap,
            compatibility_score=score,
        ))

    # Deterministic sort: score descending, then name ascending
    designs.sort(key=lambda d: (-d.compatibility_score, d.driver.name))
    return designs[:max_designs]


def combine_all_registered(
    mechanism_id: str,
    mechanism_name: str,
    description: str,
) -> list[TokenDesign]:
    """Like combine() but returns ALL compatible drivers, not capped.
    Used by the report layer to show the full compatibility landscape."""
    return combine(mechanism_id, mechanism_name, description, max_designs=len(DRIVER_REGISTRY))
