"""Round 15: formalize answer — install the smoke-gated v1 model.

The r12 no-double-save flow: nothing pre-stored; this answer is the
canonical store, and the formalize replay persists it as v1.

Run: .venv/bin/python scripts/r15_answer_formalize.py
"""

from __future__ import annotations

from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase


def main() -> None:
    src = Path("scripts/r15_models.py").read_text().replace(
        'if __name__ == "__main__":\n    main()\n', ""
    )
    ns: dict[str, object] = {"__name__": "r15m"}
    exec(compile(src, "r15_models.py", "exec"), ns)
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    model = ns["model"](db)  # type: ignore[misc, operator]
    payload = model.model_dump(mode="json")  # type: ignore[attr-defined]
    payload["version"] = 1
    AgentBridgeProvider().install_answer("33ea49b3aff04d6c", payload)
    print("answered 33ea49b3aff04d6c with cand-6fea4a5332ca v1 "
          "(single-magnet pool)")


if __name__ == "__main__":
    main()
