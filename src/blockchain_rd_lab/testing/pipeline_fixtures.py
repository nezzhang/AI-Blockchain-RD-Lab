"""Offline pipeline fixture provider (§34 demo, §35 determinism).

A schema-aware MockLLMProvider subclass: on every `complete_structured`
call it inspects the requested output schema and synthesizes the correct
fixture payload (deterministic — no queue bookkeeping). The candidate
context (name/category/etc.) is parsed from the user message, so fixture
reports are parameterized per candidate exactly like the LLM path.

This exercises the SAME validation + storage code as a real provider:
only the text proposal is deterministic (§2 prime directive).
"""

from __future__ import annotations

import json
import re
from typing import Any

from blockchain_rd_lab.agents.base import LLMMessage
from blockchain_rd_lab.agents.providers import MockLLMProvider


def _field_from_message(messages: list[LLMMessage], key: str) -> str:
    """Extract `key: value` lines from the user message."""
    for msg in messages:
        if msg.role != "user":
            continue
        m = re.search(rf"^{re.escape(key)}:\s*(.+)$", msg.content, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
    return ""


def _brief_dict(messages: list[LLMMessage]) -> dict[str, Any]:
    """Reconstruct enough of the candidate context for fixture builders."""
    return {
        "candidate_id": _field_from_message(messages, "CANDIDATE") or "cand-fixture",
        "name": _field_from_message(messages, "CANDIDATE"),
        "category": _field_from_message(messages, "category"),
        "description": _field_from_message(messages, "description") or "fixture",
        "core_mechanism": _field_from_message(messages, "core mechanism") or "fixture",
        "problem": "",
        "oracle_required": "oracle): yes"
        in " ".join(m.content for m in messages if m.role == "user"),
    }


class PipelineFixtureProvider(MockLLMProvider):
    """Serves per-agent fixtures by inspecting the output schema."""

    name = "mock-pipeline"

    def __init__(self) -> None:
        super().__init__()
        # §42 corpus serving: hand-written batches first, then the
        # deterministic generator takes over so --count 100 works offline.
        self._batch_index = 0

    def complete_structured(self, messages, *, schema: type, **kwargs):
        payload = self._fixture_for(schema, messages)
        # Route through the same validation path as every other response.
        from blockchain_rd_lab.agents.base import parse_json_as

        return parse_json_as(json.dumps(payload), schema, source=self.name)

    # -- fixture synthesis -----------------------------------------------------

    def _idea_batch(self) -> dict[str, Any]:
        """Hand-written batches first, then the §24 corpus generator."""
        from blockchain_rd_lab.testing.corpus import generate_corpus
        from blockchain_rd_lab.testing.fixtures_ideas import FIXTURE_BATCHES

        index = self._batch_index
        self._batch_index += 1
        if index < len(FIXTURE_BATCHES):
            batch = FIXTURE_BATCHES[index]
        else:
            # Deterministic generated corpus, offset past the fixtures.
            gen = list(generate_corpus(count=200, seed=24 + index))
            batch = gen[(index - len(FIXTURE_BATCHES)) % len(gen)]
        dump = batch.model_dump(mode="json")
        return {str(k): v for k, v in dump.items()}

    def _fixture_for(self, schema, messages: list[LLMMessage]) -> dict[str, Any]:
        schema_name = getattr(schema, "__name__", str(schema))

        if schema_name == "IdeaBatch":
            return self._idea_batch()

        if schema_name == "PriorArtReport":
            from blockchain_rd_lab.research import CandidateBrief
            from blockchain_rd_lab.research.agents import build_research_report_fixture

            brief = CandidateBrief.model_validate(_brief_dict(messages))
            return build_research_report_fixture(brief)["prior_art"]

        if schema_name == "EconomistReport":
            from blockchain_rd_lab.research import CandidateBrief
            from blockchain_rd_lab.research.agents import build_research_report_fixture

            brief = CandidateBrief.model_validate(_brief_dict(messages))
            return build_research_report_fixture(brief)["economist"]

        if schema_name == "MarketReport":
            from blockchain_rd_lab.research import CandidateBrief
            from blockchain_rd_lab.research.agents import build_research_report_fixture

            brief = CandidateBrief.model_validate(_brief_dict(messages))
            return build_research_report_fixture(brief)["market"]

        if schema_name == "MathModel":
            from blockchain_rd_lab.formalization.agents import build_math_model_fixture
            from blockchain_rd_lab.research import CandidateBrief

            brief = CandidateBrief.model_validate(_brief_dict(messages))
            return dict(build_math_model_fixture(brief))

        if schema_name in ("GameTheoryReport", "SecurityReport", "OracleReport", "RedTeamReport"):
            from blockchain_rd_lab.redteam.agents import build_redteam_fixture
            from blockchain_rd_lab.research import CandidateBrief

            brief = CandidateBrief.model_validate(_brief_dict(messages))
            key = {
                "GameTheoryReport": "game_theory",
                "SecurityReport": "security",
                "OracleReport": "oracle",
                "RedTeamReport": "red_team",
            }[schema_name]
            return build_redteam_fixture(brief)[key]

        if schema_name == "ImprovementProposal":
            from blockchain_rd_lab.improvement.agents import build_improvement_fixture
            from blockchain_rd_lab.research import CandidateBrief

            user_text = next(m.content for m in messages if m.role == "user")
            # The current model is embedded as pretty JSON — recover it
            # deterministically for the fixture patcher.
            import re as _re

            m = _re.search(
                r"CURRENT MODEL \(version \d+\):\n(\{.*\})\n\nADVERSARIAL",
                user_text,
                flags=_re.DOTALL,
            )
            if not m:
                raise ValueError("improvement fixture could not locate current model")
            current = json.loads(m.group(1))
            brief = CandidateBrief.model_validate(_brief_dict(messages))
            # Parse the ACTUAL adversarial findings from the prompt (the
            # improver's claims must match the attacks it was shown — a
            # blanket claim would let §33/§35 honesty gates see fixes that
            # were never claimed). r36: each line now carries the agent's
            # profitability hypothesis inside the brackets —
            # "- [red_team; false] description" — parse BOTH fields and
            # carry the hypothesis through to the fixture's claims
            # (findings the improver was shown, flags and all).
            findings: list[tuple[str, str, str]] = _re.findall(
                r"^- \[([a-z_]+); (true|false)\] (.+)$",
                user_text,
                flags=_re.MULTILINE,
            )
            parsed: list[dict[str, str]] = [
                {"agent": agent, "vector": vector, "profitable": flag}
                for agent, flag, vector in findings
            ]
            if not parsed:
                # Older prompt shape (pre-r36, no flag) — still parseable.
                legacy: list[tuple[str, str]] = _re.findall(
                    r"^- \[([a-z_]+)\] (.+)$",
                    user_text,
                    flags=_re.MULTILINE,
                )
                parsed = [
                    {"agent": agent, "vector": vector, "profitable": "true"}
                    for agent, vector in legacy
                ]
            if not parsed:
                parsed = [
                    {
                        "agent": "red_team",
                        "vector": "anchor spike manipulation",
                        "profitable": "true",
                    }
                ]
            return dict(build_improvement_fixture(brief, current, parsed))

        # Unknown schema: no fixture available — fail closed (§30) rather
        # than emit digest garbage that would masquerade as evidence.
        raise ValueError(f"no pipeline fixture for schema {schema_name!r}")


def build_pipeline_provider() -> PipelineFixtureProvider:
    """Provider for `lab pipeline --mock-fixtures` (no queue needed)."""
    return PipelineFixtureProvider()
