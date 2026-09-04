"""Agent abstraction (§8).

Every agent has: name, role, system_prompt, input_schema, output_schema,
model tier, temperature, tools, and execute(). Agents produce *structured*
outputs validated against Pydantic schemas — never arbitrary text that
controls deterministic parts of the system.

Providers live in `providers.py`; run records use `schemas.AgentRunRecord`.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from blockchain_rd_lab.schemas import AgentRunRecord, utcnow

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# Model routing tiers (§31)
# ---------------------------------------------------------------------------


class ModelTier(enum.StrEnum):
    """Cost-control routing tiers (§31)."""

    CHEAP = "cheap"
    MEDIUM = "medium"
    STRONG = "strong"
    STRONGEST = "strongest"


# ---------------------------------------------------------------------------
# Messages / errors
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Provider interface (§30)
# ---------------------------------------------------------------------------


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
        response = self.complete(
            messages, tier=tier, temperature=temperature, max_tokens=max_tokens, **kwargs
        )
        return parse_json_as(response.text, schema, source=self.name)

    def describe(self) -> dict[str, Any]:
        return {"provider": self.name}


def parse_json_as(text: str, schema: type[T], *, source: str = "provider") -> T:
    """Parse text as JSON and validate against a Pydantic schema.

    Tolerates markdown code fences around the JSON payload, a common
    provider behavior.
    """
    import json
    import re

    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, flags=re.DOTALL)
    if fence:
        stripped = fence.group(1)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMValidationError(
            f"[{source}] Provider returned non-JSON output: {exc}"
        ) from exc
    try:
        return schema.model_validate(data)
    except Exception as exc:
        raise LLMValidationError(f"[{source}] Schema validation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Agent tools (§37: explicit interfaces only)
# ---------------------------------------------------------------------------


class AgentTool(BaseModel):
    """A named capability an agent may use (explicit interfaces only, §37)."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent abstraction (§8)
# ---------------------------------------------------------------------------


class BaseAgent(ABC):
    """Abstract agent: structured input → structured output (§8).

    Subclasses (discovery, economist, red_team, ...) define their prompts and
    schemas and implement `build_prompt()`; `execute()` handles provider
    interaction, validation, and run-record persistence.
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
        from blockchain_rd_lab.agents.base import json_safe  # local re-use

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
                    "finished_at": utcnow(),
                }
            )
            if self.database is not None:
                self.database.save_agent_run(failed)
            raise
        record = started.model_copy(
            update={
                "status": "success",
                "finished_at": utcnow(),
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
