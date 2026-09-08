"""Round 13: mint the two persistent-EMA successors.

Successors of the anchor-heal siblings (see r13_supersede.py). The v1
models apply the r12 primitive with INSURANCE POLARITY — the slow EMA
of the LEVEL (not a 1000-anchored trend) so that:
  - oscillation / wash: the level EMA stays ~flat -> no premium
    harvest (the r11 wash-immunity is preserved)
  - crash then park: the level EMA MOVES to the new level and STAYS
    displaced -> cover stays priced up while tail risk is maximal
    (the r13 fix — protection persists because the level persists)
  - recovery: the EMA follows the level back down

Polarity vs the r12 meter: the meter's exceedance INTENDS to heal after
re-banding (transient semantics); insurance/alarm states must NOT heal
(persistent semantics). Same primitive, opposite polarity, chosen by
what each mechanism measures.

  1. Persistent-Trend Prediction-Fee Oracle (pred b2b411464015):
     O_t open interest, F_t fee = level-displacement premium
     (|L_t-1000| keyed, L_t = slow level EMA, wide clip) + open-
     interest fallback + fast-EMA kicker for crash-timing response.
  2. Persistent-Drift Joule Escrow (pred 8212f81f4f75):
     P_e energy price, J_t escrow, a_t alarm keyed to the persistent
     level-EMA displacement with a ratcheting tolerance (chi shrinks
     with escrow turnover — r11 v2 discipline).

Status: RESEARCHING (prior research on the IDEA stands).

Run: .venv/bin/python scripts/r13_mint.py (mints + authors v1 models
— NOT stored; the formalize answer carries them, per the r12 lesson)
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

SPECS: list[dict[str, object]] = [
    {
        "pred": "cand-b2b411464015",
        "name": "Persistent-Trend Prediction-Fee Oracle",
        "description": (
            "A prediction-fee oracle whose fee premium keys a slow EMA "
            "of the realized LEVEL — not a 1000-anchored trend — so cover "
            "stays priced up while the regime stays moved: a crashed-and-"
            "parked market pays crash-level fees forever, oscillation "
            "pays none, and recovery reprices down as the level recovers."
        ),
        "mechanism": (
            "Traders post open interest against the oracle's fee quote; "
            "the fee reads the persistent displacement |L - 1000| of a "
            "slow level-EMA (insurance polarity: displacement persists "
            "while the regime persists) plus an open-interest fallback "
            "term and a fast-EMA kicker for crash-window response."
        ),
        "problem": (
            "Tail-risk cover priced off anchored trend EMAs heals to "
            "anchor-normal levels right after a permanent crash — the "
            "r13 measured flaw: cover sold at 7% of its crash premium "
            "while the level stayed -60% moved"
        ),
    },
    {
        "pred": "cand-8212f81f4f75",
        "name": "Persistent-Drift Joule Escrow",
        "description": (
            "An energy-delivery escrow whose slash alarm keys the "
            "persistent displacement of a slow level-EMA — not an "
            "anchored trend — so a permanently-drifted regime keeps the "
            "alarm on: defaults timed to 'healed' windows still pay the "
            "slash premium, while oscillation never trips the alarm."
        ),
        "mechanism": (
            "Providers post joule-denominated escrow; the alarm reads "
            "|L - 1000| (slow level-EMA displacement) against a "
            "ratcheting tolerance that shrinks with escrow turnover; "
            "alarmed escrow slashes at psi per step into the counterparty "
            "pool until delivery resumes at the NEW level."
        ),
        "problem": (
            "Drift-gap alarms keyed to anchored trend EMAs fire ~4 steps "
            "then heal under a permanently moved regime — defaults timed "
            "to the healed window pay no slash premium (the r13 "
            "measured flaw)"
        ),
    },
]


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for spec in SPECS:
        name = str(spec["name"])
        existing = [c for c in db.list_candidates(limit=None) if c.name == name]
        if existing:
            print(f"  skip ({existing[0].id} exists)")
            continue
        pred = db.get_candidate(str(spec["pred"]))
        assert pred is not None, spec["pred"]
        cand = Candidate(
            name=name,
            category="oracle design",
            description=str(spec["description"]),
            core_mechanism=str(spec["mechanism"]),
            problem=str(spec["problem"]),
            innovation_claim=(
                f"Successor of {pred.id} (superseded r13 anchor-heal "
                f"flaw: {pred.name}). Intent unchanged; the v1 model "
                "keys protection to a persistent slow EMA of the LEVEL "
                "(r12 primitive, insurance polarity — displacement "
                "persists while the regime persists)."
            ),
            inputs=["X_t anchor price level", "dX_t anchor change",
                    "posted open interest / escrow"],
            outputs=["fee premium or slash rate", "pooled cover"],
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
