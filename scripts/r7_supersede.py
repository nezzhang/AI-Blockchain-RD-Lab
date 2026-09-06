"""Round 7 (correction): honest supersede of evidence-invalid finalists.

§2/§11/§26: the evidence-quality audit (lab audit) found 6 ranked
finalists whose stored §15 evidence carries no weight under today's
gates — 3 vacuous (states pinned at clip bounds; every scenario
identical), 3 uninterpretable (legacy dependency cycles today's
interpreter rejects). Two more finalists are replay-duplicates of
earlier candidates (same description, same replayed evidence —
restorage was a demo workaround, never honest ranking evidence).

This script marks them SUPERSEDED (the §11-legal exit from
FINALIST/SCORED) with the honest reason recorded in the candidate's
innovation_claim lineage field, ready for the §26 archive. Successors
are minted in part 2 with the corrected models.

Run: .venv/bin/python scripts/r7_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

# verdicts measured by lab audit (deterministic re-run under today's gates)
SUPERSEDE_SET: dict[str, str] = {
    "cand-7f4c2dee85e7": (
        "vacuous evidence — §15 battery 13/13 degenerate under today's gates "
        "(states pinned at clip bounds); v2 'clean' verdicts describe "
        "identical saturated trajectories, not stress survival"
    ),
    "cand-cb4d584867ed": (
        "vacuous evidence — §15 battery 13/13 degenerate under today's gates "
        "(states pinned at clip bounds); v2 'clean' verdicts describe "
        "identical saturated trajectories, not stress survival"
    ),
    "cand-c17ab7a0f74e": (
        "vacuous evidence — §15 battery 13/13 degenerate under today's gates "
        "(states pinned at clip bounds); v2 'clean' verdicts describe "
        "identical saturated trajectories, not stress survival"
    ),
    "cand-636a97854ac8": (
        "uninterpretable evidence — stored v2 model has a dependency cycle "
        "(capacity/rebalance/seasoning_depth) today's interpreter rejects; "
        "its §15 runs predate the toposort gate and read stale values"
    ),
    "cand-ef024f8bb596": (
        "uninterpretable evidence — stored v2 model has a dependency cycle "
        "(partition_income/shared_spend/solvency_tie) today's interpreter "
        "rejects; its §15 runs predate the toposort gate"
    ),
    "cand-642ea9f42170": (
        "uninterpretable evidence — stored v1 model has a dependency cycle "
        "(impact_check/rebate_pool) today's interpreter rejects; its §15 "
        "runs predate the toposort gate"
    ),
    # replay-duplicates (restorage workaround; identical descriptions +
    # replayed evidence to the earlier candidates)
    "cand-db0588dfed1a": (
        "replay-duplicate of cand-58d7091eb2a7 (Bandwidth Futures Market) — "
        "same description, replayed evidence; a restorage workaround, not "
        "independent ranking evidence"
    ),
    "cand-108293ca9f4f": (
        "replay-duplicate of cand-1acbaa9de0b0 (AI-Compute Denominated Debt) — "
        "same description, replayed evidence; a restorage workaround, not "
        "independent ranking evidence"
    ),
}


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    superseded = 0
    for cid, reason in SUPERSEDE_SET.items():
        cand = db.get_candidate(cid)
        if cand is None:
            print(f"  MISSING {cid}")
            continue
        if cand.status is CandidateStatus.SUPERSEDED:
            print(f"  already  {cid} {cand.name[:40]}")
            continue
        target = cand.transition(CandidateStatus.SUPERSEDED)
        # honest lineage record: what happened, why, successor named later
        cand.innovation_claim = (
            f"SUPERSEDED (r7 evidence-quality correction): {reason}. "
            "Successor candidate with a contract-compliant model follows."
        )
        db.save_candidate(cand)
        superseded += 1
        print(f"  {cid} {cand.name[:44]:46s} -> {target.value}")
    print(f"\n{superseded} candidates SUPERSEDED")

    # §26 archive rebuild — superseded entries now recorded with reasons
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive: {summary.rejected_indexed} entries -> {summary.archive_path}")
    # sanity: no finalist lost
    fins = db.list_candidates(status=CandidateStatus.FINALIST, limit=None)
    print(f"remaining finalists: {len(fins)}")
    for f in fins:
        print(f"  {f.id} {f.overall_score} {f.name[:50]}")


if __name__ == "__main__":
    main()
