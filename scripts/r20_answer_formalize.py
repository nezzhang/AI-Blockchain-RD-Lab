"""Round 20: formalize answer — install the smoke-gated v1 model.

Run: .venv/bin/python scripts/r20_answer_formalize.py
"""

from __future__ import annotations

from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider


def main() -> None:
    src = Path("scripts/r20_models.py").read_text().replace(
        'if __name__ == "__main__":\n    main()\n', ""
    )
    ns: dict[str, object] = {"__name__": "r20m"}
    exec(compile(src, "r20_models.py", "exec"), ns)
    from blockchain_rd_lab.config import REPO_ROOT, load_config
    from blockchain_rd_lab.database import LabDatabase
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    cid = next(c.id for c in db.list_candidates(limit=None)
               if c.name == "Separation-Keyed Fee Smoothing Escrow")
    payload = ns["model_v1"](cid).model_dump(mode="json")  # type: ignore[misc,operator]
    payload["version"] = 1
    AgentBridgeProvider().install_answer("8b9a0e1189c469d8", payload)
    print("answered 8b9a0e1189c469d8", payload["candidate_id"], "v1")


if __name__ == "__main__":
    main()
