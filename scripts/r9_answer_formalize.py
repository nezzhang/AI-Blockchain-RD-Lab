"""Bridge answers: round-9 MathModel requests.

Answers each pending MathModel request with the matching model built by
scripts/r9_models.py (already smoke-tested: 13/13 distinct non-degenerate
scenario finals, whale distinguishable from base).
"""

from __future__ import annotations

import glob
import json
import re
import sys

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider

sys.path.insert(0, "scripts")
from r9_models import BUILDERS


def candidate_name_from(messages: list[dict]) -> str | None:
    for m in messages:
        c = re.search(r"CANDIDATE: (.+?)\ncategory", m["content"])
        if c:
            return c.group(1).strip()
    return None


def main() -> None:
    bridge = AgentBridgeProvider()
    installed = 0
    for f in sorted(glob.glob(".bridge/requests/*.json")):
        with open(f) as fh:
            d = json.load(fh)
        if d.get("schema") != "MathModel" or d.get("status") != "pending":
            continue
        name = candidate_name_from(d["messages"])
        if name is None or name not in BUILDERS:
            continue
        model = BUILDERS[name]("unknown")
        bridge.install_answer(d["id"], model.model_dump(mode="json"))
        installed += 1
    print(f"installed {installed} MathModel answers")


if __name__ == "__main__":
    main()
