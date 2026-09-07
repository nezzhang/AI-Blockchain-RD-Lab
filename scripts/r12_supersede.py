"""Round 12 part 1: supersede the Sustained-Band Forecast Fee Meter.

The r11 battery measured the successor still draining +487 B_m under
pump_park (and +295 under vol_oscillation) — traced to a REAL design
flaw the r11 docs recorded as the open question: the band center
(T_t) is a 1000-anchored reverting EMA, so a PERMANENT level shift
looks like eternal mis-banding. The r12 fix re-centers the band on the
LEVEL itself (fast/slow EMA divergence gate — a MACD construction).

This supersede is a measured-design-flaw supersede: the r11 evidence
chain stands (honest red-team + survives verdict); what changed is the
battery measurement closing the open question with a concrete defect.

Run: .venv/bin/python scripts/r12_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

CID = "cand-30570d32728a"
REASON = (
    "measured design flaw — r11 §20 pattern battery: pump_park still "
    "drains B_m +487.45 (vol_oscillation +295.76) because the band "
    "centers on a 1000-anchored reverting trend EMA: a PERMANENT level "
    "shift integrates exceedance forever (eternal mis-banding). The "
    "r11 open question ('should the band re-center on an EMA of the "
    "level?') is resolved by measurement — the successor (r12) "
    "re-centers the band via a fast/slow level-EMA divergence gate: "
    "oscillation keeps both EMAs flat (no excess), a permanent shift "
    "yields one bounded re-centering transient, then the band follows "
    "the level."
)


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    cand = db.get_candidate(CID)
    assert cand is not None, CID
    assert cand.status is CandidateStatus.SCORED, f"{CID} is {cand.status}"
    cand.transition(CandidateStatus.SUPERSEDED)
    cand.innovation_claim = (
        f"SUPERSEDED (r12 measured design flaw): {REASON} The r11 "
        "evidence chain stands; the successor re-enters the funnel "
        "with the divergence-gate model."
    )
    db.save_candidate(cand)
    print(f"  {CID} SCORED -> SUPERSEDED  {cand.name}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")


if __name__ == "__main__":
    main()
