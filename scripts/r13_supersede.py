"""Round 13: supersede the two anchor-heal siblings (measured lineage).

Evidence (scripts/r13_heal_diagnostic.py + the new CRASH_PARK battery
pattern, heal_flags displacement ratios):

- Trend-Indexed Prediction-Fee Oracle (cand-b2b411464015): fee F_t heals
  to 7% of peak displacement while the level stays -60% moved — tail
  cover sold at anchor-normal premium exactly when tail risk is
  maximal. Root cause: F keys |R_t-1000| / |T_t-1000|, and the trend
  EMAs revert to the 1000 anchor once moves stop (dX=0 -> target 1000).
- Drift-Gap Joule Escrow (cand-8212f81f4f75): the drift-gap slash
  alarm a_t fires 4 steps then heals to 0 under a permanently moved
  regime — a default timed to the healed window pays no slash premium.
  Root cause: a_t keys |T_t-1000| (anchored trend), same class.

NOT superseded (the hypothesis was 3/3; the evidence says 2/3):
- Trend-Drawdown Liquidity Corridor (cand-31dd017e61de): capacity U_t
  retains 74% of displacement (stays -300, tracking the moved level via
  its level term 1000 + 0.5*(X-1000)) — an insurance corridor SHOULD
  contract capacity after a crash; protection persists. No flaw.
- Divergence-Gated Fee Band Meter (cand-a9f161bde5a8, r12): E_t heals
  BY DESIGN (the band re-centered; exceedance genuinely stops). The
  intended transient semantics of a re-banding meter.

Run: .venv/bin/python scripts/r13_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

REASON = (
    "measured anchor-heal flaw (r13 CRASH_PARK battery pattern): "
    "protection keyed to a 1000-anchored reverting trend EMA heals to "
    "the anchor once moves stop, while a permanently-shifted regime "
    "stays moved — tail cover / slash premium decays to zero exactly "
    "when risk is maximal"
)


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for cid, detail in [
        ("cand-b2b411464015",
         "fee F_t heals to 7% of peak displacement while the level "
         "stays -60% moved (heal_flags F_t=0.069)"),
        ("cand-8212f81f4f75",
         "drift-gap slash alarm a_t fires 4 steps then heals to 0 "
         "under the moved regime — defaults timed to healed windows "
         "pay no slash premium"),
    ]:
        cand = db.get_candidate(cid)
        assert cand is not None, cid
        assert cand.status in (CandidateStatus.FINALIST, CandidateStatus.SCORED), (
            f"{cid} is {cand.status}"
        )
        cand.transition(CandidateStatus.SUPERSEDED)
        cand.innovation_claim = (
            f"SUPERSEDED (r13 {REASON}): {detail}. The successor keys "
            "protection to a persistent slow EMA of the LEVEL (r12 "
            "primitive, insurance polarity: stays displaced while the "
            "regime stays moved)."
        )
        db.save_candidate(cand)
        print(f"  {cid} -> SUPERSEDED  {cand.name}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")


if __name__ == "__main__":
    main()
