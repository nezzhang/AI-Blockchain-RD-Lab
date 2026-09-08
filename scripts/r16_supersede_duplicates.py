"""Round 16b: the duplicate-content census supersession (r7 precedent, 2.5x scale).

The formal duplicate-content census (equation-set signature over the
ranked corpus) found TWENTY candidates sharing ONE identical equation
set — the pre-r10 corpus block: Demographic Reserve Rule x5,
Carbon-Weighted Gas Fees x4, Habitat Bond Curve x4, Labor-Backed
Escrow x2, Commodity-Volatility Stable Unit x2, Population-Linked
Supply, Bandwidth Futures Market, AI-Compute Denominated Debt.

All 20 score identically 5.050 (the imputed-median floor: 5 of 11
dimensions imputed on duplicated evidence) — 41% of ranked slots,
three holding FINALIST positions. This is the r7 vacuum finding at
larger scale, and the hidden driver behind the curriculum guard's
'dominant family 19-21%' readings.

Disposition: keep ONE exemplar (cand-1acbaa9de0b0, the first of the
group in rank order — all tie at 5.050; the ranking's own name-asc
tiebreak), supersede the other 19 with duplicate-content lineage.
The mechanism family already carries an honest successor from this
round (Reversion-Keyed Demographic Reserve, cand-47c62aa507b4, 6.25 —
the additive-flow + reverting-EMA primitive, worst battery edge
12.42 vs the duplicated form's 913.5-family behavior).

Run: .venv/bin/python scripts/r16_supersede_duplicates.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

KEEP = "cand-1acbaa9de0b0"
SUPERSEDE = [
    "cand-e33c18c7a75e", "cand-81eece8ab470", "cand-84b0ad6d012f",
    "cand-6aff3509aeaf", "cand-fb4bfe53914b", "cand-58d7091eb2a7",
    "cand-045642b91848", "cand-d14a12373eb5", "cand-6e9dedb8b844",
    "cand-b8188890330a", "cand-986c8dd65b08", "cand-ebab7a8e41db",
    "cand-e0c39af1bd66", "cand-c7118453cf48", "cand-274537b6fc9c",
    "cand-6aa7f2eaaac0", "cand-a9105451d386", "cand-0bd19afa908c",
    "cand-02bfb7635ef0",
]
REASON = (
    "duplicate-content census (r16): identical equation set shared by "
    "20 ranked candidates — one copy-pasted pre-r10 model occupying "
    "41% of ranked slots at the 5.050 imputed-score floor; the family's "
    "honest successor is cand-47c62aa507b4 (Reversion-Keyed "
    "Demographic Reserve, 6.25, worst battery edge 12.42)"
)


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for cid in SUPERSEDE:
        cand = db.get_candidate(cid)
        assert cand is not None, cid
        assert cand.status in (CandidateStatus.SCORED, CandidateStatus.FINALIST), (
            f"{cid} is {cand.status}"
        )
        cand.transition(CandidateStatus.SUPERSEDED)
        cand.innovation_claim = f"SUPERSEDED (r16 duplicate census): {REASON}"
        db.save_candidate(cand)
        print(f"  {cid} -> SUPERSEDED  {cand.name[:44]}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")
    print(f"kept exemplar: {KEEP}")


if __name__ == "__main__":
    main()
