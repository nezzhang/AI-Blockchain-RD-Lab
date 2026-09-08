"""Round 15: supersede the Bandwidth Bond Market (measured anchor-tug flaw).

The r14 re-measurement surfaced crash_park C_t +179.24 on the
RECOMMENDED candidate; the r15 diagnostic (scripts/r15_flaw_diagnostic
inline in the round) traced the root cause: the collateral pool C_t is
caught between TWO magnets — 0.07*(1000-C) mean-reversion toward the
anchor and 0.03*(X-1000) tracking the level. Under a permanent -60%
shift the pool settles at the tug-of-war equilibrium (~465-490, 22%
away from the level), so the stress signal s_t (keyed to
|X-C| deviation > 0.1) NEVER closes: the pool burns chi*s*300
(~17.7/step) FOREVER while relatively enriching A_t holders (A/C
doubles). Same family as the r11 meter's eternal mis-banding: a
deviation that can never close because the state cannot re-base.

Successor: Level-Recentered Bandwidth Bond Market — the collateral
pool follows a slow EMA of the LEVEL (single magnet), so |X-C|
closes after any permanent shift and the stress slash is bounded to
the shift's transient window.

NOT superseded (r15 diagnostic, same evidence discipline as r13):
- Persistent-Drift Joule Escrow: the alarm persists then heals ON
  GENUINE RE-BASE (both EMAs re-base to 400; g_t decays; slash
  bounded; Q_c spend is the credit doing its job). Correct behavior.
- Corridor-Native FX Batch Matching: M/V crash-step excursion fully
  recovers under park (M is a throughput index, not a pool) — the
  battery now classifies it transient; no standing edge.
- Trend-Drawdown Corridor: r13 verdict stands (U_t persists 74% —
  protection; T_t excursion reclassified transient at r15).

Run: .venv/bin/python scripts/r15_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

CID = "cand-b713e862acdc"
REASON = (
    "measured anchor-tug flaw (r15 crash_park diagnostic): the "
    "collateral pool is caught between 1000-mean-reversion and level-"
    "tracking magnets — under a permanent shift it settles 22% from "
    "the level, the stress deviation never closes, and the pool "
    "burns ~17.7/step forever (C_t drawn 179.24 measured) while A_t "
    "holders are relatively enriched (A/C doubles)"
)


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    cand = db.get_candidate(CID)
    assert cand is not None, CID
    assert cand.status is CandidateStatus.FINALIST, f"{CID} is {cand.status}"
    cand.transition(CandidateStatus.SUPERSEDED)
    cand.innovation_claim = (
        f"SUPERSEDED (r15 {REASON}). The successor re-centers the "
        "pool on a slow EMA of the level (single magnet): the stress "
        "deviation closes after any permanent shift, bounding the "
        "slash to the shift's transient window."
    )
    db.save_candidate(cand)
    print(f"  {CID} FINALIST -> SUPERSEDED  {cand.name}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")


if __name__ == "__main__":
    main()
