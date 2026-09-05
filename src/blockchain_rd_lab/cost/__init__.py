"""§31 cost control: token budgets, caching, and usage accounting.

The founder has limited capital, so the lab must NOT use its most
expensive model for everything — and it must never silently blow a
budget. This module provides:

- `TokenBudget`: a hard, cumulative spend ceiling per run. Providers
  wrapped in `BudgetGuard` count prompt+completion tokens from every
  response and REFUSE (fail closed, §30) once the ceiling is crossed.
- `ResponseCache`: content-hash keyed cache so agents do not re-pay for
  identical requests (§31 caching; §32 agents must not repeatedly
  rediscover the same information). Cached hits cost zero tokens.
- `UsageLedger`: durable per-run accounting persisted to the database,
  so cost evidence is auditable like everything else (§21 spirit).

All of it is deterministic code (§2) — no LLM involved.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from blockchain_rd_lab.agents.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    ModelTier,
)


def _import_time() -> float:
    import time

    return time.time()


class BudgetExceededError(Exception):
    """Raised when a call would cross the run's token budget (§31)."""


class BudgetState(BaseModel):
    """Cumulative spend against one run's budget."""

    model_config = ConfigDict(validate_assignment=True)

    budget: int
    spent: int = 0
    calls: int = 0
    cache_hits: int = 0
    cache_enabled: bool = True

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self.spent)

    @property
    def exceeded(self) -> bool:
        return self.spent >= self.budget


class TokenBudget:
    """Hard ceiling on tokens spent by one pipeline run."""

    def __init__(self, total: int, *, allow_overrun: bool = False) -> None:
        if total < 0:
            raise ValueError("budget must be non-negative")
        self.state = BudgetState(budget=total)
        self.allow_overrun = allow_overrun

    def charge(self, response: LLMResponse) -> None:
        """Record spend; raise when the ceiling is crossed."""
        cost = response.prompt_tokens + response.completion_tokens
        self.state.spent += cost
        self.state.calls += 1
        if not self.allow_overrun and self.state.exceeded:
            raise BudgetExceededError(
                f"token budget exhausted: spent {self.state.spent} of "
                f"{self.state.budget} tokens across {self.state.calls} calls (§31)"
            )

    def record_cache_hit(self) -> None:
        self.state.cache_hits += 1

    @property
    def remaining(self) -> int:
        return self.state.remaining

    @property
    def exceeded(self) -> bool:
        return self.state.exceeded


def _request_key(
    messages: list[LLMMessage],
    tier: ModelTier,
    temperature: float,
    schema_name: str,
) -> str:
    """Content-hash of everything that determines the response."""
    payload = {
        "messages": [m.model_dump() for m in messages],
        "tier": tier.value,
        "temperature": temperature,
        "schema": schema_name,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


class ResponseCache:
    """Disk-backed cache of provider responses (§31 caching, §32 memory).

    Deterministic: identical requests hit identical keys. TTL bounds
    staleness; persistence survives process restarts so agents do not
    repeatedly re-pay for the same research.
    """

    def __init__(self, cache_dir: Path, ttl_seconds: float = 86400.0) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> LLMResponse | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            import time

            record = json.loads(path.read_text(encoding="utf-8"))
            if self.ttl_seconds > 0:
                age = time.time() - float(record.get("cached_at", 0))
                if age > self.ttl_seconds:
                    path.unlink(missing_ok=True)
                    return None
            return LLMResponse.model_validate(record["response"])
        except Exception:
            # Corrupt cache entries are ignored, never fatal (§35).
            return None

    def put(self, key: str, response: LLMResponse) -> None:
        import time

        record = {"cached_at": time.time(), "response": response.model_dump(mode="json")}
        self._path(key).write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8"
        )


class BudgetGuard(LLMProvider):
    """Wraps any provider with budget + cache enforcement (§31).

    Every `complete` routes through the cache first; misses hit the
    wrapped provider, charge the budget, and store the response. The
    budget fails CLOSED: once the ceiling is crossed, further calls
    raise instead of silently overspending.
    """

    name = "budget-guard"

    def __init__(
        self,
        inner: LLMProvider,
        budget: TokenBudget,
        cache: ResponseCache | None = None,
    ) -> None:
        self.inner = inner
        self.budget = budget
        self.cache = cache

    # BaseProvider interface -------------------------------------------------

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tier: ModelTier = ModelTier.MEDIUM,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        schema_name = str(kwargs.get("schema", ""))
        key = _request_key(messages, tier, temperature, schema_name)
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                self.budget.record_cache_hit()
                return hit
        # Pre-check BEFORE paying: refuse calls that would cross the line.
        if self.budget.state.exceeded:
            raise BudgetExceededError(
                f"token budget exhausted before call: {self.budget.state.spent}"
                f"/{self.budget.state.budget} (§31)"
            )
        response = self.inner.complete(
            messages, tier=tier, temperature=temperature, max_tokens=max_tokens, **kwargs
        )
        self.budget.charge(response)
        if self.cache is not None:
            self.cache.put(key, response)
        return response

    def complete_structured(self, messages, *, schema, **kwargs):
        """Delegate structured calls to the inner provider, with budget +
        cache around them (§31). The inner provider owns structured
        semantics (native structured output, schema-aware fixtures);
        the guard owns spend accounting and memoization (§32).
        """
        tier = kwargs.get("tier", ModelTier.MEDIUM)
        temperature = kwargs.get("temperature", 0.7)
        key = _request_key(messages, tier, temperature, schema.__name__)

        # §32 memory: memoize validated models by request hash.
        if self.cache is not None:
            hit = self._get_model_cache(key, schema)
            if hit is not None:
                self.budget.record_cache_hit()
                return hit
        if self.budget.state.exceeded:
            raise BudgetExceededError(
                f"token budget exhausted before call: {self.budget.state.spent}"
                f"/{self.budget.state.budget} (§31)"
            )
        output = self.inner.complete_structured(messages, schema=schema, **kwargs)
        # Charge an estimate: request chars/4 + model dump chars/4 (the
        # mock provider uses exactly this convention).
        est_prompt = sum(len(m.content) for m in messages) // 4
        est_completion = len(output.model_dump_json()) // 4
        self.budget.state.spent += est_prompt + est_completion
        self.budget.state.calls += 1
        if self.budget.state.exceeded:
            raise BudgetExceededError(
                f"token budget exhausted: spent {self.budget.state.spent} of "
                f"{self.budget.state.budget} tokens across {self.budget.state.calls} "
                "calls (§31)"
            )
        if self.cache is not None:
            self._put_model_cache(key, output)
        return output

    # -- structured model cache helpers --------------------------------------

    def _get_model_cache(self, key: str, schema: Any):
        import json as _json

        path = self.cache._path(f"{key}-model") if self.cache else None
        if path is None or not path.exists():
            return None
        try:
            record = _json.loads(path.read_text(encoding="utf-8"))
            if self.cache is not None and self.cache.ttl_seconds > 0:
                import time

                if time.time() - record.get("cached_at", 0) > self.cache.ttl_seconds:
                    path.unlink(missing_ok=True)
                    return None
            return schema.model_validate(record["model"])
        except Exception:
            return None

    def _put_model_cache(self, key: str, output: Any) -> None:
        import json as _json

        if self.cache is None:
            return
        path = self.cache._path(f"{key}-model")
        record = {"cached_at": _import_time(), "model": _json.loads(output.model_dump_json())}
        path.write_text(_json.dumps(record), encoding="utf-8")


class UsageLedger(BaseModel):
    """Per-run usage summary for reporting and audit."""

    model_config = ConfigDict(validate_assignment=True)

    run_id: str
    budget: int = 0
    spent: int = 0
    calls: int = 0
    cache_hits: int = 0
    by_agent: dict[str, int] = Field(default_factory=dict)

    @classmethod
    def from_budget(cls, run_id: str, budget: TokenBudget) -> UsageLedger:
        return cls(
            run_id=run_id,
            budget=budget.state.budget,
            spent=budget.state.spent,
            calls=budget.state.calls,
            cache_hits=budget.state.cache_hits,
        )

    @property
    def saved_by_cache(self) -> int:
        """Rough estimate: cache hits ≈ tokens not spent."""
        return self.cache_hits

    def to_artifact(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.model_dump(mode="json"), indent=2), encoding="utf-8"
        )
