"""Round 16: formalize answer — install the smoke-gated v1 model (no-store flow).

Run: .venv/bin/python scripts/r16_answer_formalize.py
"""

from __future__ import annotations

from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider


def main() -> None:
    src = Path("scripts/r16_models.py").read_text().replace(
        'if __name__ == "__main__":\n    main()\n', ""
    )
    ns: dict[str, object] = {"__name__": "r16m"}
    exec(compile(src, "r16_models.py", "exec"), ns)
    payload = ns["model"]().model_dump(mode="json")  # type: ignore[misc,operator]
    payload["version"] = 1
    AgentBridgeProvider().install_answer("9ac787e0449977cd", payload)
    print("answered 9ac787e0449977cd with cand-47c62aa507b4 v1 "
          "(reversion-keyed additive-flow reserve)")


if __name__ == "__main__":
    main()
