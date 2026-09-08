"""Round 18: the compound-choreography supersession set (r18 census).

The GRIND_HARVEST census (creep-then-strike) surfaced TWO candidates
whose edges the SINGLE-pattern battery had read as zero — the
sequencing hypothesis confirmed. Diagnosing WHY exposed two
measurement bugs (fixed the same round) and, behind them, TWO flaw
classes on four SCORED candidates:

MEASUREMENT FIXES (adversarial.py, both pinned by the census):
1. PIN-AWARE ARRIVAL: a state sitting exactly AT a declared clip
   bound was read by the r15b level-arrival check as "tracking the
   level" whenever the bound coincided with the crashed level —
   Cyclic's Z_t pinned at its 400 floor while X sits at 400 was
   classified REGIME-TRACKING, hiding a fully-drained pool (the
   compound's creep-then-strike moved the coincidence enough to see
   it; the single crash_park had the identical hidden drain).
2. HEAL-CONTRADICTION GUARD: the r15 transient check reads the
   window END only; a state still healing toward its ANCHOR (the
   r13 flaw signature) can sit under the 25% transient threshold at
   window end and be mislabeled TRANSIENT — the Treasury's V_t
   (heal 0.34 mid-window, 0.007 at longer windows) was hidden under
   crash_park and only surfaced under the compound's shorter
   post-strike window. The guard now requires recovered-to-NEAR-
   THE-LEVEL for a transient classification.

FLAW CLASSES / SUPERSESSIONS (all measured, §11 + r7/r16 precedent):
- Adverse-Selection Taxed Prediction Clearing (cand-6b5791c8ae9c):
  ANCHOR-HEAL class — I_t (adverse-selection intensity) and A_t
  (allocation) heal to 1000.0 exactly (heal 0.0) while the level
  stays -60% moved; excursion 750 measured under crash_park.
- Treasury-Backed Fee Parameter Governance (cand-73de8d339542):
  ANCHOR-HEAL class — V_t (the vote signal) reverts to its 1000
  anchor (heal 0.007 at window end) while X sits at 400; excursion
  600 measured.
- Cyclic Demand Reserve for Fee Recycles (cand-e626f13713b0):
  STANDING FLOOR-PIN DRAIN — Z_t's inflow is capped (min(200,
  0.10*(X-1000))) but the OUTFLOW is uncapped below 1000: the term
  0.10*(X-1000) goes negative without any floor, bleeding the pool
  to its 400 floor (-60%/step region), 509.7 standing under
  crash_park, 579.0 under the compound.
- Belief-Weighted Volatility Target Fund (cand-5e05dec83af0):
  STANDING FLOOR-PIN DRAIN — V_t pinned at its 500 floor under the
  moved regime (301.3 standing), the same uncapped-outflow family.

Successors: ONE per flaw class (the r16 exemplar discipline):
- Class A (anchor-heal) → r19 successor with the r13 three-speed
  insurance polarity (the construction proven by the r13 successors).
- Class B (uncapped outflow) → successor with the symmetric cap: the
  outflow floor mirrors the inflow cap (the min() asymmetry fixed).

Run: .venv/bin/python scripts/r18_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

SUPERSEDE = {
    "cand-6b5791c8ae9c":
        "anchor-heal class (r18 compound census): I_t/A_t heal to 1000 "
        "exactly (heal 0.0) while the level stays -60% moved — tail "
        "unprotected under the moved regime; excursion 750 measured",
    "cand-73de8d339542":
        "anchor-heal class (r18 compound census): the vote signal V_t "
        "reverts to its 1000 anchor (heal 0.007) while X sits at 400; "
        "excursion 600 measured; hidden pre-r18 by the transient "
        "window-end misclassification",
    "cand-e626f13713b0":
        "standing floor-pin drain (r18): the recycle inflow is capped "
        "(min(200, ...)) but the outflow is UNCAPPED below 1000 — the "
        "pool bleeds to its 400 floor under any sub-1000 regime; 509.7 "
        "standing under crash_park (hidden pre-r18 by the pin-coincident "
        "arrival misclassification)",
    "cand-5e05dec83af0":
        "standing floor-pin drain (r18): the vol-target pool V_t pinned "
        "at its 500 floor under the moved regime, 301.3 standing — the "
        "uncapped-outflow family",
}


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for cid, reason in SUPERSEDE.items():
        cand = db.get_candidate(cid)
        assert cand is not None, cid
        assert cand.status in (CandidateStatus.SCORED, CandidateStatus.FINALIST), (
            f"{cid} is {cand.status}"
        )
        cand.transition(CandidateStatus.SUPERSEDED)
        cand.innovation_claim = f"SUPERSEDED (r18 compound census): {reason}"
        db.save_candidate(cand)
        print(f"  {cid} -> SUPERSEDED  {cand.name[:44]}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")


if __name__ == "__main__":
    main()
