"""Round 16: mint the exemplar successor for the demographic-reserve family.

Population-linked reserve rule whose supply state is keyed to a
REVERTING EMA of the level path (the r11 primitive): zero-mean
oscillation washes out, sustained drift carries, no divergence
multiplier on the stock. The 8 other superseded families stay
represented by their healthy corpus relatives (no duplicate minting).

Run: .venv/bin/python scripts/r16_mint.py
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

PRED = "cand-c8aaf4f3244e"


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name = "Reversion-Keyed Demographic Reserve"
    existing = [c for c in db.list_candidates(limit=None) if c.name == name]
    if existing:
        print(f"  skip ({existing[0].id} exists)")
        return
    pred = db.get_candidate(PRED)
    assert pred is not None, PRED
    cand = Candidate(
        name=name,
        category="stablecoin design",
        description=(
            "A population-linked reserve whose supply response is keyed "
            "to a REVERTING EMA of the level path: zero-mean "
            "oscillation washes out of the EMA (no divergence "
            "multiplier harvest), sustained drift carries, and the "
            "stock adjusts by a bounded additive flow instead of a "
            "multiplicative clip-ratchet."
        ),
        core_mechanism=(
            "The reserve tracks a reverting EMA of the signed level "
            "path; supply adjusts additively toward the EMA-implied "
            "target with an asymmetric response band; a small "
            "instantaneous kicker preserves whale-trace distinctness."
        ),
        problem=(
            "The superseded cluster's supply was a multiplicative "
            "function of EMA-vs-level divergence — zero-mean "
            "oscillation harvested the pool -94% (913.5 drawn, r16 "
            "census measured) because every down-leg compounded"
        ),
        innovation_claim=(
            f"Successor of {PRED} ({pred.name}, superseded r16 census: "
            "duplicate-content cluster, EMA-divergence multiplier "
            "collapse). The v1 model keys the response to a reverting "
            "EMA with additive bounded flows — the r11 primitive "
            "applied to the demographic-reserve family."
        ),
        inputs=["X_t population-linked level", "dX_t level change"],
        outputs=["reserve supply response"],
        oracle_required=False,
        blockchain_required=True,
        token_required=False,
        source_agent="discovery",
    )
    cand.status = CandidateStatus.RESEARCHING
    db.save_candidate(cand)
    print(f"  {cand.id} <- {PRED}  {cand.name}")


if __name__ == "__main__":
    main()
