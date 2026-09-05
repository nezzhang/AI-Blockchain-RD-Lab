"""§31 cost control tests: token budgets, response cache, budget guard.

All deterministic, offline (§2): the guard is pure accounting code.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from blockchain_rd_lab.agents import MockLLMProvider
from blockchain_rd_lab.agents.base import LLMMessage, ModelTier
from blockchain_rd_lab.cost import (
    BudgetExceededError,
    BudgetGuard,
    BudgetState,
    ResponseCache,
    TokenBudget,
    UsageLedger,
)


def msgs(text: str = "hello world") -> list[LLMMessage]:
    return [LLMMessage(role="user", content=text)]


class ProviderWithTokens(MockLLMProvider):
    """Mock whose responses report deterministic token counts."""

    name = "mock-tokens"

    def __init__(self, tokens_per_call: int = 100) -> None:
        super().__init__()
        self.tokens_per_call = tokens_per_call
        self.real_calls = 0

    def complete(self, messages, *, tier=ModelTier.MEDIUM, **kwargs):
        self.real_calls += 1
        resp = super().complete(messages, tier=tier, **kwargs)
        return resp.model_copy(
            update={
                "prompt_tokens": self.tokens_per_call // 2,
                "completion_tokens": self.tokens_per_call // 2,
            }
        )


# ---------------------------------------------------------------------------
# TokenBudget
# ---------------------------------------------------------------------------


class TestTokenBudget:
    def test_charges_accumulate(self):
        from blockchain_rd_lab.agents.base import LLMResponse

        budget = TokenBudget(1_000)
        resp = LLMResponse(
            text="x", model="m", provider="p", prompt_tokens=60, completion_tokens=40
        )
        budget.charge(resp)
        assert budget.state.spent == 100
        assert budget.state.calls == 1
        assert budget.remaining == 900

    def test_fails_closed_when_exhausted(self):
        from blockchain_rd_lab.agents.base import LLMResponse

        budget = TokenBudget(100)
        resp = LLMResponse(
            text="x", model="m", provider="p", prompt_tokens=60, completion_tokens=40
        )
        # Spending exactly to the ceiling raises: the run is over.
        with pytest.raises(BudgetExceededError, match="§31"):
            budget.charge(resp)
        assert budget.state.spent == 100
        assert budget.state.exceeded

    def test_negative_budget_rejected(self):
        with pytest.raises(ValueError):
            TokenBudget(-1)

    def test_budget_state_model(self):
        state = BudgetState(budget=10, spent=4)
        assert state.remaining == 6
        assert not state.exceeded


# ---------------------------------------------------------------------------
# ResponseCache
# ---------------------------------------------------------------------------


class TestResponseCache:
    def test_roundtrip(self, tmp_path: Path):
        from blockchain_rd_lab.agents.base import LLMResponse

        cache = ResponseCache(tmp_path)
        resp = LLMResponse(
            text="cached!", model="m", provider="p", prompt_tokens=1, completion_tokens=2
        )
        cache.put("k", resp)
        hit = cache.get("k")
        assert hit is not None and hit.text == "cached!"

    def test_miss_returns_none(self, tmp_path: Path):
        assert ResponseCache(tmp_path).get("nope") is None

    def test_corrupt_entries_are_ignored(self, tmp_path: Path):
        cache = ResponseCache(tmp_path)
        (tmp_path / "bad.json").write_text("not json {{{", encoding="utf-8")
        assert cache.get("bad") is None

    def test_ttl_expiry(self, tmp_path: Path):
        from blockchain_rd_lab.agents.base import LLMResponse

        cache = ResponseCache(tmp_path, ttl_seconds=0.01)
        cache.put("k", LLMResponse(text="t", model="m", provider="p"))
        import time

        time.sleep(0.05)
        assert cache.get("k") is None


# ---------------------------------------------------------------------------
# BudgetGuard
# ---------------------------------------------------------------------------


class TestBudgetGuard:
    def test_charges_wrap_through(self, tmp_path: Path):
        inner = ProviderWithTokens(tokens_per_call=100)
        guard = BudgetGuard(inner, TokenBudget(1_000), ResponseCache(tmp_path))
        resp = guard.complete(msgs())
        assert resp.prompt_tokens + resp.completion_tokens == 100
        assert guard.budget.state.spent == 100

    def test_fails_closed_before_the_call(self, tmp_path: Path):
        inner = ProviderWithTokens(tokens_per_call=100)
        guard = BudgetGuard(inner, TokenBudget(150), ResponseCache(tmp_path))
        guard.complete(msgs())  # 100 spent — fine
        # Second call crosses the line: the provider IS hit, the charge raises.
        with pytest.raises(BudgetExceededError):
            guard.complete(msgs("different"))  # distinct: no cache hit
        assert inner.real_calls == 2
        # The THIRD call is refused BEFORE paying the provider.
        with pytest.raises(BudgetExceededError, match="before call"):
            guard.complete(msgs("third distinct request"))
        assert inner.real_calls == 2  # never hit

    def test_cache_hits_are_free(self, tmp_path: Path):
        inner = ProviderWithTokens(tokens_per_call=100)
        guard = BudgetGuard(inner, TokenBudget(1_000), ResponseCache(tmp_path))
        first = guard.complete(msgs("identical request"), temperature=0.5)
        second = guard.complete(msgs("identical request"), temperature=0.5)
        assert first.text == second.text
        assert inner.real_calls == 1  # only one real call
        assert guard.budget.state.cache_hits == 1
        assert guard.budget.state.spent == 100  # not 200

    def test_structured_roundtrip_with_cache(self, tmp_path: Path):
        from blockchain_rd_lab.formalization import MathModel
        from blockchain_rd_lab.research import CandidateBrief
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        inner = build_pipeline_provider()
        guard = BudgetGuard(inner, TokenBudget(1_000_000), ResponseCache(tmp_path))

        brief = CandidateBrief(
            candidate_id="cand-x",
            name="Test Mechanism",
            category="monetary",
            description="Supply follows an anchor.",
            core_mechanism="supply rule",
        )
        messages = [
            LLMMessage(
                role="user",
                content=f"CANDIDATE: {brief.name}\ncategory: {brief.category}\n"
                f"description: {brief.description}\ncore mechanism: "
                f"{brief.core_mechanism}\n",
            )
        ]
        out1 = guard.complete_structured(
            messages, schema=MathModel, tier=ModelTier.STRONG
        )
        assert isinstance(out1, MathModel)
        assert guard.budget.state.calls == 1
        # second identical call: cache hit, no extra spend
        guard.complete_structured(
            messages, schema=MathModel, tier=ModelTier.STRONG
        )
        assert guard.budget.state.calls == 1
        assert guard.budget.state.cache_hits == 1

    def test_structured_budget_fails_closed(self, tmp_path: Path):
        from blockchain_rd_lab.formalization import MathModel
        from blockchain_rd_lab.research import CandidateBrief
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        inner = build_pipeline_provider()
        guard = BudgetGuard(inner, TokenBudget(10), ResponseCache(tmp_path))
        brief = CandidateBrief(
            candidate_id="cand-x",
            name="Test Mechanism",
            category="monetary",
            description="Supply follows an anchor.",
            core_mechanism="supply rule",
        )
        messages = [
            LLMMessage(
                role="user",
                content=f"CANDIDATE: {brief.name}\ncategory: {brief.category}\n",
            )
        ]
        with pytest.raises(BudgetExceededError):
            guard.complete_structured(messages, schema=MathModel)


# ---------------------------------------------------------------------------
# UsageLedger
# ---------------------------------------------------------------------------


class TestUsageLedger:
    def test_from_budget_snapshot(self, tmp_path: Path):
        inner = ProviderWithTokens(tokens_per_call=50)
        guard = BudgetGuard(inner, TokenBudget(1_000), ResponseCache(tmp_path))
        guard.complete(msgs())
        ledger = UsageLedger.from_budget("run-1", guard.budget)
        assert ledger.spent == 50
        assert ledger.calls == 1
        assert ledger.cache_hits == 0

    def test_artifact_written(self, tmp_path: Path):
        ledger = UsageLedger(run_id="run-x", budget=100, spent=40, calls=2, cache_hits=1)
        out = tmp_path / "usage.json"
        ledger.to_artifact(out)
        data = json.loads(out.read_text())
        assert data["run_id"] == "run-x"
        assert data["spent"] == 40

    def test_saved_by_cache(self):
        ledger = UsageLedger(run_id="r", cache_hits=7)
        assert ledger.saved_by_cache == 7


# ---------------------------------------------------------------------------
# Pipeline integration: §31 enforcement through the §34 loop
# ---------------------------------------------------------------------------


class TestPipelineBudget:
    def test_pipeline_reports_usage_artifact(self, memory_db, tmp_path):
        from blockchain_rd_lab.pipeline import PipelineService
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        service = PipelineService(
            build_pipeline_provider(),
            memory_db,
            repo_root=tmp_path,
            research_config=None,
            token_budget=500_000,
        )
        summary = service.run(count=2, target=2, finalists=2)
        assert summary.completed
        ledger_path = tmp_path / "reports" / "usage-latest.json"
        assert ledger_path.exists()
        data = json.loads(ledger_path.read_text())
        assert data["budget"] == 500_000
        assert data["calls"] >= 1  # agent calls were made and counted

    def test_tiny_budget_stops_the_run(self, memory_db, tmp_path):
        """A 0-token budget fails closed: no candidate advances (§31)."""
        from blockchain_rd_lab.pipeline import PipelineService
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        service = PipelineService(
            build_pipeline_provider(),
            memory_db,
            repo_root=tmp_path,
            research_config=None,
            token_budget=0,
        )
        summary = service.run(count=2, target=2, finalists=2)
        # Budget refused every call; stages record errors but the run
        # itself completes structurally (§35 isolation).
        assert summary.completed
        discover = next(s for s in summary.stages if s.stage == "discover")
        assert discover.advanced == 0
