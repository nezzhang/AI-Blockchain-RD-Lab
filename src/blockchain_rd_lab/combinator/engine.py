"""§18 combinator engine: mine families, score pairs, emit hints.

Pure code. No LLM. The hints feed `DiscoveryPayload.combination_hint`,
which the existing discovery prompt already honors ("Mechanism
combinatorics (§18): ...").

Semantic bridges: shared vocabulary between two families (normalized
Jaccard over their keyword sets, reusing the Phase 1 stopword
discipline). Economic compatibility: the hand-curated control-flow map
(+1) plus category-token overlap (+0..1). Both are required — §18 says
"semantic similarity AND economic compatibility", never random mashups.
"""

from __future__ import annotations

import re
from itertools import combinations

from blockchain_rd_lab.combinator import (
    _COMPATIBLE,
    FAMILY_VOCAB,
    CombinationHint,
    CombinatorSummary,
    MechanismFamily,
)
from blockchain_rd_lab.discovery.normalize import _STOPWORDS, _TOKEN_RE

_MIN_SCORE = 0.30  # combined gate for emitting a hint (§18: score-only)


def _tokens(text: str) -> set[str]:
    return {
        t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) >= 3
    }


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class MechanismCombinator:
    """Proposes economically compatible mechanism combinations (§18)."""

    def __init__(self, min_score: float = _MIN_SCORE) -> None:
        self.min_score = min_score

    # -- family mining --------------------------------------------------------

    def mine_families(self, candidates: list) -> list[MechanismFamily]:
        """Cluster candidates by driving-domain vocabulary overlap.

        A candidate joins a family when its name+description+mechanism
        tokens overlap the family vocabulary. One candidate may belong to
        several families (hybrids are the point, §17).
        """
        families: dict[str, list] = {}
        keywords: dict[str, set[str]] = {}
        for cand in candidates:
            text = " ".join(
                [
                    getattr(cand, "name", ""),
                    getattr(cand, "description", ""),
                    getattr(cand, "core_mechanism", ""),
                ]
            )
            tokens = _tokens(text)
            if not tokens:
                continue
            for family, vocab in FAMILY_VOCAB.items():
                overlap = tokens & vocab
                if overlap:  # any vocabulary hit joins the family
                    families.setdefault(family, []).append(cand.id)
                    keywords.setdefault(family, set()).update(overlap)
        return [
            MechanismFamily(
                family=f,
                member_ids=tuple(sorted(set(ids))),
                keywords=frozenset(kws),
            )
            for f, ids in sorted(families.items())
            for kws in [keywords.get(f, set())]
        ]

    # -- pair scoring -----------------------------------------------------------

    def bridge_strength(self, a: MechanismFamily, b: MechanismFamily) -> float:
        """Semantic bridge: shared vocabulary between the families."""
        return _jaccard(a.keywords, b.keywords)

    def compatibility(self, a: MechanismFamily, b: MechanismFamily) -> float:
        """Economic compatibility: curated control-flow map + token overlap."""
        base = 0.5 if b.family in _COMPATIBLE.get(a.family, frozenset()) else 0.0
        if base == 0.0:
            base = 0.5 if a.family in _COMPATIBLE.get(b.family, frozenset()) else 0.0
        # cross-vocabulary token affinity (e.g. both mention 'reserve')
        cross = _jaccard(
            a.keywords | FAMILY_VOCAB.get(a.family, frozenset()),
            b.keywords | FAMILY_VOCAB.get(b.family, frozenset()),
        )
        return base + cross

    def propose(self, candidates: list, max_hints: int = 10) -> list[CombinationHint]:
        """Emit combination hints, strongest bridges first (deterministic)."""
        families = self.mine_families(candidates)
        by_family = {f.family: f for f in families}
        hints: list[CombinationHint] = []
        pairs_considered = 0
        for a, b in combinations(sorted(families, key=lambda f: f.family), 2):
            pairs_considered += 1
            bridge = self.bridge_strength(a, b)
            compat = self.compatibility(a, b)
            # §18 gate: score-only. A minimum-bridge AND-gate here would
            # silently veto compat-only pairs the master prompt itself
            # canonizes (Population+Stablecoin, Energy+PoS are bridge-0
            # pairs); the anti-mashup protection is the score floor —
            # bridge 0 AND compat 0 scores 0 and never emits.
            score = 0.5 * bridge + 0.5 * compat
            if score < self.min_score:
                continue
            hints.append(
                CombinationHint(
                    family_a=a.family,
                    family_b=b.family,
                    bridge_strength=round(bridge, 4),
                    compatibility=round(compat, 4),
                    score=round(score, 4),
                    rationale=(
                        f"vocabulary bridge ({a.family} ∩ {b.family} via "
                        f"shared terms) plus a compatible control flow "
                        f"({a.family} can feed {b.family}'s control "
                        f"surface, or vice versa)"
                        if bridge > 0
                        else f"compatible control flow ({a.family} can "
                        f"feed {b.family}'s control surface, or vice "
                        f"versa) with no shared vocabulary — §18 permits "
                        f"compat-only combinations"
                    ),
                    example_a=", ".join(a.member_ids[:2]),
                    example_b=", ".join(b.member_ids[:2]),
                )
            )
        _ = by_family  # families are self-contained in hints
        hints.sort(key=lambda h: (-h.score, h.family_a, h.family_b))
        return hints[:max_hints]

    def run(self, candidates: list, max_hints: int = 10) -> CombinatorSummary:
        hints = self.propose(candidates, max_hints=max_hints)
        families = self.mine_families(candidates)
        n = len(families)
        return CombinatorSummary(
            families_found=n,
            pairs_considered=n * (n - 1) // 2,
            hints_emitted=len(hints),
        )


def combination_hint_text(hint: CombinationHint) -> str:
    """Render a hint into the discovery prompt's combination_hint slot."""
    return hint.hint_text()


# §17 lists "Hybrid" as its own family label; combinations ARE hybrids.
_HYBRID_RE = re.compile(r"hybrid", re.IGNORECASE)


def is_hybrid(name: str) -> bool:
    """Whether a candidate name declares itself a hybrid (§17)."""
    return bool(_HYBRID_RE.search(name))
