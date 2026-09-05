"""§18 Mechanism Combinator tests: family mining, pair scoring, hints.

The combinator is pure deterministic code (§2) — no LLM anywhere. It
PROPOSES combinations; discovery still normalizes, dedups, and validates.
"""

from __future__ import annotations

import pytest

from blockchain_rd_lab.combinator import (
    CombinationHint,
    CombinatorSummary,
    MechanismFamily,
)
from blockchain_rd_lab.combinator.engine import (
    MechanismCombinator,
    combination_hint_text,
    is_hybrid,
)


def make_candidate(name: str, description: str, mechanism: str = ""):
    from blockchain_rd_lab.schemas import Candidate

    return Candidate(
        name=name,
        category="monetary",
        description=description,
        core_mechanism=mechanism or "supply rule",
    )


CLIMATE = make_candidate(
    "Carbon-Weighted Gas Fees",
    "Transaction fees reprice against verified carbon emission intensity.",
)
INSURANCE = make_candidate(
    "Prediction-Coupled Insurance Float",
    "Insurance float invests in prediction market liquidity pools.",
)
STABLE = make_candidate(
    "Merchant Settlement Channel",
    "Stablecoin payment routing with merchant liquidity collateral.",
)
ENERGY = make_candidate(
    "Grid Stability Coin",
    "Supply expands with verified renewable energy grid output.",
)
DEMOGRAPHIC = make_candidate(
    "Demographic Reserve Rule",
    "Monetary base tracks verified population and migration statistics.",
)


# ---------------------------------------------------------------------------
# Family mining
# ---------------------------------------------------------------------------


class TestMineFamilies:
    def test_mines_by_vocabulary(self):
        comb = MechanismCombinator()
        families = comb.mine_families([CLIMATE, STABLE, ENERGY])
        names = {f.family for f in families}
        assert "climate-driven" in names
        assert "stablecoin-infra" in names
        assert "energy-driven" in names

    def test_hybrids_join_multiple_families(self):
        # §17: hybrid mechanisms are the point — one candidate, several families
        hybrid = make_candidate(
            "Energy-Backed Insurance Float",
            "Renewable energy grid output collateralizes an insurance float.",
        )
        families = MechanismCombinator().mine_families([hybrid])
        names = {f.family for f in families}
        assert {"energy-driven", "insurance-driven"} <= names

    def test_no_signal_no_family(self):
        vague = make_candidate("Vague Thing", "It does stuff somehow.")
        assert MechanismCombinator().mine_families([vague]) == []

    def test_empty_corpus(self):
        assert MechanismCombinator().mine_families([]) == []

    def test_family_members_recorded(self):
        families = MechanismCombinator().mine_families([DEMOGRAPHIC])
        demo = next(f for f in families if f.family == "demographic-driven")
        assert DEMOGRAPHIC.id in demo.member_ids
        assert demo.keywords  # the triggering vocabulary is recorded


# ---------------------------------------------------------------------------
# Pair scoring (semantic bridge + economic compatibility)
# ---------------------------------------------------------------------------


class TestPairScoring:
    def _families(self, cands):
        return {f.family: f for f in MechanismCombinator().mine_families(cands)}

    def test_bridge_requires_shared_vocabulary(self):
        comb = MechanismCombinator()
        fams = self._families([CLIMATE, INSURANCE, STABLE])
        # climate and stablecoin share no vocabulary in this corpus
        assert comb.bridge_strength(fams["climate-driven"], fams["stablecoin-infra"]) == 0.0

    def test_compatibility_map_is_symmetric_ish(self):
        comb = MechanismCombinator()
        fams = self._families([CLIMATE, ENERGY])
        climate, energy = fams["climate-driven"], fams["energy-driven"]
        # climate-driven feeds energy-driven and vice versa (curated map)
        assert comb.compatibility(climate, energy) >= 0.5
        assert comb.compatibility(energy, climate) >= 0.5

    def test_scores_are_deterministic(self):
        cands = [CLIMATE, INSURANCE, STABLE, ENERGY, DEMOGRAPHIC]
        a = MechanismCombinator().propose(cands)
        b = MechanismCombinator().propose(cands)
        assert [(h.family_a, h.family_b, h.score) for h in a] == [
            (h.family_a, h.family_b, h.score) for h in b
        ]

    def test_incompatible_pairs_not_emitted(self):
        # §18: never random mashups — pairs below the gates are dropped
        hints = MechanismCombinator().propose([CLIMATE, STABLE], max_hints=10)
        emitted = {(h.family_a, h.family_b) for h in hints}
        assert ("climate-driven", "stablecoin-infra") not in emitted

    def test_max_hints_cap(self):
        cands = [CLIMATE, INSURANCE, STABLE, ENERGY, DEMOGRAPHIC]
        hints = MechanismCombinator().propose(cands, max_hints=1)
        assert len(hints) <= 1

    def test_strong_pairs_sorted_first(self):
        cands = [CLIMATE, INSURANCE, STABLE, ENERGY, DEMOGRAPHIC]
        hints = MechanismCombinator().propose(cands, max_hints=10)
        scores = [h.score for h in hints]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Hint objects + §17 hybrid tagging
# ---------------------------------------------------------------------------


class TestHints:
    def test_hint_text_names_both_families_and_rationale(self):
        hint = CombinationHint(
            family_a="insurance-driven",
            family_b="market-driven",
            bridge_strength=0.125,
            compatibility=0.61,
            score=0.37,
            rationale="float liquidity feeds market microstructure",
        )
        text = combination_hint_text(hint)
        assert "insurance-driven" in text and "market-driven" in text
        assert "float liquidity" in text

    def test_hybrid_detection(self):
        assert is_hybrid("Energy-Backed Hybrid Supply Rule")
        assert not is_hybrid("Demographic Reserve Rule")

    def test_family_hint_text_includes_examples(self):
        fam = MechanismFamily(
            family="energy-driven",
            member_ids=("cand-a", "cand-b"),
            keywords=frozenset({"energy", "grid"}),
        )
        text = fam.hint_text()
        assert "energy-driven" in text and "cand-a" in text

    def test_combinator_summary_counts(self):
        cands = [CLIMATE, INSURANCE, STABLE, ENERGY, DEMOGRAPHIC]
        summary = MechanismCombinator().run(cands)
        assert summary.families_found >= 3
        assert summary.pairs_considered >= 3
        assert summary.hints_emitted >= 0
        assert isinstance(summary, CombinatorSummary)


# ---------------------------------------------------------------------------
# Discovery integration: hints steer batches (§2: combinator proposes only)
# ---------------------------------------------------------------------------


class TestDiscoveryIntegration:
    def test_discover_accepts_hints(self, memory_db):
        """The service signature carries hints without changing behavior
        when none are given (backwards compatible)."""
        from blockchain_rd_lab.agents import MockLLMProvider
        from blockchain_rd_lab.discovery.service import DiscoveryService
        from blockchain_rd_lab.testing import fixture_responses

        provider = MockLLMProvider()
        for response in fixture_responses():
            provider.queue_response(response)
        service = DiscoveryService(provider, memory_db)
        summary_plain = service.discover(count=2, avoid_existing=False)

        provider2 = MockLLMProvider()
        for response in fixture_responses():
            provider2.queue_response(response)
        service2 = DiscoveryService(provider2, memory_db)
        summary_hinted = service2.discover(
            count=2,
            avoid_existing=False,
            combination_hints=["Combine a market-driven mechanism with a "
                               "stablecoin-infra mechanism."],
        )
        # Both store ideas through the same normalize/dedup path
        assert summary_plain.stored >= 1
        assert summary_hinted.stored >= 1

    def test_combinator_has_no_llm(self):
        """The engine imports no provider — pure code (§2)."""
        import inspect

        import blockchain_rd_lab.combinator.engine as engine_mod

        source = inspect.getsource(engine_mod)
        assert "LLMProvider" not in source
        assert "provider" not in source.replace("providers", "")


@pytest.mark.parametrize(
    "text,family",
    [
        ("carbon emission market", "climate-driven"),
        ("stablecoin merchant settlement", "stablecoin-infra"),
        ("renewable grid electricity", "energy-driven"),
    ],
)
def test_vocabulary_families(text, family):
    cand = make_candidate("X " + family, text)
    fams = {f.family for f in MechanismCombinator().mine_families([cand])}
    assert family in fams
