"""Agent abstraction (§8) and LLM provider abstraction (§30).

Every agent has: name, role, system_prompt, input_schema, output_schema,
model tier, temperature, tools, and execute(). Agents produce *structured*
outputs validated against Pydantic schemas — never arbitrary text that
controls deterministic parts of the system.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from blockchain_rd_lab.schemas import AgentRunRecord

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# LLM provider abstraction (§30)
# ---------------------------------------------------------------------------


class ModelTier(enum.StrEnum):
    """Cost-control routing tiers (§31)."""

    CHEAP = "cheap"
    MEDIUM = "medium"
    STRONG = "strong"
    STRONGEST = "strongest"


class LLMError(Exception):
    """Base error for LLM provider failures."""


class LLMConnectionError(LLMError):
    """Transient failure — retryable."""


class LLMResponseError(LLMError):
    """Provider returned an unusable response — retryable with backoff."""


class LLMValidationError(LLMError):
    """Structured output failed schema validation — not retryable as-is."""


class LLMMessage(BaseModel):
    """A single chat message."""

    model_config = ConfigDict(frozen=True)

    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class LLMResponse(BaseModel):
    """Normalized provider response."""

    model_config = ConfigDict(frozen=True)

    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider(ABC):
    """Abstract LLM provider (§30): OpenAI, Anthropic, Gemini, Local, Mock."""

    name: str = "abstract"

    @abstractmethod
    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tier: ModelTier = ModelTier.MEDIUM,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request and return the normalized response."""

    def complete_structured(
        self,
        messages: list[LLMMessage],
        *,
        schema: type[T],
        tier: ModelTier = ModelTier.MEDIUM,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> T:
        """Complete and validate the response against a Pydantic schema.

        Default implementation parses JSON from the response text; providers
        with native structured-output support override this.
        """
        import json

        response = self.complete(
            messages, tier=tier, temperature=temperature, max_tokens=max_tokens, **kwargs
        )
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise LLMValidationError(f"Provider returned non-JSON output: {exc}") from exc
        try:
            return schema.model_validate(data)
        except Exception as exc:  # pydantic.ValidationError and friends
            raise LLMValidationError(f"Schema validation failed: {exc}") from exc

    # Context introspection for cost accounting.
    def describe(self) -> dict[str, Any]:
        return {"provider": self.name}


# ---------------------------------------------------------------------------
# Mock provider (§38 Phase 0)
# ---------------------------------------------------------------------------


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider for tests and offline development.

    Behavior:
      - Returns programmable canned responses in FIFO order.
      - If no canned response matches, derives a deterministic placeholder
        from a hash of the prompt.
      - `complete_structured` validates the canned/derived payload against
        the requested schema, so schema-aware tests can inject fixtures.
      - Optionally raises a programmable exception to test error handling.
    """

    name = "mock"

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses: list[str] = list(responses or [])
        self._errors: list[BaseException] = []
        self.call_count: int = 0
        self.calls: list[dict[str, Any]] = []

    # -- test helpers --------------------------------------------------------

    def queue_response(self, text: str) -> None:
        self._responses.append(text)

    def queue_error(self, error: BaseException) -> None:
        self._errors.append(error)

    # -- LLMProvider ---------------------------------------------------------

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tier: ModelTier = ModelTier.MEDIUM,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_count += 1
        self.calls.append(
            {
                "messages": [m.model_dump() for m in messages],
                "tier": tier.value,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "kwargs": kwargs,
            }
        )
        if self._errors:
            raise self._errors.pop(0)
        if self._responses:
            text = self._responses.pop(0)
        else:
            # Deterministic placeholder derived from the prompt.
            digest = hash((tuple(m.content for m in messages), tier.value))
            text = f'{{"mock": true, "digest": "{abs(digest) % 10_000_000}"}}'
        return LLMResponse(
            text=text,
            model=f"mock-{tier.value}-model",
            provider=self.name,
            prompt_tokens=sum(len(m.content) for m in messages) // 4,
            completion_tokens=len(text) // 4,
        )


PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "mock": MockLLMProvider,
}


def get_provider(name: str, **kwargs: Any) -> LLMProvider:
    """Resolve a provider by name; unknown providers raise LLMError."""
    cls = PROVIDER_REGISTRY.get(name)
    if cls is None:
        raise LLMError(f"Unknown LLM provider: {name!r}")
    return cls(**kwargs)


# ---------------------------------------------------------------------------
# Agent abstraction (§8)
# ---------------------------------------------------------------------------


class AgentTool(BaseModel):
    """A named capability an agent may use (explicit interfaces only, §37)."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract agent: structured input → structured output (§8).

    Subclasses (discovery, economist, red_team, ...) define their prompts and
    schemas and implement `build_prompt()`; `execute()` handles provider
    interaction, validation, retries, and run-record persistence.
    """

    name: str = "agent"
    role: str = ""
    system_prompt: str = ""
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    model_tier: ModelTier = ModelTier.MEDIUM
    temperature: float = 0.7
    tools: list[AgentTool] = Field(default_factory=list)

    def __init__(
        self,
        provider: LLMProvider,
        database: Any | None = None,
    ) -> None:
        self.provider = provider
        self.database = database

    @abstractmethod
    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        """Construct the chat messages for a run."""

    def execute(self, payload: BaseModel) -> tuple[BaseModel, AgentRunRecord]:
        """Run the agent: provider call → schema validation → run record."""
        started = AgentRunRecord(
            agent_name=self.name,
            provider=self.provider.name,
            model=f"{self.provider.name}:{self.model_tier.value}",
            status="pending",
        )
        messages = self.build_prompt(payload)
        try:
            output = self.provider.complete_structured(
                messages,
                schema=self.output_schema,
                tier=self.model_tier,
                temperature=self.temperature,
            )
        except LLMError as exc:
            failed = started.model_copy(
                update={
                    "status": "error",
                    "error": str(exc),
                    "finished_at": AgentRunRecord.model_fields["finished_at"].get_default(),
                }
            )
            if self.database is not None:
                self.database.save_agent_run(failed)
            raise
        record = started.model_copy(
            update={
                "status": "success",
                "finished_at": AgentRunRecord.model_fields["finished_at"].get_default(),
                "output": json_safe(output.model_dump()),
            }
        )
        if self.database is not None:
            self.database.save_agent_run(record)
        return output, record


def json_safe(data: Any) -> Any:
    """Recursively convert values to JSON-serializable types."""
    if isinstance(data, dict):
        return {k: json_safe(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [json_safe(v) for v in data]
    if isinstance(data, enum.Enum):
        return data.value
    if hasattr(data, "isoformat"):
        return data.isoformat()
    return data
