"""Idea normalization and de-duplication (Phase 1, deterministic code).

LLM proposes. Code tests. Evidence decides. — normalization and dedup are
pure, deterministic Python: no LLM in the loop (§2, §38 Phase 1).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from blockchain_rd_lab.config import DedupSettings, ResearchConfig, load_research
from blockchain_rd_lab.discovery import (
    DuplicateVerdict,
    IdeaDraft,
    NormalizedIdea,
)

# Words too generic to carry semantic signal for dedup.
_STOPWORDS = frozenset(
    (
        "a", "an", "and", "are", "as", "at", "be", "based", "by",
        "chain", "coin", "crypto", "data", "decentralized", "defi",
        "driven", "economic", "economics", "for", "from", "fund",
        "governed", "in", "into", "is", "it", "market", "mechanism",
        "money", "monetary", "new", "of", "on", "on-chain", "oracle",
        "protocol", "system", "that", "the", "this", "to", "token",
        "using", "via", "with",
    )
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _normalize_text(text: str) -> str:
    """Lowercase, split camelCase, strip punctuation to a token stream."""
    spaced = _CAMEL_RE.sub(" ", text)
    return spaced.replace("-", " ").replace("_", " ").lower()


def keyword_tokens(text: str) -> list[str]:
    """Ordered, de-duplicated keyword tokens (stopwords removed)."""
    seen: set[str] = set()
    out: list[str] = []
    for tok in _TOKEN_RE.findall(_normalize_text(text)):
        if tok in _STOPWORDS or len(tok) < 3 or tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def name_key(name: str) -> str:
    """Canonical name key: sorted significant tokens, space-joined."""
    return " ".join(sorted(keyword_tokens(name)))


def _shingles(tokens: list[str], size: int) -> set[tuple[str, ...]]:
    if len(tokens) < size:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def jaccard(a: set, b: set) -> float:
    """Jaccard similarity; both empty → 1.0 (identical emptiness)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class Normalizer:
    """Deterministic IdeaDraft → NormalizedIdea conversion."""

    def __init__(self, research_config: ResearchConfig | None = None) -> None:
        self.research = research_config or load_research()

    def normalize(self, draft: IdeaDraft, source_batch: str = "") -> NormalizedIdea:
        max_chars = self.research.discovery.max_description_chars
        description = " ".join(draft.description.split())[:max_chars]
        return NormalizedIdea(
            name=" ".join(draft.name.split()),
            name_key=name_key(draft.name),
            keywords=keyword_tokens(f"{draft.name} {draft.category} {draft.description}"),
            category=" ".join(draft.category.split()).lower(),
            domain=draft.domain.strip().lower(),
            description=description,
            core_mechanism=" ".join(draft.core_mechanism.split()),
            problem=" ".join(draft.problem.split()) if draft.problem else "",
            innovation_claim=(
                " ".join(draft.innovation_claim.split()) if draft.innovation_claim else ""
            ),
            inputs=[i.strip().lower() for i in draft.inputs if i.strip()],
            outputs=[o.strip().lower() for o in draft.outputs if o.strip()],
            oracle_required=draft.oracle_required,
            blockchain_required=draft.blockchain_required,
            token_required=draft.token_required,
            source_batch=source_batch,
        )

    def normalize_batch(
        self, batch: Iterable[IdeaDraft], source_batch: str = ""
    ) -> list[NormalizedIdea]:
        return [self.normalize(d, source_batch) for d in batch]


class Deduplicator:
    """Deterministic near-duplicate detection over keyword sets.

    Two signals (both pure code):
      1. Exact name-key collision → duplicate outright.
      2. Combined similarity = max(name shingle Jaccard, keyword Jaccard)
         vs thresholds from config/research.yaml.
    """

    def __init__(self, settings: DedupSettings | None = None) -> None:
        self.settings = settings or (load_research().dedup)

    def _name_similarity(self, a: NormalizedIdea, b: NormalizedIdea) -> float:
        size = max(1, self.settings.name_shingle_size)
        sa = _shingles(keyword_tokens(a.name), size)
        sb = _shingles(keyword_tokens(b.name), size)
        return jaccard(sa, sb)

    def _keyword_similarity(self, a: NormalizedIdea, b: NormalizedIdea) -> float:
        return jaccard(set(a.keywords), set(b.keywords))

    def similarity(self, a: NormalizedIdea, b: NormalizedIdea) -> float:
        """Overall similarity between two ideas."""
        name_sim = self._name_similarity(a, b)
        kw_sim = self._keyword_similarity(a, b)
        return max(name_sim, kw_sim)

    def check(
        self,
        candidate: NormalizedIdea,
        existing: Iterable[NormalizedIdea],
    ) -> DuplicateVerdict:
        """Best-match duplicate verdict for `candidate` vs stored ideas."""
        best: DuplicateVerdict | None = None
        for other in existing:
            if candidate.name_key and candidate.name_key == other.name_key:
                return DuplicateVerdict(
                    is_duplicate=True,
                    similarity=1.0,
                    matched_idea_id=other.idea_id,
                    matched_name=other.name,
                    reason="exact name-key collision",
                )
            sim = self.similarity(candidate, other)
            if best is None or sim > best.similarity:
                best = DuplicateVerdict(
                    is_duplicate=False,
                    similarity=sim,
                    matched_idea_id=other.idea_id,
                    matched_name=other.name,
                    reason="similarity",
                )
        if best is None:
            return DuplicateVerdict(is_duplicate=False, similarity=0.0)
        if best.similarity >= self.settings.exact_threshold:
            reason = f"similarity {best.similarity:.3f} >= exact threshold"
            return best.model_copy(update={"is_duplicate": True, "reason": reason})
        return best
