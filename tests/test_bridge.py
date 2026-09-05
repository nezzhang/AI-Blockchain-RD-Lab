"""§30 bridge provider tests: agent-as-LLM file protocol.

The bridge lets the operator (a reasoning agent or human) BE the lab's
LLM: requests are written to disk, the provider fails closed, and
installed answers replay for free — all through the same validation
path as any other provider (§2).
"""

from __future__ import annotations

import contextlib
import json

import pytest

from blockchain_rd_lab.agents.base import LLMError, LLMMessage, LLMValidationError
from blockchain_rd_lab.agents.bridge import (
    AgentBridgeProvider,
    request_id_from_messages,
)
from blockchain_rd_lab.discovery import IdeaBatch

MESSAGES = [
    LLMMessage(role="system", content="You are the Discovery Agent."),
    LLMMessage(role="user", content="Propose 2 mechanism ideas for stablecoins."),
]


def _valid_idea_batch() -> dict:
    return {
        "ideas": [
            {
                "name": "CPI-Basket Reference Unit",
                "category": "Stablecoins",
                "description": "A unit pegged to a CPI basket via mint throttle.",
                "core_mechanism": "S_t1 = S_t * (1 + clip(p - 1, -0.02, 0.02)).",
                "inputs": ["CPI Index"],
                "outputs": ["Adjusted Supply"],
            },
            {
                "name": "Trade-Weighted FX Peg",
                "category": "Stablecoins",
                "description": "Redemption fee tracks a trade-weighted FX index.",
                "core_mechanism": "fee_t = 0.01 + 0.1 * |fx_dev_t|.",
                "inputs": ["FX Index"],
                "outputs": ["Redemption Fee"],
            },
        ],
        "source_agent": "operator",
    }


class TestProtocol:
    def test_pending_request_written_and_fail_closed(self, tmp_path):
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with pytest.raises(LLMError, match="PENDING"):
            p.complete_structured(MESSAGES, schema=IdeaBatch)
        reqs = [
            r
            for r in (tmp_path / "bridge" / "requests").glob("*.json")
            if not r.name.endswith(".template.json")
        ]
        assert len(reqs) == 1
        req = json.loads(reqs[0].read_text())
        assert req["schema"] == "IdeaBatch"
        assert req["status"] == "pending"
        assert req["messages"][1]["content"].startswith("Propose")

    def test_deterministic_request_id(self):
        a = request_id_from_messages(MESSAGES, "IdeaBatch")
        b = request_id_from_messages(MESSAGES, "IdeaBatch")
        assert a == b
        # different schema or content => different id
        assert a != request_id_from_messages(MESSAGES, "PriorArtReport")
        other = [LLMMessage(role="user", content="different")]
        assert a != request_id_from_messages(other, "IdeaBatch")

    def test_same_request_not_duplicated(self, tmp_path):
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        for _ in range(3):
            with pytest.raises(LLMError):
                p.complete_structured(MESSAGES, schema=IdeaBatch)
        reqs = list((tmp_path / "bridge" / "requests").glob("*.json"))
        assert len([r for r in reqs if not r.name.endswith(".template.json")]) == 1

    def test_answer_template_written(self, tmp_path):
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with pytest.raises(LLMError):
            p.complete_structured(MESSAGES, schema=IdeaBatch)
        tpl = list((tmp_path / "bridge" / "requests").glob("*.template.json"))
        assert tpl, "fillable template must exist"
        template = json.loads(tpl[0].read_text())
        assert template["_schema"] == "IdeaBatch"
        assert "ideas" in template


class TestAnswers:
    def test_install_and_replay(self, tmp_path):
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with pytest.raises(LLMError):
            p.complete_structured(MESSAGES, schema=IdeaBatch)
        rid = request_id_from_messages(MESSAGES, "IdeaBatch")

        p.install_answer(rid, _valid_idea_batch())

        # replay: same call now succeeds, returning the validated model
        result = p.complete_structured(MESSAGES, schema=IdeaBatch)
        assert isinstance(result, IdeaBatch)
        assert result.ideas[0].name == "CPI-Basket Reference Unit"

    def test_invalid_answer_rejected_at_install(self, tmp_path):
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with pytest.raises(LLMError):
            p.complete_structured(MESSAGES, schema=IdeaBatch)
        rid = request_id_from_messages(MESSAGES, "IdeaBatch")

        bad = _valid_idea_batch()
        bad["ideas"][0]["name"] = ""  # violates min_length
        with pytest.raises(LLMValidationError):
            p.install_answer(rid, bad)
        assert not (tmp_path / "bridge" / "answers" / f"{rid}.json").exists()

    def test_install_unknown_request_fails(self, tmp_path):
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with pytest.raises(LLMError, match="No pending request"):
            p.install_answer("nope123", _valid_idea_batch())

    def test_replay_is_free(self, tmp_path):
        """Answered requests never write new pending files (§31/§32)."""
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with pytest.raises(LLMError):
            p.complete_structured(MESSAGES, schema=IdeaBatch)
        rid = request_id_from_messages(MESSAGES, "IdeaBatch")
        p.install_answer(rid, _valid_idea_batch())

        for _ in range(5):
            p.complete_structured(MESSAGES, schema=IdeaBatch)
        reqs = [
            r
            for r in (tmp_path / "bridge" / "requests").glob("*.json")
            if not r.name.endswith(".template.json")
        ]
        assert len(reqs) == 1
        assert json.loads(reqs[0].read_text())["status"] == "answered"


class TestPurge:
    def test_purge_keeps_answered(self, tmp_path):
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with pytest.raises(LLMError):
            p.complete_structured(MESSAGES, schema=IdeaBatch)
        rid = request_id_from_messages(MESSAGES, "IdeaBatch")
        p.install_answer(rid, _valid_idea_batch())

        # a second, unanswered request
        other_msgs = [LLMMessage(role="user", content="another prompt")]
        with pytest.raises(LLMError):
            p.complete_structured(other_msgs, schema=IdeaBatch)

        n = p.purge_pending()
        assert n == 1
        # answered stays replayable
        result = p.complete_structured(MESSAGES, schema=IdeaBatch)
        assert isinstance(result, IdeaBatch)


class TestCompleteRefusal:
    def test_free_text_completion_refused(self, tmp_path):
        """§2: the lab never uses unstructured LLM text — refuse it."""
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with pytest.raises(LLMError, match="structured-only"):
            p.complete(MESSAGES)


class TestCLI:
    def test_bridge_cli_roundtrip(self, tmp_path, monkeypatch, capsys):
        from blockchain_rd_lab import cli

        monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(
            "blockchain_rd_lab.cli._bridge_provider",
            lambda: AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge")),
        )
        from typer.testing import CliRunner

        runner = CliRunner()
        # create a pending request via the provider
        p = AgentBridgeProvider(bridge_dir=str(tmp_path / "bridge"))
        with contextlib.suppress(LLMError):
            p.complete_structured(MESSAGES, schema=IdeaBatch)
        rid = request_id_from_messages(MESSAGES, "IdeaBatch")

        r = runner.invoke(cli.app, ["bridge", "list"])
        assert rid in r.output

        r = runner.invoke(cli.app, ["bridge", "show", rid])
        assert "Propose 2 mechanism" in r.output

        r = runner.invoke(cli.app, ["bridge", "answer", rid, json.dumps(_valid_idea_batch())])
        assert "installed" in r.output.lower()

        r = runner.invoke(cli.app, ["bridge", "list", "--all"])
        assert "answered" in r.output.lower() or rid in r.output
