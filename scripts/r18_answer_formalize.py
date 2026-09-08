"""Round 18: formalize answers — install both smoke-gated v1 models.

Run: .venv/bin/python scripts/r18_answer_formalize.py
"""

from __future__ import annotations

from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider


def main() -> None:
    src = Path("scripts/r18_models.py").read_text().replace(
        'if __name__ == "__main__":\n    main()\n', ""
    )
    ns: dict[str, object] = {"__name__": "r18m"}
    exec(compile(src, "r18_models.py", "exec"), ns)
    for rid, key in [
        ("8a520e527fb88e7f", "model_a"),
        ("1dc37c6243ea22ad", "model_b"),
    ]:
        payload = ns[key]().model_dump(mode="json")  # type: ignore[misc,operator]
        payload["version"] = 1
        AgentBridgeProvider().install_answer(rid, payload)
        print("answered", rid, payload["candidate_id"], "v1")


if __name__ == "__main__":
    main()
