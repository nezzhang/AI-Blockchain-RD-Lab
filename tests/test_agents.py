"""Agent abstraction and mock LLM provider tests (§8, §30, §36)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from blockchain_rd_lab.agents import (
    AgentTool,
    BaseAgent,
    LLMMessage,
    LLMValidationError,
    MockLLMProvider,
    ModelTier,
    get_provider,
    json_safe,
)
from blockchain_rd_lab.schemas import Candidate


class IdeaPayload(BaseModel):
    domain: str


class IdeaOutput(BaseModel):
    name: str
    category: str


class StubAgent(BaseAgent):
    name = "stub"
    role = "testing"
    system_prompt = "You generate test ideas."
    input_schema = IdeaPayload
    output_schema = IdeaOutput
    model_tier = ModelTier.CHEAP
    temperature = 0.1

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        assert isinstance(payload, IdeaPayload)
        return [
            LLMMessage(role="system", content=self.system_prompt),
            LLMMessage(role="user", content=f"domain: {payload.domain}"),
        ]


class TestMockLLMProvider:
    def test_canned_response_fifo(self):
        provider = MockLLMProvider()
        provider.queue_response('{"name": "A", "category": "c"}')
        provider.queue_response('{"name": "B", "category": "c"}')
        r1 = provider.complete_structured([], schema=IdeaOutput)
        r2 = provider.complete_structured([], schema=IdeaOutput)
        assert (r1.name, r2.name) == ("A", "B")

    def test_default_response_is_valid_json(self):
        provider = MockLLMProvider()
        response = provider.complete([LLMMessage(role="user", content="hello")])
        assert response.provider == "mock"
        assert response.model == "mock-medium-model"

    def test_tier_affects_model_name(self):
        provider = MockLLMProvider()
        response = provider.complete([], tier=ModelTier.STRONGEST)
        assert response.model == "mock-strongest-model"

    def test_call_tracking(self):
        provider = MockLLMProvider()
        provider.complete([LLMMessage(role="user", content="x")], tier=ModelTier.CHEAP)
        assert provider.call_count == 1
        assert provider.calls[0]["tier"] == "cheap"

    def test_programmable_error(self):
        provider = MockLLMProvider()
        provider.queue_error(RuntimeError("provider down"))
        with pytest.raises(RuntimeError, match="provider down"):
            provider.complete([])
        # Error consumed; next call succeeds.
        assert provider.complete([]).provider == "mock"

    def test_structured_validation_error(self):
        provider = MockLLMProvider()
        provider.queue_response("not json at all")
        with pytest.raises(LLMValidationError):
            provider.complete_structured([], schema=IdeaOutput)

    def test_schema_mismatch_raises(self):
        provider = MockLLMProvider()
        provider.queue_response('{"wrong": "field"}')
        with pytest.raises(LLMValidationError):
            provider.complete_structured([], schema=IdeaOutput)


class TestProviderRegistry:
    def test_mock_registered(self):
        provider = get_provider("mock")
        assert isinstance(provider, MockLLMProvider)

    def test_unknown_provider_rejected(self):
        from blockchain_rd_lab.agents import LLMError

        with pytest.raises(LLMError):
            get_provider("nonexistent")


class TestBaseAgent:
    def test_execute_success_records_run(self, memory_db):
        provider = MockLLMProvider()
        provider.queue_response('{"name": "Test Idea", "category": "energy"}')
        agent = StubAgent(provider, database=memory_db)
        output, record = agent.execute(IdeaPayload(domain="energy"))
        assert output.name == "Test Idea"
        assert record.status == "success"
        assert record.agent_name == "stub"
        runs = list(memory_db.iter_agent_runs("stub"))
        assert len(runs) == 1
        assert runs[0].status == "success"

    def test_execute_failure_records_and_raises(self, memory_db):
        from blockchain_rd_lab.agents import LLMError

        provider = MockLLMProvider()
        provider.queue_response("<<<invalid>>>")
        agent = StubAgent(provider, database=memory_db)
        with pytest.raises(LLMError):
            agent.execute(IdeaPayload(domain="energy"))
        runs = list(memory_db.iter_agent_runs("stub"))
        assert len(runs) == 1
        assert runs[0].status == "error"
        assert runs[0].error is not None

    def test_agent_metadata(self):
        agent = StubAgent(MockLLMProvider())
        assert agent.name == "stub"
        assert agent.model_tier is ModelTier.CHEAP
        assert agent.output_schema is IdeaOutput


class TestAgentTool:
    def test_frozen(self):
        import pydantic

        tool = AgentTool(name="search_web", description="web search")
        with pytest.raises(pydantic.ValidationError):
            tool.name = "other"  # type: ignore[misc]


class TestJsonSafe:
    def test_handles_enums_and_datetimes(self, sample_candidate: Candidate):
        data = json_safe(sample_candidate.model_dump())
        # No exception and enums became plain values.
        assert isinstance(data["status"], str)
