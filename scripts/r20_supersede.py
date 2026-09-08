"""Round 20: resonance disposition.

The r20 pattern (N strike-cycles at the model's recovery cadence,
matched base = one late cycle at identical final-cycle timing)
found two confirmed flaw classes among the 27 ranked, both
invisible to every prior battery pattern because DEPTH metrics are
structurally blind to repetition (a bounded per-cycle drain
returns to the same level each cycle; only the per-state FLOW
volume and the window-END ratchet vs base see it):

1. Vol-Weighted Fee Smoothing Escrow (cand-cd39d95ea572, FINALIST):
   vol-indexed retention ratchet — retention keys ABSOLUTE
   realized vol (eta=40 pins r_t at the 0.9 ceiling through every
   crafted ramp) while the outflow term is 0.05*sigma weaker, so
   every cycle over-retains monotonic. Measured: 285 -> 1321 ->
   2143 -> 6479 (linear-unbounded in N), persists under a quiet
   tail (1321 -> 1081). SUPERSeded; successor
   Separation-Keyed Fee Smoothing Escrow (cand-9200b07691c3)
   through the full §34 loop (v1 VULNERABLE saw-tooth -> v2
   symmetric band + magnitude counter, honestly re-broken ->
   v3 sign-persistence counter SURVIVES; 6.45, above its
   predecessor).

2. AI-Compute Denominated Debt (cand-1acbaa9de0b0, the r16
   duplicate-block exemplar, FINALIST): the multiplicative-supply
   r16 class at resonance scale — S_t1 = S_t*(1+g_t) compounds
   every recovery ramp (13 consecutive same-sign steps per cycle;
   no prior pattern had them). Measured: 3583 -> 24352 -> 666931
   (exponential in N), persists. SUPERSeded; the class's r16
   successor (Reversion-Keyed Demographic Reserve, additive flows,
   resonance-healthy 32.6) already carries the fix lineage — no
   second mint (one exemplar successor per flaw class, r16).

Transit classifications (the quiet-tail layer, r19 discipline
applied to repetition): Relay Congestion Cover Mesh 362 -> 0.0,
Counter-Cyclical Fee Sink Insurer 310 -> 0.0, Persistent-Drift
Joule Escrow 304 -> 111.6 (its disclosed U_s lag) — all three gaps
CLOSE under 40 quiet steps; the r18/r19 successors and the
recommended candidate all classify healthy.

Run: .venv/bin/python scripts/r20_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

SUPERSEDE = {
    "cand-cd39d95ea572":
        "vol-indexed retention ratchet (r20 resonance): retention "
        "keys ABSOLUTE realized vol (eta=40 pins r_t at the 0.9 "
        "ceiling through every crafted recovery ramp) while the "
        "outflow term is 0.05*sigma weaker — every strike-recovery "
        "cycle over-retains monotonic: measured 285 -> 1321 -> 2143 "
        "-> 6479 (linear-unbounded in N), persisting under a quiet "
        "tail (1321 -> 1081); invisible to every prior pattern "
        "(depth metrics are blind to repetition). Successor "
        "cand-9200b07691c3 (separation-keyed retention, symmetric "
        "band, sign-persistence counter) SURVIVES at 6.45",
    "cand-1acbaa9de0b0":
        "multiplicative-supply ratchet at resonance scale (r20): the "
        "r16 duplicate-block exemplar kept the family's S_t1 = "
        "S_t*(1+g_t) compounding form — every resonance recovery "
        "ramp is 13 consecutive same-sign growth steps, so each "
        "cycle compounds the supply again: measured 3583 -> 24352 "
        "-> 666931 (exponential in N), persisting under quiet. No "
        "prior pattern had consecutive same-sign recovery steps, so "
        "the r16 finding measured only the oscillation leg. The "
        "class successor (cand-47c62aa507b4, additive flows) "
        "already carries the fix lineage — no second mint (r16 "
        "exemplar discipline)",
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
        cand.innovation_claim = f"SUPERSEDED (r20 resonance): {reason}"
        db.save_candidate(cand)
        print(f"  {cid} -> SUPERSEDED  {cand.name[:44]}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")


if __name__ == "__main__":
    main()
