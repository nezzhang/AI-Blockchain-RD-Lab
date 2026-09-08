"""Round 21: §27 publication-decision brief (r23: library-backed).

The r21 brief's builder moved into the reporting library in r23
(blockchain_rd_lab.reporting.decision — one source of truth; the
r23 three-option packages and any future pair re-use it). This
script stays as the thin CLI driver that writes the brief file.

Run: .venv/bin/python scripts/r21_decision_brief.py
"""

from __future__ import annotations

from pathlib import Path

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.reporting.decision import (
    DECISION_CANDIDATES,
    build_decision_brief,
)


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    text = build_decision_brief(db, DECISION_CANDIDATES)
    out = REPO_ROOT / "reports" / "release" / "decision-brief-r21.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"written {out} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
