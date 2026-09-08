"""Round 20: mint + model the successor (vol-indexed retention ratchet).

Successor: Separation-Keyed Fee Smoothing Escrow — the r13 polarity
fix applied to the vol-indexed retention ratchet: retention keys the
SIGNED separation (fast pressure vs slow regime anchor), so a
crafted up-ramp (premium inflation) retains while the strike's
down-leg (crash cost) releases — a full resonance cycle nets ~zero
by construction instead of over-retaining at the clip ceiling every
ramp phase.

Run: .venv/bin/python scripts/r20_mint.py
"""

from __future__ import annotations

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

PRED_ID = "cand-cd39d95ea572"


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    name = "Separation-Keyed Fee Smoothing Escrow"
    if any(c.name == name for c in db.list_candidates(limit=None)):
        print("  skip (exists)")
        return
    cand = Candidate(
        name=name,
        category="market",
        description=(
            "A fee-smoothing escrow whose retention keys the SIGNED "
            "separation between fast pressure and a slow regime anchor: "
            "sustained premium pressure (up-ramps) raises retention, "
            "crash legs release it, and zero-mean resonance cycles "
            "average OUT instead of over-retaining at a clip ceiling "
            "on every ramp phase."
        ),
        core_mechanism=(
            "Fast pressure EMA vs slow regime EMA; retention = clip("
            "delta + eta * separation / X, 0.1, 0.9) with the SEPARATION "
            "denominated relative; escrow flow symmetric in the same "
            "separation key (inflow and outflow caps mirror); clip "
            "bounds bracket battery scales."
        ),
        problem=(
            "The superseded predecessor's retention keyed ABSOLUTE "
            "realized vol (eta=40 pinned r_t at the 0.9 ceiling through "
            "every crafted ramp) while its outflow term was 0.05*sigma "
            "weaker — every resonance cycle over-retained inflow "
            "monotonically: measured ratchet 285 -> 1321 -> 2143 -> "
            "6479 (linear-unbounded in N, persists under a quiet tail; "
            "r20 measured)"
        ),
        innovation_claim=(
            f"Successor of {PRED_ID} (superseded r20 vol-indexed "
            "retention ratchet). Signed-separation keying: a full "
            "strike-recovery cycle nets ~zero retention by construction "
            "(the r13 polarity fix applied to escrow retention)."
        ),
        inputs=["X_t anchor level", "dX_t level change"],
        outputs=["escrow level", "retention fraction"],
        oracle_required=False, blockchain_required=True, token_required=False,
        source_agent="discovery",
    )
    cand.status = CandidateStatus.RESEARCHING
    db.save_candidate(cand)
    print(f"  {cand.id} <- {PRED_ID}  {cand.name}")


if __name__ == "__main__":
    main()
