"""Discovery module tests (Phase 1): agent, normalizer, deduplicator, service."""

from __future__ import annotations

import json

import pydantic
import pytest

from blockchain_rd_lab.agents import MockLLMProvider
from blockchain_rd_lab.config import DedupSettings, load_research
from blockchain_rd_lab.discovery import (
    DiscoveryRunSummary,
    DuplicateVerdict,
    IdeaBatch,
    IdeaDraft,
)
from blockchain_rd_lab.discovery.agent import DiscoveryAgent, DiscoveryPayload
from blockchain_rd_lab.discovery.normalize import (
    Deduplicator,
    Normalizer,
    jaccard,
    keyword_tokens,
)
from blockchain_rd_lab.discovery.service import DiscoveryService
from blockchain_rd_lab.schemas import CandidateStatus
from blockchain_rd_lab.seeds import POPULATION_MONEY


def make_draft(**overrides) -> IdeaDraft:
    base = dict(
        name="Energy-Usage Fee Market",
        category="energy",
        domain="energy",
        description=(
            "Transaction fees are priced by renewable grid load, shifting "
            "usage to surplus windows."
        ),
        core_mechanism=(
            "Fee = base_fee * f(grid_load); surplus periods discount fees, "
            "scarcity periods raise them."
        ),
        problem="Flat fees ignore real-time energy scarcity",
        inputs=["grid_load", "renewable_output"],
        outputs=["fee"],
    )
    base.update(overrides)
    return IdeaDraft(**base)


class TestIdeaDraft:
    def test_valid(self):
        d = make_draft()
        assert d.blockchain_required is True
        assert d.oracle_required is False

    def test_rejects_short_description(self):
        with pytest.raises(pydantic.ValidationError):
            make_draft(description="too short")

    def test_rejects_empty_name(self):
        with pytest.raises(pydantic.ValidationError):
            make_draft(name="  ")


class TestNormalizer:
    def test_keywords_and_name_key(self):
        norm = Normalizer(load_research())
        n = norm.normalize(make_draft())
        assert "energy" in n.keywords
        assert "fee" in n.keywords
        assert n.name_key == " ".join(sorted(keyword_tokens("Energy-Usage Fee Market")))
        assert n.category == "energy"
        assert n.domain == "energy"

    def test_to_candidate(self):
        norm = Normalizer(load_research())
        cand = norm.normalize(make_draft()).to_candidate()
        assert cand.status == CandidateStatus.GENERATED
        assert cand.source_agent == "discovery"
        assert cand.oracle_required is False
        assert "energy" in cand.category

    def test_whitespace_collapsed(self):
        norm = Normalizer(load_research())
        n = norm.normalize(make_draft(description="alpha beta\n  gamma   delta epsilon zeta"))
        assert "alpha beta gamma delta epsilon zeta" in n.description


class TestDeduplicator:
    def test_exact_name_key_collision(self):
        norm = Normalizer(load_research())
        dedup = Deduplicator(load_research().dedup)
        a = norm.normalize(make_draft())
        b = norm.normalize(make_draft(name="Fee Market Energy Usage"))  # same tokens
        verdict = dedup.check(b, [a])
        assert verdict.is_duplicate
        assert verdict.reason == "exact name-key collision"

    def test_identical_text_is_duplicate(self):
        norm = Normalizer(load_research())
        dedup = Deduplicator(load_research().dedup)
        a = norm.normalize(make_draft())
        b = norm.normalize(make_draft())
        verdict = dedup.check(b, [a])
        assert verdict.is_duplicate
        assert verdict.similarity >= 0.95

    def test_different_idea_not_duplicate(self):
        norm = Normalizer(load_research())
        dedup = Deduplicator(load_research().dedup)
        a = norm.normalize(make_draft())
        b = norm.normalize(
            make_draft(
                name="Insurance Mutual Backstop",
                category="insurance",
                domain="insurance",
                description=(
                    "A mutual insurance pool where premiums are set by "
                    "realized claim history on-chain."
                ),
                core_mechanism=(
                    "Premium = expected_claims * loading; collateral pooled by stakers."
                ),
                inputs=["claim_history"],
                outputs=["premium"],
            )
        )
        verdict = dedup.check(b, [a])
        assert not verdict.is_duplicate

    def test_near_duplicate_flagged(self):
        norm = Normalizer(load_research())
        dedup = Deduplicator(DedupSettings(exact_threshold=0.95, near_threshold=0.60))
        a = norm.normalize(make_draft())
        b = norm.normalize(
            make_draft(
                description=(
                    "Transaction fees priced by renewable energy grid load; surplus "
                    "windows discount fees while scarcity windows raise them."
                )
            )
        )
        sim = dedup.similarity(a, b)
        assert sim >= 0.60, f"expected near-duplicate signal, got {sim:.3f}"

    def test_empty_stored(self):
        norm = Normalizer(load_research())
        dedup = Deduplicator(load_research().dedup)
        a = norm.normalize(make_draft())
        verdict = dedup.check(a, [])
        assert verdict == DuplicateVerdict(is_duplicate=False, similarity=0.0)


class TestJaccard:
    def test_basics(self):
        assert jaccard({1, 2}, {1, 2}) == 1.0
        assert jaccard(set(), set()) == 1.0
        assert jaccard({1}, set()) == 0.0
        # {1,2,3} ∩ {3,4} = {3}; union = {1,2,3,4} → 1/4
        assert jaccard({1, 2, 3}, {3, 4}) == pytest.approx(0.25)


class TestDiscoveryAgent:
    def test_structured_output_via_mock(self, memory_db):
        batch = IdeaBatch(
            ideas=[make_draft(), make_draft(name="Labor Escrow Market", category="labor")],
            domains_requested=["energy", "labor"],
        )
        provider = MockLLMProvider()
        provider.queue_response(json.dumps({"ideas": [i.model_dump() for i in batch.ideas]}))
        agent = DiscoveryAgent(provider, database=memory_db, research_config=load_research())
        out, record = agent.execute(DiscoveryPayload(count=2))
        assert isinstance(out, IdeaBatch)
        assert len(out.ideas) == 2
        assert record.status == "success"

    def test_prompt_content(self):
        agent = DiscoveryAgent(MockLLMProvider(), research_config=load_research())
        msgs = agent.build_prompt(DiscoveryPayload(count=3, domains=["energy"]))
        assert msgs[0].role == "system"
        assert "MECHANISMS" in msgs[0].content
        assert "energy" in msgs[1].content
        assert "3" in msgs[1].content

    def test_forbidden_novelty_language_in_prompt(self):
        agent = DiscoveryAgent(MockLLMProvider(), research_config=load_research())
        msgs = agent.build_prompt(DiscoveryPayload(count=1))
        assert "NEVER say" in msgs[0].content
        assert "substantially similar" in msgs[0].content


class TestDiscoveryService:
    def _service(self, memory_db, drafts):
        provider = MockLLMProvider()
        for d in drafts:
            batch = IdeaBatch(ideas=[d] if isinstance(d, IdeaDraft) else d)
            provider.queue_response(json.dumps({"ideas": [i.model_dump() for i in batch.ideas]}))
        return DiscoveryService(
            provider, memory_db, research_config=load_research(), ideas_dir=None
        )

    def test_end_to_end_store_and_dedup(self, memory_db):
        a = make_draft()
        a_dup = make_draft(name="Energy Usage Fee Market")  # same name tokens
        b = make_draft(
            name="Prediction-Weighted Premiums",
            category="prediction markets",
            description="Insurance premiums reprice by prediction market odds each epoch.",
            core_mechanism="Premium(t+1) = Premium(t) * g(oracle odds)",
            inputs=["market_odds"], outputs=["premium"],
        )
        service = self._service(memory_db, [a, a_dup, b])
        summary = service.discover(count=3, avoid_existing=True)

        assert summary.generated == 3
        assert summary.stored == 2
        assert summary.duplicates_removed == 1
        assert len(memory_db.list_candidates()) == 2

    def test_llm_failure_does_not_crash(self, memory_db):
        provider = MockLLMProvider()
        provider.queue_response("not valid json <<<")
        service = DiscoveryService(provider, memory_db, research_config=load_research())
        summary = service.discover(count=5)
        assert summary.failed_batches == 1
        assert summary.stored == 0
        assert memory_db.count_candidates() == 0

    def test_seed_competes_fairly(self, memory_db):
        # §24: the Population seed must dedup like any other idea.
        from blockchain_rd_lab.seeds import EXPERIMENT_SEEDS

        seeds = EXPERIMENT_SEEDS["population-money"]
        provider = MockLLMProvider()
        near_dup = IdeaDraft(
            name="Population-Linked Supply Mechanism",
            category="monetary economics",
            domain="demographics",
            description=(
                "Token supply tracks verified global population changes through "
                "oracle-reported births, deaths, and migration."
            ),
            core_mechanism="Supply expands with population growth via oracle reports.",
            inputs=["population"], outputs=["supply"],
        )
        provider.queue_response(json.dumps({"ideas": [near_dup.model_dump()]}))
        memory_db.save_candidate(seeds[0].to_candidate())
        service = DiscoveryService(provider, memory_db, research_config=load_research())
        summary = service.discover(count=1, avoid_existing=True)
        assert summary.stored == 0
        assert summary.duplicates_removed == 1


class TestSeedExperiment:
    def test_population_money_seed_shape(self):
        assert POPULATION_MONEY.domain == "demographics"
        assert POPULATION_MONEY.oracle_required is True
        assert "Experiment #001" in POPULATION_MONEY.description
        cand = POPULATION_MONEY.to_candidate()
        assert cand.status == CandidateStatus.GENERATED
        assert cand.novelty_score == 5.0  # class E until prior-art research

    def test_discovery_summary_defaults(self):
        s = DiscoveryRunSummary()
        assert s.generated == 0 and s.stored == 0


class TestModelTierRouting:
    def test_provider_registry(self):
        from blockchain_rd_lab.agents import PROVIDER_REGISTRY, get_provider

        assert "openai" in PROVIDER_REGISTRY
        assert "local" in PROVIDER_REGISTRY
        p = get_provider("local")
        assert p.name == "local"
