"""Round 13 diagnostic: the anchor-heal flaw in the r11 anchored-trend siblings.

Hypothesis: all three r11 siblings key their protection to a trend EMA
that REVERTS TO THE 1000 ANCHOR (T_t1 = T_t + kappa*((1000 + (dX/X)*1000)
- T_t)). When moves STOP — crash then park — the EMA's input target is
1000 (dX=0 → target 1000), so T heals back to 1000 while the LEVEL
stays moved. Every protection keyed to |T-1000| or max(0, 1000-T) decays
to zero exactly when the regime has permanently shifted. The r10
choreographies (wash / pump-unwind / shock-timing) all move repeatedly
or revert; NONE is move-once-then-park — the flaw is invisible to the
§20 battery by construction.

An attacker: crash the level (or wait for a real crash), park, then buy
protection cheap while tail risk is maximal. Also probes: after-park
re-raise (protection reprices on noise, not on the moved level) and
graded-crash (ramp down over several steps then park).

Run: .venv/bin/python scripts/r13_heal_diagnostic.py
"""

from __future__ import annotations

import json

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.simulation import MechanismSimulation

SIBLINGS = {
    "cand-b2b411464015": ("Trend-Indexed Prediction-Fee Oracle", ["T_t", "R_t", "O_t", "F_t"]),
    "cand-8212f81f4f75": ("Drift-Gap Joule Escrow", ["T_t", "P_e", "J_t", "a_t"]),
    "cand-31dd017e61de": ("Trend-Drawdown Liquidity Corridor", ["T_t", "D_t", "U_t"]),
}


def series_crash_park(steps: int = 120, at: int = 20, to: float = 400.0) -> list[dict[str, float]]:
    """One-shot -60% crash at `at`, then parked at `to` forever."""
    rows = []
    for t in range(steps):
        if t < at:
            rows.append({"X_t": 1000.0, "dX_t": 0.0})
        elif t == at:
            rows.append({"X_t": to, "dX_t": to - 1000.0})
        else:
            rows.append({"X_t": to, "dX_t": 0.0})
    return rows


def series_ramp_park(
    steps: int = 120, at: int = 20, n: int = 10, to: float = 400.0
) -> list[dict[str, float]]:
    """Graded crash: -60% spread over n steps (no single |dX| spike), then park."""
    s: list[dict[str, float]] = []
    level = 1000.0
    for t in range(steps):
        if t < at:
            s.append({"X_t": 1000.0, "dX_t": 0.0})
        elif t < at + n:
            prev = level
            level = 1000.0 + (to - 1000.0) * (t - at + 1) / n
            s.append({"X_t": level, "dX_t": level - prev})
        else:
            s.append({"X_t": to, "dX_t": 0.0})
    return s


def diagnosis(model: MathModel, series: list[dict[str, float]], keyed: list[str]):
    """Return (at-crash values, parked values) of the keyed states."""
    run = MechanismSimulation(model).run(series)
    hist = run.history
    crash_idx = next(i for i, h in enumerate(hist) if h["dX_t"] < -50.0)
    crash = {k: hist[crash_idx][k] for k in keyed}
    parked = {k: hist[-1][k] for k in keyed}
    # also: level displacement persisted
    return crash, parked, hist[crash_idx]["X_t"], hist[-1]["X_t"]


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for cid, (name, keyed) in SIBLINGS.items():
        model = MathModel.model_validate(json.loads(db.get_latest_math_model(cid)))
        print("=" * 74)
        print(f"{cid}  {name}")
        for label, series in [("one-shot crash & park", series_crash_park()),
                              ("graded crash & park", series_ramp_park())]:
            crash, parked, xc, xe = diagnosis(model, series, keyed)
            print(f"  [{label}]  X: {xc:.0f} -> {xe:.0f} (level stays moved)")
            for k in keyed:
                c, p = crash[k], parked[k]
                # decay ratio: how much of the crash-time signal survived parking
                ratio = abs(p) / abs(c) if abs(c) > 1e-9 else float("nan")
                print(f"    {k:>5s}: crash {c:9.2f} -> parked {p:9.2f}   "
                      f"survival {ratio:.3f}")
        print()


if __name__ == "__main__":
    main()
