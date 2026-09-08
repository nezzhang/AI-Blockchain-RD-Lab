"""Round 18: mint the two class successors (r16 exemplar discipline).

Class A (anchor-heal) -> Three-Speed Adverse-Selection Premium:
the r13 insurance-polarity construction (fast kicker + medium EMA +
ultra-slow regime anchor; gate = |medium - anchor|/anchor) applied
to adverse-selection cover: smooth regimes track together (no false
premium), a moved regime keeps the gate open persistently (cover
stays priced while risk stays moved), oscillation flattens both
speeds (no wash harvest).

Class B (uncapped outflow) -> Symmetric-Cap Fee Recycle Reserve:
the inflow cap mirrored as an outflow floor — the pool can neither
fill nor bleed faster than its declared rate, so a sub-anchor regime
taxes the pool at a bounded rate instead of draining it to the floor.

Run: .venv/bin/python scripts/r18_mint.py
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

CLASS_A_PRED = "cand-6b5791c8ae9c"
CLASS_B_PRED = "cand-e626f13713b0"


def _mint(db: LabDatabase, name: str, category: str, desc: str,
          mech: str, problem: str, claim: str, pred_id: str) -> None:
    existing = [c for c in db.list_candidates(limit=None) if c.name == name]
    if existing:
        print(f"  skip ({existing[0].id} exists)")
        return
    cand = Candidate(
        name=name, category=category, description=desc,
        core_mechanism=mech, problem=problem, innovation_claim=claim,
        inputs=["X_t anchor level", "dX_t level change"],
        outputs=["premium/flow response"],
        oracle_required=False, blockchain_required=True, token_required=False,
        source_agent="discovery",
    )
    cand.status = CandidateStatus.RESEARCHING
    db.save_candidate(cand)
    print(f"  {cand.id} <- {pred_id}  {cand.name}")


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)

    _mint(
        db,
        name="Three-Speed Adverse-Selection Premium",
        category="prediction market",
        desc=(
            "Adverse-selection cover priced by a THREE-SPEED gate: a fast "
            "kicker, a medium adverse-intensity EMA, and an ultra-slow "
            "regime anchor. The premium keys |medium - anchor|/anchor: "
            "smooth regimes track together (no false premium), a "
            "permanently moved regime keeps the gate open PERSISTENTLY "
            "(cover stays priced while risk stays moved — the r13 "
            "insurance polarity), zero-mean oscillation flattens both "
            "EMAs (no wash harvest)."
        ),
        mech=(
            "Adverse-selection intensity flows into a medium EMA; the "
            "ultra-slow anchor EMA filters regime from noise; the "
            "premium = base + gain*separation, clipped; a small "
            "fast-vs-medium kicker preserves whale-trace."
        ),
        problem=(
            "The superseded predecessor's intensity and allocation "
            "states healed to their 1000 anchor exactly while the "
            "regime stayed -60% moved (heal 0.0, excursion 750 "
            "measured) — tail cover unpriced exactly when tail risk "
            "is maximal (the r18 compound-census anchor-heal finding)"
        ),
        claim=(
            f"Successor of {CLASS_A_PRED} (superseded r18 anchor-heal "
            "class). The r13 three-speed insurance polarity applied to "
            "adverse-selection cover: persistent displacement under "
            "moved regimes by construction."
        ),
        pred_id=CLASS_A_PRED,
    )

    _mint(
        db,
        name="Symmetric-Cap Fee Recycle Reserve",
        category="fee mechanism",
        desc=(
            "A fee-recycle reserve whose flows are SYMMETRICALLY capped: "
            "the inflow cap mirrored as an outflow floor. The pool can "
            "neither fill nor bleed faster than its declared rate — a "
            "sub-anchor regime taxes the reserve at a bounded rate "
            "instead of draining it to the clip floor."
        ),
        mech=(
            "Net flow = clip(rate*(X - anchor), -cap, +cap): the same "
            "cap bounds both directions; the reserve mean-reverts to "
            "its target; a small recycle kicker keeps whale-trace."
        ),
        problem=(
            "The superseded predecessor capped its INFLOW (min(200, "
            "0.10*(X-1000))) but left the OUTFLOW uncapped below the "
            "anchor: any sub-1000 regime bled the pool to its 400 "
            "floor, 509.7 standing under crash_park (the r18 "
            "floor-pin-drain finding, hidden by the pin-coincident "
            "arrival misclassification)"
        ),
        claim=(
            f"Successor of {CLASS_B_PRED} (superseded r18 standing "
            "floor-pin drain). The symmetric cap removes the min() "
            "asymmetry: bounded bleed both directions by construction."
        ),
        pred_id=CLASS_B_PRED,
    )


if __name__ == "__main__":
    main()
