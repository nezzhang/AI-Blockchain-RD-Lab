"""Round 19: window-length robustness audit disposition.

The r18 lesson ("every window-end-only classification is window-
length-sensitive — measure the DIRECTION, not the endpoint") made
systematic: run the park-style battery at 60/120/240 steps and find
every ranked candidate whose edge classification FLIPS with window
length. A flip means either a still-moving state misread at one
length or a hidden pin reached at another.

AUDIT RESULT (3 flips >100 found):
1. Symmetric-Cap Fee Recycle Reserve (the r18 successor): 340 -> 394
   -> 0.0. DIAGNOSED HONEST-NEGATIVE: at 240 the reserve is still in
   slow transit toward its demand-EMA target (reversion 0.15/step);
   convergence verified monotone-stable to the T+50 steady state at
   steps 400 (Z-T gap 103 -> 50, no undershoot). The 60/120 readings
   were transit, not extraction. NO FLAW — documented as the audit's
   control case.
2. Level-Recentered Bandwidth Bond Market: 266 -> 230 -> 136. The
   longer grind raises BOTH the pattern and the matched creep-only
   base (the r18 compound design: base isolates what the timed
   strike ADDS), so the difference shrinks — the matched-base
   subtraction working as intended. The A_t allocation pass-through
   (299.7 under crash_park) remains disclosed. NO FLAW.
3. Productivity-Index Scaled Compute Clearing: 188 -> 400 -> 400.
   CONFIRMED FLAW — the r15 floor-above-crash-level class: the wage
   pool's clip floor is 600.0 while the crash parks X at 400.0; the
   flow IS symmetrically step-capped (max(-step_w, min(step_w, ...)),
   ±40/step) but the FLOOR blocks re-basing, so W_t pins at 600
   forever under the moved regime — a 400 excursion standing by
   construction (measured at 120 and 240 steps; the 60-step window
   read only 188 because the pool was still draining toward the
   pin). The r18 pin-aware arrival fix kept it visible; this round
   supersedes on the measured lineage.
4. Output-Indexed Compute Swap Board (the audit's post-fix finding):
   the r19b target-relative rule's anti-hiding probe exposed a
   SECOND floor-above-crash-level instance hidden pre-r19 by the
   separation-predicate self-read leak — B_t pins at its 500 floor
   at all windows. Superseded; the wage-pool successor carries the
   family's fix construction.

Run: .venv/bin/python scripts/r19_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

SUPERSEDE = {
    "cand-9af3c61061d1":
        "floor-above-crash-level class (r19 window audit): the wage "
        "pool's clip floor 600 sits ABOVE the -60% crash level 400 — "
        "the flow is symmetrically step-capped but the floor blocks "
        "re-basing, so W_t pins at 600 under the moved regime (400 "
        "standing at 120/240-step windows; still draining at 60) — "
        "the r15 bandwidth-bond flaw family, measured",
}

SUPERSEDE.update({
    "cand-d5bf8d515927":
        "floor-above-crash-level class (r19 window audit, second "
        "instance): the swap board's pool B_t pins at its 500 floor "
        "under the moved regime (X=400) at ALL windows 60/120/240 — "
        "its min(400, 0.7*(X-1000)) tracking term caps the positive "
        "leg while the anchor reversion pulls toward 1000 and the "
        "floor blocks re-basing (500 standing, stable); hidden "
        "pre-r19 by the separation-predicate self-read leak, "
        "exposed by the r19b target-relative rule's anti-hiding "
        "probe",
})


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for cid, reason in SUPERSEDE.items():
        cand = db.get_candidate(cid)
        assert cand is not None, cid
        assert cand.status in (CandidateStatus.SCORED, CandidateStatus.FINALIST), (
            f"{cid} is {cand.status}"
        )
        cand.transition(CandidateStatus.SUPERSEDED)
        cand.innovation_claim = f"SUPERSEDED (r19 window audit): {reason}"
        db.save_candidate(cand)
        print(f"  {cid} -> SUPERSEDED  {cand.name[:44]}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")
