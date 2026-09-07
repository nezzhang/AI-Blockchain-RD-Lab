"""Round 11 part 1: supersede finalists carrying measured §20 residuals.

The r10 AttackPatternBattery measured concrete attacker edges against
these 4 finalists' final models (persisted §21 records, disclosed in
release §4b). Per §11 the only legal exit from FINALIST is SUPERSEDED;
successors are minted (part 2, r11_mint.py) whose v1 models carry the
pattern-discrimination patches (directional-sustained EMA responses in
place of instantaneous |dX| responses), and re-enter the funnel to
build the fresh evidence chain.

This is NOT an evidence-invalidity supersede (the r7 case): these
finalists' §15/§20 evidence stands. The supersede reason records the
MEASURED adversarial residual that a corrected successor addresses.

Run: .venv/bin/python scripts/r11_supersede.py
"""

from __future__ import annotations

from blockchain_rd_lab.archive import ArchiveBuilder
from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import CandidateStatus

# measured §20 edges (r10 §21 records, release §4b numbers)
SUPERSEDE_SET: dict[str, str] = {
    "cand-cab81fc40bbf": (
        "measured adversarial residual — r10 §20 pattern battery: attacker "
        "edge +14.75 (pump_unwind, F_l fee ladder) / +6.90 (wash_flow) / "
        "+6.32 (vol_oscillation) / +1.94 (shock_timing, O_p): crafted vol "
        "inflates the open-interest index above honest open interest and "
        "harvests fee-ladder discounts; the v2 model keys O_p to "
        "instantaneous |dX|, which zero-mean oscillation pumps. Successor "
        "keys the index to a directional-sustained EMA of signed moves."
    ),
    "cand-e98e5859f3f5": (
        "measured adversarial residual — r10 §20 pattern battery: attacker "
        "edge +351.83 (pump_unwind, J_t escrow) / +288.85 (vol_oscillation): "
        "crafted vol spikes the attest-gap measure and slashes honest "
        "providers' escrow; the v2 model keys a_t to instantaneous "
        "|dX|/X spikes. Successor keys the gap to directional-sustained "
        "divergence between anchor and energy index."
    ),
    "cand-52eeaf35607b": (
        "measured adversarial residual — r10 §20 pattern battery: attacker "
        "edge +700.00 (vol_oscillation / wash_flow / pump_unwind, B_m bond "
        "pool): crafted vol drives |dX|/X past the mis-band every step, "
        "forfeiting reporter bonds to the floor while the stabilization "
        "pool pays out — wash-flow extraction of collateral. Successor "
        "keys forfeiture to integrated (EMA) mis-banding, so only "
        "sustained mis-banding drains bonds."
    ),
    "cand-f8fc37dce6a1": (
        "measured adversarial residual — r10 §20 pattern battery: attacker "
        "edge +784.99 (shock_timing, U_t tranche capacity) / +241.91 "
        "(vol_oscillation) / +228.85 (wash_flow) / +77.72 (pump_unwind): "
        "crafted |dX| spikes pump the drawdown state, which drains "
        "tranche capacity on oscillation that never sustained a trend. "
        "Successor keys drawdown to a directional-sustained EMA of signed "
        "relative moves."
    ),
}


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for cid, reason in SUPERSEDE_SET.items():
        cand = db.get_candidate(cid)
        assert cand is not None, f"{cid} missing"
        assert cand.status is CandidateStatus.FINALIST, (
            f"{cid} is {cand.status}, expected FINALIST"
        )
        cand.transition(CandidateStatus.SUPERSEDED)
        # lineage: the supersede reason lives in innovation_claim (r7
        # convention — the dossier renders it; §26 archive records it too)
        cand.innovation_claim = (
            f"SUPERSEDED (r11 measured adversarial residual): {reason} "
            "Original §15/§20 evidence stands (r7-successor chain); the "
            "successor re-enters the funnel with a corrected model."
        )
        db.save_candidate(cand)
        print(f"  {cid} FINALIST -> SUPERSEDED  {cand.name[:46]}")
    summary = ArchiveBuilder(db).build(REPO_ROOT / "ideas")
    print(f"§26 archive rebuilt: {summary.rejected_indexed} entries")


if __name__ == "__main__":
    main()
