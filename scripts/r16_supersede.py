"""Round 16: the convergence census supersession set (§11, r7 precedent).

The r16 corpus-wide census under the FINAL battery (r13/r14/r15
classifications) found 9 SCORED candidates carrying pool-collapse
edges authored under the pre-r10 formalization era (vacuous-era
evidence occupying ranking slots):

- 6 candidates share IDENTICAL equation sets (duplicate content from
  the r8/r9 bridge batches): S_t = S_t*(1 + clip(alpha*(X_smooth -
  X)/X, ...)) — an EMA-divergence multiplier that collapses the pool
  -94% under vol_oscillation (1000 -> 60 measured). The r11
  remediation pass touched only the then-finalists; these stayed.
  Members: Demographic Reserve Rule x3 (cand-c8aaf4f3244e v2,
  cand-dc109b36cd60 v4 [malformed: X_smooth defined thrice],
  cand-e37c1f655db5 v2), Carbon-Weighted Gas Fees x2
  (cand-afe909352ab4 v2, cand-f84653a7fb9c v2), Habitat Bond Curve
  (cand-a4e0cf125cdf v2).
- Attestation-Locked Prediction Settlement v2 (cand-273882700f28):
  A_b drawn 700 under pump_unwind (attestation bond collapse).
- Fee-Tier Voted Model Registry v2 (cand-771f66f9de0a): H_t drawn
  494.7 under vol_oscillation.
- Vol-Adaptive Market Making Rebate Curve v2 (cand-27e6a6ae5492):
  drawn 386.2 under vol_oscillation.

All 9 are superseded with the measured edge recorded as lineage. ONE
exemplar successor (the demographic-reserve family) is minted with
the r11 primitive (reverting-EMA + asymmetric response) closing the
divergence harvest. Not superseded: the <400 tier are successors
carrying honest DISCLOSED residuals (allocation pass-through, mutual
drawdown), the §27 4b publishes every one.

Run: .venv/bin/python scripts/r16_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

SUPERSEDE = {
    "cand-c8aaf4f3244e": "duplicate-content cluster: EMA-divergence "
                          "multiplier collapses S_t -94% under "
                          "vol_oscillation (913.5 drawn, measured)",
    "cand-dc109b36cd60": "duplicate-content cluster + malformed v4 "
                         "(X_smooth defined thrice); same -94% collapse",
    "cand-e37c1f655db5": "duplicate-content cluster: same -94% collapse",
    "cand-afe909352ab4": "duplicate-content cluster: same -94% collapse",
    "cand-f84653a7fb9c": "duplicate-content cluster: same -94% collapse",
    "cand-a4e0cf125cdf": "duplicate-content cluster: same -94% collapse",
    "cand-273882700f28": "attestation bond A_b collapses 700 under "
                         "pump_unwind (measured)",
    "cand-771f66f9de0a": "H_t drawn 494.7 under vol_oscillation "
                         "(measured)",
    "cand-27e6a6ae5492": "drawn 386.2 under vol_oscillation (measured)",
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
        cand.innovation_claim = f"SUPERSEDED (r16 census): {reason}"
        db.save_candidate(cand)
        print(f"  {cid} -> SUPERSEDED  {cand.name[:44]}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")


if __name__ == "__main__":
    main()
