"""LLM provider implementations (§30).

- MockLLMProvider: deterministic, offline (tests + Phase 0/1 plumbing).
- OpenAICompatProvider: any OpenAI-compatible chat completions endpoint
  (OpenAI, many local servers, compatible gateways) using only stdlib
  urllib — no SDK dependency. Registered under "openai" and "local".
- AnthropicProvider / GeminiProvider hooks: OpenAI-compatible gateways can
  cover them; native SDKs arrive when their phase needs them.

Configuration (config/lab.yaml `providers:` section):

    providers:
      openai:
        base_url: https://api.openai.com/v1      # or a local server URL
        model: gpt-4o-mini                        # default model name
        tier_models:                              # optional per-tier overrides
          cheap: gpt-4o-mini
          medium: gpt-4o-mini
          strong: gpt-4o
          strongest: gpt-4o

API keys are read from the environment only (§30: never hard-code keys).
"""

from __future__ import annotations

import contextlib
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from blockchain_rd_lab.agents.base import (
    LLMConnectionError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMValidationError,
    ModelTier,
)


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


class OpenAICompatProvider(LLMProvider):
    """Minimal OpenAI-compatible chat-completions provider (stdlib only).

    Works with OpenAI, local inference servers (llama.cpp, vLLM, Ollama's
    OpenAI endpoint, LM Studio, ...), and any compatible gateway. `tier_models`
    implements §31 model routing: cheap model for simple tasks, stronger
    models for finalists.
    """

    name = "openai"

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_key_env: str = "OPENAI_API_KEY",
        tier_models: dict[str, str] | None = None,
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 2.0,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.tier_models = dict(tier_models or {})
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.extra_headers = dict(extra_headers or {})

    def _resolve_model(self, tier: ModelTier) -> str:
        return self.tier_models.get(tier.value, self.model)

    def _headers(self) -> dict[str, str]:
        api_key = os.environ.get(self.api_key_env, "")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            **self.extra_headers,
        }
        return headers

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tier: ModelTier = ModelTier.MEDIUM,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        model = self._resolve_model(tier)
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        headers = self._headers()

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            if attempt > 0:
                time.sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                choice = data["choices"][0]
                text = choice["message"]["content"]
                usage = data.get("usage") or {}
                return LLMResponse(
                    text=text,
                    model=data.get("model", model),
                    provider=self.name,
                    prompt_tokens=int(usage.get("prompt_tokens", 0)),
                    completion_tokens=int(usage.get("completion_tokens", 0)),
                )
            except urllib.error.HTTPError as exc:
                detail = ""
                with contextlib.suppress(Exception):
                    detail = exc.read().decode("utf-8", errors="replace")[:500]
                last_error = LLMConnectionError(f"HTTP {exc.code}: {detail}")
                # 4xx (except 429) are not retryable.
                if 400 <= exc.code < 500 and exc.code != 429:
                    raise last_error from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = LLMConnectionError(f"connection error: {exc}")
            except (KeyError, IndexError, json.JSONDecodeError) as exc:
                last_error = LLMValidationError(f"malformed provider response: {exc}")
                raise last_error from exc

        assert last_error is not None
        raise last_error


class LocalLLMProvider(OpenAICompatProvider):
    """Local OpenAI-compatible server (Ollama/vLLM/LM Studio/llama.cpp)."""

    name = "local"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        model: str = "local-model",
        api_key_env: str = "LOCAL_LLM_API_KEY",
        tier_models: dict[str, str] | None = None,
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 2.0,
    ) -> None:
        super().__init__(
            base_url=base_url,
            model=model,
            api_key_env=api_key_env,
            tier_models=tier_models,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )


PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "mock": MockLLMProvider,
    "openai": OpenAICompatProvider,
    "local": LocalLLMProvider,
}


def get_provider(name: str, **kwargs: Any) -> LLMProvider:
    """Resolve a provider by name; unknown providers raise LLMError."""
    from blockchain_rd_lab.agents.base import LLMError

    cls = PROVIDER_REGISTRY.get(name)
    if cls is None:
        raise LLMError(f"Unknown LLM provider: {name!r}")
    return cls(**kwargs)
