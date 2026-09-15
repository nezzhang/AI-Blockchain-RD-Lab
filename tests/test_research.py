"""Phase 2 research tests: schemas, agents, service, filter, persistence."""

from __future__ import annotations

import json

import pydantic
import pytest

from blockchain_rd_lab.agents import MockLLMProvider
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.research import (
    CandidateBrief,
    EconomistReport,
    EvidenceLevel,
    FilterOutcome,
    MarketReport,
    PriorArtReport,
    ResearchSource,
)
from blockchain_rd_lab.research.agents import (
    EconomistAgent,
    MarketAgent,
    PriorArtAgent,
    build_research_report_fixture,
    fixture_research_responses,
)
from blockchain_rd_lab.research.service import ResearchFilter, ResearchService
from blockchain_rd_lab.schemas import (
    REQUIRED_NOVELTY_CLAIM,
    Candidate,
    CandidateStatus,
    NoveltyClass,
)


def make_candidate(**overrides) -> Candidate:
    base = dict(
        name="Carbon-Weighted Gas Fees",
        category="energy",
        description="Gas priced by verified carbon intensity of validator energy mix.",
        core_mechanism="GasPrice = base * (1 + beta * carbon_intensity_t).",
        problem="Blockchains ignore energy externalities",
    )
    base.update(overrides)
    return Candidate(**base)


MINIMAL_PRIOR_ART = dict(
    search_queries=["blockchain supply rule prior art"],
    findings=["No direct match found in searched sources."],
    conclusion="Insufficient evidence to classify novelty from the searched sources.",
)


class TestResearchSchemas:
    def test_prior_art_report_defaults(self):
        r = PriorArtReport(**MINIMAL_PRIOR_ART)
        assert r.novelty_class is NoveltyClass.E
        assert r.novelty_score == 5.0

    def test_bare_mock_digest_is_rejected(self):
        """§12/§2: garbage LLM output must never validate as evidence."""
        with pytest.raises(pydantic.ValidationError):
            PriorArtReport.model_validate(
                {"mock": True, "digest": "8270489"}
            )

    def test_class_d_requires_required_claim(self):
        with pytest.raises(pydantic.ValidationError):
            PriorArtReport(
                **{**MINIMAL_PRIOR_ART, "conclusion": "it is brand new!"},
                novelty_class=NoveltyClass.D,
            )

    def test_class_d_with_required_claim_ok(self):
        r = PriorArtReport(
            **{**MINIMAL_PRIOR_ART, "conclusion": REQUIRED_NOVELTY_CLAIM},
            novelty_class=NoveltyClass.D,
        )
        assert r.novelty_score == 8.5

    def test_forbidden_claim_always_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            PriorArtReport(
                **{**MINIMAL_PRIOR_ART, "conclusion": "Nobody has ever done this."},
                novelty_class=NoveltyClass.C,
            )

    def test_source_type_pattern(self):
        with pytest.raises(pydantic.ValidationError):
            ResearchSource(title="X", url="u", source_type="blogspam")
        ok = ResearchSource(title="UN Dataset", url="https://un.org/x", source_type="gov_dataset")
        assert ok.source_type == "gov_dataset"

    def test_dedupe_findings(self):
        r = PriorArtReport(
            **{**MINIMAL_PRIOR_ART, "findings": ["a", "a", "b"]},
        )
        assert r.findings == ["a", "b"]

    def test_brief_from_candidate(self):
        cand = make_candidate()
        brief = CandidateBrief.from_candidate(cand)
        assert brief.candidate_id == cand.id
        assert brief.oracle_required is False

    def test_evidence_level_enum(self):
        assert EvidenceLevel.FACT == "FACT"
        assert EvidenceLevel.HYPOTHESIS == "HYPOTHESIS"


class TestAgentsViaMock:
    def _provider_with(self, report: dict) -> MockLLMProvider:
        p = MockLLMProvider()
        p.queue_response(json.dumps(report))
        return p

    def test_prior_art_agent(self, memory_db):
        brief = CandidateBrief.from_candidate(make_candidate())
        fixture = build_research_report_fixture(brief, novelty_class="C")
        agent = PriorArtAgent(self._provider_with(fixture["prior_art"]), database=memory_db)
        out, record = agent.execute(brief)
        assert isinstance(out, PriorArtReport)
        assert out.novelty_class is NoveltyClass.C
        assert record.status == "success"

    def test_prior_art_agent_rejects_bad_payload(self):
        agent = PriorArtAgent(MockLLMProvider())
        with pytest.raises(TypeError):
            agent.build_prompt("not a brief")

    def test_economist_agent(self, memory_db):
        brief = CandidateBrief.from_candidate(make_candidate())
        fixture = build_research_report_fixture(brief)
        agent = EconomistAgent(self._provider_with(fixture["economist"]), database=memory_db)
        out, _ = agent.execute(brief)
        assert isinstance(out, EconomistReport)
        assert 0.0 <= out.economic_coherence_score <= 10.0

    def test_market_agent(self, memory_db):
        brief = CandidateBrief.from_candidate(make_candidate())
        fixture = build_research_report_fixture(brief)
        agent = MarketAgent(self._provider_with(fixture["market"]), database=memory_db)
        out, _ = agent.execute(brief)
        assert isinstance(out, MarketReport)
        assert out.customer.startswith("fixture")

    def test_prompts_encode_rules(self):
        brief = CandidateBrief.from_candidate(make_candidate())
        pa = PriorArtAgent(MockLLMProvider()).build_prompt(brief)
        assert "NEVER" in pa[0].content
        assert "substantially similar" in pa[0].content
        eco = EconomistAgent(MockLLMProvider()).build_prompt(brief)
        assert "FACT / INFERENCE / HYPOTHESIS" in eco[0].content or "FACT" in eco[0].content
        mkt = MarketAgent(MockLLMProvider()).build_prompt(brief)
        assert "NOT a customer" in mkt[0].content


class TestResearchService:
    def _mock_provider(self, briefs, **kwargs) -> MockLLMProvider:
        p = MockLLMProvider()
        for response in fixture_research_responses(briefs, **kwargs):
            p.queue_response(response)
        return p

    def test_research_candidate_full_flow(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        brief = CandidateBrief.from_candidate(cand)
        service = ResearchService(self._mock_provider([brief]), memory_db)
        result = service.research_candidate(cand)

        assert result.prior_art is not None
        assert result.economist is not None
        assert result.market is not None
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        # §11: GENERATED → RESEARCHING → PRIOR_ART_CHECKED
        assert stored.status is CandidateStatus.PRIOR_ART_CHECKED
        assert stored.novelty_class is NoveltyClass.E
        assert "novelty" in stored.scores
        assert "economic_coherence" in stored.scores
        assert "market_demand" in stored.scores
        # §12/§22: prior-art evidence persisted
        pa_rows = memory_db.list_prior_art(cand.id)
        assert len(pa_rows) == 1
        assert pa_rows[0]["similarity_class"] == "insufficient_evidence"
        # Offline fixture:// citations are hypotheses, not retrieved evidence.
        assert memory_db.list_sources() == []

    def test_fatal_concern_is_hypothesis_not_rejection(self, memory_db):
        """§2/§20: an Economist fatal bit needs deterministic confirmation."""
        cand = make_candidate(name="Guaranteed Death Spiral Token")
        memory_db.save_candidate(cand)
        brief = CandidateBrief.from_candidate(cand)
        service = ResearchService(
            self._mock_provider([brief], fatal=True), memory_db
        )
        result = service.research_candidate(cand)
        assert result.rejected is False
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.PRIOR_ART_CHECKED
        assert stored.has_confirmed_fatal_flaw is False
        assert len(stored.fatal_flaws) == 1
        assert stored.fatal_flaws[0].confirmed is False
        assert stored.fatal_flaws[0].identified_by == "economist"

    def test_agent_failure_isolated(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        provider = MockLLMProvider()
        provider.queue_response("<<<invalid prior art>>>")  # prior art fails
        brief = CandidateBrief.from_candidate(cand)
        for r in fixture_research_responses([brief])[1:]:
            provider.queue_response(r)
        service = ResearchService(provider, memory_db)
        result = service.research_candidate(cand)
        assert result.prior_art is None
        assert any("prior_art" in e for e in result.errors)
        # Economist/market results still applied
        assert result.economist is not None
        assert result.market is not None

    def test_research_all_failure_isolated(self, memory_db):
        c1 = make_candidate()
        c2 = make_candidate(name="Second Idea", category="payments")
        memory_db.save_candidate(c1)
        memory_db.save_candidate(c2)
        provider = MockLLMProvider()
        # First candidate: 3 failures; second candidate: 3 good reports
        for _ in range(3):
            provider.queue_response("<<<bad>>>")
        for r in fixture_research_responses(
            [CandidateBrief.from_candidate(c2)]
        ):
            provider.queue_response(r)
        service = ResearchService(provider, memory_db)
        results = service.research_all()
        assert len(results) == 2
        assert all(len(r.errors) == 3 for r in results if r.candidate_id == c1.id)
        assert results[1].prior_art is not None

    def test_class_d_fixture_uses_required_claim(self, memory_db):
        cand = make_candidate()
        brief = CandidateBrief.from_candidate(cand)
        fixture = build_research_report_fixture(brief, novelty_class="D")
        report = PriorArtReport.model_validate(fixture["prior_art"])
        assert report.novelty_class is NoveltyClass.D
        assert REQUIRED_NOVELTY_CLAIM in report.conclusion


class TestResearchFilter:
    def _setup(self, db: LabDatabase, classes: list[NoveltyClass]):
        from blockchain_rd_lab.schemas import novelty_score_for

        cands = []
        for i, cls in enumerate(classes):
            c = make_candidate(name=f"Candidate {i:03d}")
            c.novelty_class = cls
            c.novelty_score = novelty_score_for(cls)
            db.save_candidate(c)
            stored = db.get_candidate(c.id)
            assert stored is not None
            stored.transition(CandidateStatus.RESEARCHING)
            stored.transition(CandidateStatus.PRIOR_ART_CHECKED)
            db.save_candidate(stored)
            cands.append(stored)
        return cands

    def test_cuts_class_a_and_b(self, memory_db):
        self._setup(
            memory_db,
            [NoveltyClass.A, NoveltyClass.B, NoveltyClass.C, NoveltyClass.D, NoveltyClass.E],
        )
        outcome = ResearchFilter(target=10).apply(memory_db)
        assert outcome.considered == 5
        assert outcome.kept == 3
        assert outcome.rejected_class_a == 1
        assert outcome.rejected_class_b == 1
        remaining = memory_db.list_candidates(status=CandidateStatus.PRIOR_ART_CHECKED)
        assert len(remaining) == 3

    def test_overflow_rejected_beyond_target(self, memory_db):
        classes = [NoveltyClass.C] * 8
        self._setup(memory_db, classes)
        outcome = ResearchFilter(target=3).apply(memory_db)
        assert outcome.kept == 3
        assert outcome.rejected == 5
        assert len(outcome.kept_ids) == 3

    def test_ranking_prefers_novelty(self, memory_db):
        self._setup(
            memory_db,
            [NoveltyClass.E, NoveltyClass.D, NoveltyClass.C, NoveltyClass.E],
        )
        outcome = ResearchFilter(target=2).apply(memory_db)
        kept = [memory_db.get_candidate(i) for i in outcome.kept_ids]
        kept = [c for c in kept if c is not None]
        assert kept[0].novelty_class is NoveltyClass.D
        assert all(c.novelty_class is not NoveltyClass.A for c in kept)

    def test_rejected_is_terminal(self, memory_db):
        from blockchain_rd_lab.schemas import InvalidTransitionError

        self._setup(memory_db, [NoveltyClass.A, NoveltyClass.D])
        ResearchFilter(target=5).apply(memory_db)
        rejected = memory_db.list_candidates(status=CandidateStatus.REJECTED)
        assert len(rejected) == 1
        with pytest.raises(InvalidTransitionError):
            rejected[0].transition(CandidateStatus.GENERATED)

    def test_filter_outcome_defaults(self):
        fo = FilterOutcome()
        assert fo.target == 20
        assert fo.kept == 0


class TestPriorArtPersistence:
    def test_source_dedupe_by_url(self, memory_db):
        id1 = memory_db.save_source("T", "https://x.com/1", "paper")
        id2 = memory_db.save_source("T again", "https://x.com/1", "paper")
        assert id1 == id2
        assert len(memory_db.list_sources()) == 1


class TestFixtureGenerator:
    def test_fixture_research_responses_count(self):
        briefs = [CandidateBrief.from_candidate(make_candidate()) for _ in range(3)]
        responses = fixture_research_responses(briefs)
        assert len(responses) == 9  # 3 candidates x 3 agents
        for r in responses:
            json.loads(r)  # all valid JSON
