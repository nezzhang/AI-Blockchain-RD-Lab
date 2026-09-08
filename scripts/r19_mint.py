"""Round 19: mint + model the successor (floor-below-crash-level).

Successor: Regime-Indexed Compute Wage Pool — the r15 fix discipline
applied to a productivity-indexed wage pool: the pool re-centers on
a slow EMA of the level (single magnet), flows symmetrically
step-capped, and the clip FLOOR sits BELOW the deepest battery crash
level (250 < 400) so the pool can reach the moved regime instead of
pinning above it.

Run: .venv/bin/python scripts/r19_mint.py
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

PRED_ID = "cand-9af3c61061d1"


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name = "Regime-Indexed Compute Wage Pool"
    if any(c.name == name for c in db.list_candidates(limit=None)):
        print("  skip (exists)")
        return
    cand = Candidate(
        name=name,
        category="productivity",
        description=(
            "A productivity-indexed compute wage pool that RE-CENTERS "
            "on the moved regime: the pool target is a slow EMA of the "
            "level (single magnet — no anchor tug-of-war), wage flows "
            "are symmetrically step-capped, and the clip floor sits "
            "BELOW the deepest battery crash level so the pool can "
            "reach the moved regime instead of pinning above it."
        ),
        core_mechanism=(
            "Pool follows a slow level EMA (kappa_w); wage flow = "
            "clip(level deviation, -step_w, +step_w) symmetric; clip "
            "bounds 250..4000 bracket the battery extremes; a small "
            "delivery kicker keeps whale-trace."
        ),
        problem=(
            "The superseded predecessor's wage pool floor (600) sat "
            "ABOVE the -60% crash level (400): the flow was "
            "symmetrically capped but the floor blocked re-basing, so "
            "the pool pinned at 600 under the moved regime — 400 "
            "standing, window-verified at 120/240 steps (r19 measured; "
            "the r15 bandwidth-bond flaw family)"
        ),
        innovation_claim=(
            f"Successor of {PRED_ID} (superseded r19 floor-above-"
            "crash-level). Floor 250 < crash 400: the pool re-bases by "
            "construction (the r15 fix discipline)."
        ),
        inputs=["X_t anchor level", "dX_t level change"],
        outputs=["wage pool level", "wage flow"],
        oracle_required=False, blockchain_required=True, token_required=False,
        source_agent="discovery",
    )
    cand.status = CandidateStatus.RESEARCHING
    db.save_candidate(cand)
    print(f"  {cand.id} <- {PRED_ID}  {cand.name}")


if __name__ == "__main__":
    main()
