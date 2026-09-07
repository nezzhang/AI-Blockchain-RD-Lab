"""Round 11 part 5: install the stored models as formalize answers.

The 4 formalize bridge requests expect a MathModel JSON (schema
'mathmodel' or similar). This script reads each pending formalize
request, resolves its candidate by name from the prompt, loads the
STORED v1 model for that candidate (already smoke-passed), and
installs it as the answer — the §2 chain stays intact: the model that
the pipeline formalizes IS the smoke-tested stored model.
"""

from __future__ import annotations

import json
import re

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase

REQ = REPO_ROOT / ".bridge" / "requests"
STALE = {"27e6edeb0da116df", "ca2cad10be5038a9"}


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name_to_cid = {c.name: c.id for c in db.list_candidates(limit=None)}
    provider = AgentBridgeProvider()
    installed = 0
    for p in sorted(REQ.glob("*.json")):
        if p.name.endswith(".template.json"):
            continue
        req = json.loads(p.read_text())
        if req["status"] != "pending":
            continue
        rid = p.name.replace(".json", "")
        if rid in STALE:
            continue
        cand_name = None
        for msg in req["messages"]:
            m = re.search(r"CANDIDATE: (.+?)\ncategory", msg["content"])
            if m:
                cand_name = m.group(1)
                break
        if cand_name is None or cand_name not in name_to_cid:
            print(f"  skip {rid} ({req['schema']}) — not an r11 candidate request")
            continue
        model_json = db.get_latest_math_model(name_to_cid[cand_name])
        if model_json is None:
            raise SystemExit(f"no stored model for {cand_name}")
        provider.install_answer(rid, json.loads(model_json))
        installed += 1
        print(f"  {rid} {req['schema']} <- {cand_name[:40]} (stored v1)")
    print(f"{installed} formalize answers installed")


if __name__ == "__main__":
    main()
