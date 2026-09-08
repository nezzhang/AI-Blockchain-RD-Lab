"""Round 19: formalize answer — install the smoke-gated v1 model.

Run: .venv/bin/python scripts/r19_answer_formalize.py
"""

from __future__ import annotations

from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider


def main() -> None:
    src = Path("scripts/r19_models.py").read_text().replace(
        'if __name__ == "__main__":\n    main()\n', ""
    )
    ns: dict[str, object] = {"__name__": "r19m"}
    exec(compile(src, "r19_models.py", "exec"), ns)
    payload = ns["model_v1"]().model_dump(mode="json")  # type: ignore[misc,operator]
    payload["version"] = 1
    AgentBridgeProvider().install_answer("7db3d04362d953ce", payload)
    print("answered 7db3d04362d953ce", payload["candidate_id"], "v1")


if __name__ == "__main__":
    main()
