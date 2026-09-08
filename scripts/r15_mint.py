"""Round 15: mint the Level-Recentered Bandwidth Bond Market successor.

The v1 model (authored + smoke-gated in scripts/r15_models.py; the
formalize answer carries it — the r12 no-double-save flow): the
collateral pool C_t follows a SLOW EMA OF THE LEVEL (single magnet,
r12/r13 primitive): |X - C| closes after any permanent shift, the
stress signal s_t keys that closing deviation, and the slash is
bounded to the shift's transient window. A_t (relay allocation)
weights 0.5*E + 0.5*C as before — with C now honestly re-based, A
tracks the level instead of being relatively enriched by an eternal
burn.

Run: .venv/bin/python scripts/r15_mint.py
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

PRED = "cand-b713e862acdc"


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name = "Level-Recentered Bandwidth Bond Market"
    existing = [c for c in db.list_candidates(limit=None) if c.name == name]
    if existing:
        print(f"  skip ({existing[0].id} exists)")
        return
    pred = db.get_candidate(PRED)
    assert pred is not None, PRED
    cand = Candidate(
        name=name,
        category="market design",
        description=(
            "A relay-bandwidth bond market whose collateral pool "
            "follows a slow EMA of the bandwidth level — one magnet, "
            "not two: after a permanent level shift the pool re-bases "
            "and the stress deviation CLOSES, so the slash is bounded "
            "to the shift's transient window instead of burning "
            "forever while allocation holders are relatively enriched."
        ),
        core_mechanism=(
            "Relay peers post collateral into a pool that tracks a "
            "slow EMA of the bandwidth level; a stress signal keys the "
            "pool-level deviation (which closes as the pool re-bases) "
            "and slashes transiently during the re-basing window; the "
            "relay allocation weights escrow demand and the re-based "
            "pool."
        ),
        problem=(
            "Bond-market collateral caught between an anchor magnet "
            "and a level magnet settles between them under permanent "
            "shifts — the deviation never closes and the stress slash "
            "burns forever (r15 measured: 17.7/step standing, A/C "
            "doubles, C_t drawn 179.24 under crash_park)"
        ),
        innovation_claim=(
            f"Successor of {pred.id} (superseded r15 anchor-tug flaw: "
            f"{pred.name}). The mechanism intent is unchanged; the v1 "
            "model gives the pool a single magnet — a slow EMA of the "
            "level — so the stress deviation closes and the slash is "
            "bounded to the re-basing transient."
        ),
        inputs=["X_t bandwidth level", "dX_t level change",
                "posted escrow demand"],
        outputs=["relay allocation", "transient stress slash"],
        oracle_required=False,
        blockchain_required=True,
        token_required=False,
        source_agent="discovery",
    )
    cand.status = CandidateStatus.RESEARCHING
    db.save_candidate(cand)
    print(f"  {cand.id} <- {pred.id}  {cand.name}")


if __name__ == "__main__":
    main()
