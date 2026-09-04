"""Agent and LLM-provider abstractions (§8, §30).

Public API is re-exported from `base.py` and `providers.py`; import from
`blockchain_rd_lab.agents` directly as before.
"""

from __future__ import annotations

from blockchain_rd_lab.agents.base import (
    AgentTool,
    BaseAgent,
    LLMConnectionError,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMValidationError,
    ModelTier,
    json_safe,
    parse_json_as,
)
from blockchain_rd_lab.agents.providers import (
    PROVIDER_REGISTRY,
    LocalLLMProvider,
    MockLLMProvider,
    OpenAICompatProvider,
    get_provider,
)

__all__ = [
    "PROVIDER_REGISTRY",
    "AgentTool",
    "BaseAgent",
    "LLMConnectionError",
    "LLMError",
    "LLMMessage",
    "LLMProvider",
    "LLMResponse",
    "LLMValidationError",
    "LocalLLMProvider",
    "MockLLMProvider",
    "ModelTier",
    "OpenAICompatProvider",
    "get_provider",
    "json_safe",
    "parse_json_as",
]
