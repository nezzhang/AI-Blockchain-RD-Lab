"""Round 13: formalize answers — install the smoke-gated v1 models.

The r12 no-double-save flow: nothing was pre-stored; these answers are
the canonical store, and the formalize replay persists them as v1.

Run: .venv/bin/python scripts/r13_answer_formalize.py
"""

from __future__ import annotations

from pathlib import Path

from blockchain_rd_lab.agents.bridge import AgentBridgeProvider


def _models() -> dict[str, dict]:
    src = Path("scripts/r13_models.py").read_text().replace(
        'if __name__ == "__main__":\n    main()\n', ""
    )
    ns: dict[str, object] = {"__name__": "r13m"}
    exec(compile(src, "r13_models.py", "exec"), ns)
    from blockchain_rd_lab.config import REPO_ROOT, load_config
    from blockchain_rd_lab.database import LabDatabase

    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    out = {}
    for build in ("oracle_model", "joule_model"):
        m = ns[build](db)  # type: ignore[misc]
        out[m.candidate_id] = m.model_dump(mode="json")  # type: ignore[attr-defined]
    return out


def main() -> None:
    models = _models()
    rid_by_cid = {
        "cand-d656eeeaeca1": "b7f1ba7256051781",  # oracle
        "cand-4e292d1b929b": "a3efa598406e751f",  # joule
    }
    p = AgentBridgeProvider()
    for cid, rid in rid_by_cid.items():
        model = models[cid]
        model["version"] = 1
        p.install_answer(rid, model)
        print("answered", rid, "with", cid, "v1 (3-speed persistent gate)")


if __name__ == "__main__":
    main()
