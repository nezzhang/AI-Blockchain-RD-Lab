"""Round 23: build ALL THREE §27 publication-option packages.

The r21 brief's remaining options were: publish the successor /
publish the incumbent / publish both as a comparative package.
"Running" them, within §28/§41 (the lab stages; the human posts —
publishing official claims is a listed human-approval action), is
making each option LITERALLY BUILDABLE:

1. SUCCESSOR package — the §7 rank-1's §27 release package
   (the existing default path; restaged with the r22 sweep
   evidence now in the census trail).
2. INCUMBENT package — the same builder with the candidate
   OVERRIDE (the r23 release.py parameterization): §27 is the
   human's decision, so any finalist must be publishable, not
   only the rank-1. Output: release-package-incumbent.md
3. COMPARATIVE package — the both-option: the decision brief
   (moved r21→library in r23: one source of truth) + both §27
   packages, side by side, presented and never ranked.

All three land in reports/release/. Nothing is posted anywhere;
the packages exist so the human's §27 call is a file copy, not a
research project.

Run: .venv/bin/python scripts/r23_build_packages.py
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.reporting.decision import (
    DECISION_CANDIDATES,
    build_decision_brief,
)
from blockchain_rd_lab.reporting.release import ReleasePackageBuilder

SUCCESSOR = DECISION_CANDIDATES[0]  # rank-1 (§7 default subject)
INCUMBENT = DECISION_CANDIDATES[1]  # the r15-r19 recommended


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    rb = ReleasePackageBuilder(db)
    # the builder itself appends /release — hand it the reports root
    out = REPO_ROOT / "reports"

    # 1. the successor package (the §7-recommended default subject)
    p1 = rb.write(out, candidate_id=None,
                  filename="release-package-successor.md")
    assert p1 is not None
    print(f"1. successor package: {p1.name}")

    # 2. the incumbent package (the explicit-override path)
    p2 = rb.write(out, candidate_id=INCUMBENT,
                  filename="release-package-incumbent.md")
    assert p2 is not None
    print(f"2. incumbent package: {p2.name}")

    # 3. the comparative package (the both-option): brief + both
    # packages' §1-§4 evidence, assembled by code, side by side
    brief = build_decision_brief(db)
    s_txt = p1.read_text(encoding="utf-8")
    i_txt = p2.read_text(encoding="utf-8")

    lines: list[str] = []
    lines.append("# §27 Comparative Publication Package (both options)")
    lines.append("")
    lines.append(
        "The third §27 option: publish BOTH decision candidates. "
        "Assembled by code from stored evidence only (§2). This "
        "document presents the two mechanisms side by side and the "
        "evidence for each; it RANKS NOTHING — the comparative "
        "score table is the §19 deterministic output, the census "
        "tables are the §21 measurement trail, and the §27 call "
        "stays with the human (§28/§41: the lab stages, the human "
        "posts)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("# Part A — The Comparative Decision Brief")
    lines.append("")
    lines.append(brief)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("# Part B — §27 Release Package: the successor (§7 rank 1)")
    lines.append("")
    lines.append(s_txt)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("# Part C — §27 Release Package: the incumbent (r15-r19 recommended)")
    lines.append("")
    lines.append(i_txt)
    lines.append("")
    # written directly (not via the builder): match the builder's
    # reports/release/ landing directory
    comp = out / "release" / "comparative-package.md"
    comp.write_text("\n".join(lines), encoding="utf-8")
    print(f"3. comparative package: {comp.name}")

    # keep the conventional latest pointer on the rank-1 default
    rb.write(out, candidate_id=None,
             filename="release-package-latest.md")
    print("   release-package-latest.md re-staged (rank-1 default)")


if __name__ == "__main__":
    main()
