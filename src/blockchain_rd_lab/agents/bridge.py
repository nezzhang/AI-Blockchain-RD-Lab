"""Agent-as-LLM bridge provider: the lab's human/agent operator IS the model.

This provider replaces the network hop with a file protocol so a
reasoning agent (or a careful human) can act as the lab's LLM without
any API key or spend (§30):

    1. The lab calls ``complete``/``complete_structured`` as usual.
    2. The provider writes a PENDING request file describing the prompt
       and, if structured, the exact Pydantic schema the answer must
       satisfy.
    3. The provider FAILS CLOSED (§30/§35): the run halts at this stage,
       resumable by status. The database remains the checkpoint.
    4. The operator answers: ``lab bridge answer <id> --file answer.json``
       (or the template written next to the request, filled in).
    5. On the next run the provider replays installed answers — answered
       requests are FREE, like cache hits (§31/§32).

Every answered request passes the same validation path as any provider:
``parse_json_as(schema, ...)`` for structured calls (§2: LLM proposes,
code tests), so an invalid answer never enters the database.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from blockchain_rd_lab.agents.base import LLMError, LLMMessage, LLMProvider, LLMResponse


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def request_id_from_messages(messages: list[LLMMessage], schema: str = "") -> str:
    """Deterministic request id from the prompt content (§2/§32 reuse).

    Same prompt + schema ⇒ same id ⇒ an installed answer replays forever
    (free), and re-runs don't duplicate pending files.
    """
    import hashlib

    digest = hashlib.sha256()
    for m in messages:
        digest.update((m.role + "\x1f" + m.content).encode("utf-8"))
    digest.update(b"\x1e" + schema.encode("utf-8"))
    return digest.hexdigest()[:16]


class AgentBridgeProvider(LLMProvider):
    """File-protocol provider: the operator is the LLM."""

    name = "bridge"

    def __init__(
        self,
        bridge_dir: str = ".bridge",
        *,
        base_url: str = "",
        model: str = "",
        api_key_env: str = "",
        tier_models: dict[str, str] | None = None,
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 2.0,
    ) -> None:
        # The shared ProviderSettings block is accepted for uniform config
        # (§30) but only bridge_dir matters: no network, no key, no spend.
        self.bridge_dir = Path(bridge_dir)
        if not self.bridge_dir.is_absolute():
            # resolve against the repo root so tests/subprocesses match
            from blockchain_rd_lab.config import REPO_ROOT

            self.bridge_dir = REPO_ROOT / bridge_dir
        self.requests_dir = self.bridge_dir / "requests"
        self.answers_dir = self.bridge_dir / "answers"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.answers_dir.mkdir(parents=True, exist_ok=True)

    # -- protocol ------------------------------------------------------------

    def _request_path(self, rid: str) -> Path:
        return self.requests_dir / f"{rid}.json"

    def _answer_path(self, rid: str) -> Path:
        return self.answers_dir / f"{rid}.json"

    def _template_path(self, rid: str) -> Path:
        return self.requests_dir / f"{rid}.template.json"

    def _write_request(
        self,
        rid: str,
        messages: list[LLMMessage],
        schema_name: str,
        temperature: float,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": rid,
            "schema": schema_name,
            "temperature": temperature,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
            ],
            "created_at": _now_iso(),
            "status": "pending",
        }
        self._request_path(rid).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        # For structured requests, write a fillable template with the
        # schema's required fields and defaults so answering is easy.
        if schema_name and schema_name != "str":
            template = self._schema_template(schema_name)
            if template is not None:
                self._template_path(rid).write_text(
                    json.dumps(template, indent=2), encoding="utf-8"
                )
        return payload

    def _schema_template(self, schema_name: str) -> dict[str, Any] | None:
        """Best-effort JSON template from the Pydantic schema by name."""
        schema_cls = self._resolve_schema(schema_name)
        if schema_cls is None:
            return None
        template: dict[str, Any] = {"_schema": schema_name}
        try:
            for name, field in schema_cls.model_fields.items():
                if name == "id" and field.is_required():
                    continue
                ann = str(field.annotation)
                if "str" in ann:
                    template[name] = "<str>"
                elif "bool" in ann:
                    template[name] = False
                elif "int" in ann and "float" not in ann:
                    template[name] = 0
                elif "float" in ann:
                    template[name] = 0.0
                elif "list" in ann:
                    template[name] = ["<item>"]
                else:
                    template[name] = f"<{ann}>"
        except Exception:
            return None
        return template

    def _resolve_schema(self, schema_name: str) -> Any | None:
        """Find a Pydantic model class by name across lab modules."""
        import importlib

        for module_name in (
            "blockchain_rd_lab.discovery",
            "blockchain_rd_lab.research",
            "blockanswer.answer",  # placeholder never imported
            "blockchain_rd_lab.formalization",
            "blockchain_rd_lab.redteam",
            "bucket.answer",
            "blockchain_rd_lab.improvement",
            "blockchain_rd_lab.scoring.assessment",
        ):
            if "answer" in module_name:
                continue
            try:
                module = importlib.import_module(module_name)
            except Exception:
                continue
            cls = getattr(module, schema_name, None)
            if cls is not None and hasattr(cls, "model_fields"):
                return cls
        return None

    # -- LLMProvider interface --------------------------------------------------

    def complete(
        self,
        messages: list[LLMMessage],
        *,
        tier: Any = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise LLMError(
            "bridge provider is structured-only: the lab never uses free-text "
            "completion (§2)"
        )

    def complete_structured(
        self,
        messages: list[LLMMessage],
        *,
        schema: type,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Any:
        rid = request_id_from_messages(messages, getattr(schema, "__name__", str(schema)))
        # Replay path: an installed answer returns for free (§31/§32).
        apath = self._answer_path(rid)
        if apath.exists():
            answer = json.loads(apath.read_text(encoding="utf-8"))
            answer = answer.get("answer", answer)
            from blockchain_rd_lab.agents.base import parse_json_as

            return parse_json_as(
                json.dumps(answer), schema, source=f"bridge:{rid}"
            )
        # Pending path: write the request, fail closed (§30/§35).
        self._write_request(
            rid,
            messages,
            getattr(schema, "__name__", str(schema)),
            temperature,
        )
        raise LLMError(
            f"bridge request {rid} is PENDING: answer it with "
            f"`lab bridge answer {rid}` (see the request + template files "
            f"in {self.requests_dir}), then re-run. The run is resumable "
            f"by status (§35)."
        )

    # -- operator helpers (CLI) ----------------------------------------------

    def list_requests(self, status: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for p in sorted(self.requests_dir.glob("*.json")):
            if p.name.endswith(".template.json"):
                continue  # fillable template, not a request
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if status is None or data.get("status") == status:
                out.append(data)
        return out

    def install_answer(self, rid: str, answer: dict[str, Any]) -> Path:
        """Validate + install an operator answer (structured answers only)."""
        request = self._request_path(rid)
        if not request.exists():
            raise LLMError(f"No pending request {rid}")
        req = json.loads(request.read_text(encoding="utf-8"))
        schema_cls = self._resolve_schema(req.get("schema", ""))
        if schema_cls is None:
            raise LLMError(
                f"Cannot resolve schema {req.get('schema')!r} for request {rid}"
            )
        from blockchain_rd_lab.agents.base import parse_json_as

        parse_json_as(json.dumps(answer), schema_cls, source=f"bridge-answer:{rid}")
        self._answer_path(rid).write_text(
            json.dumps({"id": rid, "answer": answer}, indent=2),
            encoding="utf-8",
        )
        req["status"] = "answered"
        self._request_path(rid).write_text(
            json.dumps(req, indent=2), encoding="utf-8"
        )
        return self._answer_path(rid)

    def get_answer(self, rid: str) -> dict[str, Any] | None:
        p = self._answer_path(rid)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("answer", data)

    def purge_pending(self) -> int:
        """Remove pending requests (fresh round); answered stay (free replay)."""
        n = 0
        for p in self.requests_dir.glob("*.json"):
            if p.name.endswith(".template.json"):
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("status") == "pending":
                p.unlink()
                n += 1
        return n
