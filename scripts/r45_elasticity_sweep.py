"""r45 elasticity sweep: η ∈ [0, 0.25, 0.5, 0.75, 1.0] across all
composable drivers and scenarios.

The r43 stock layer pinned η=0.5 and measured the feedback
amplification (gamma -> g/(1-η), transiently 2x at η=0.5). This
sweep maps the FULL curve: where does each driver's verdict flip as
elasticity increases? At what η does the reflexive channel turn from
stabilizing (value recovers) to destabilizing (spirals)?

Design contracts:
- Deterministic: same (driver, scenario, eta) -> same floats.
- Uses dataclasses.replace to vary ONLY elasticity; every other
  scenario parameter is held constant (the r22 pattern).
- ALL drivers with a resolvable signal axis are swept (13 of 13 in
  the registry); the 3 that compose as VACUOUS are swept too and
  their vacuity RECORDED at every η — the census MEASURES that
  vacuity is η-invariant instead of assuming it (r46: the original
  docstring claimed they were 'skipped'; the helper checked axis
  resolvability, not composability — nothing was ever skipped).
- §21 census stored idempotently.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from sqlalchemy import text  # noqa: E402

from blockchain_rd_lab.config import REPO_ROOT, load_config  # noqa: E402
from blockchain_rd_lab.database import LabDatabase  # noqa: E402
from blockchain_rd_lab.schemas import ExperimentRecord  # noqa: E402
from blockchain_rd_lab.tokenomics.stock import (  # noqa: E402
    SCENARIOS,
    StockVerdict,
    run_stock_scenario,
)
from blockchain_rd_lab.tokenomics.supply_drivers import DRIVER_REGISTRY  # noqa: E402

ETA_VALUES = (0.0, 0.25, 0.5, 0.75, 1.0)
CENSUS_ID = "r45-elasticity-sweep"


def _has_resolvable_axis(driver_name: str) -> bool:
    """True if the driver's signal axis resolves (a probe exists).

    NOT the same as composability: the stock layer may still return
    VACUOUS (no reference key, unspanned one-sided axis). The sweep
    includes every resolvable driver; vacuous composition is
    recorded, never skipped (r46 F1: this helper was named
    _is_composable and claimed to filter vacuity it did not check)."""
    from blockchain_rd_lab.tokenomics.battery import resolve_signal

    d = next(x for x in DRIVER_REGISTRY if x.name == driver_name)
    return resolve_signal(d) is not None


def run_sweep() -> list[dict]:
    """All composable drivers x all scenarios x all eta values."""
    rows: list[dict] = []
    for d in DRIVER_REGISTRY:
        if not _has_resolvable_axis(d.name):
            continue
        for sc_name, sc in SCENARIOS.items():
            for eta in ETA_VALUES:
                varied = replace(sc, elasticity=eta)
                r = run_stock_scenario(d, varied)
                rows.append(
                    {
                        "driver": d.name,
                        "scenario": sc_name,
                        "eta": eta,
                        "verdict": r.verdict.value,
                        "supply_ratio": round(r.supply_ratio, 6),
                        "demand_ratio": round(r.demand_ratio, 6),
                        "value_ratio": round(r.value_ratio, 6),
                        "tail_drift": round(r.tail_drift, 6),
                        "endogenous_growth": round(
                            r.endogenous_growth, 6
                        ),
                    }
                )
    return rows


def find_flip_points(rows: list[dict]) -> list[dict]:
    """For each (driver, scenario), find the LOWEST η where the
    verdict first becomes a spiral (the flip point). If no flip
    occurs, record the verdict trajectory instead."""
    flips: list[dict] = []
    drivers = sorted({r["driver"] for r in rows})
    scenarios = sorted({r["scenario"] for r in rows})
    spirals = {StockVerdict.SPIRAL_DOWN.value, StockVerdict.SPIRAL_UP.value}

    for drv in drivers:
        for sc in scenarios:
            drv_rows = [
                r
                for r in rows
                if r["driver"] == drv and r["scenario"] == sc
            ]
            drv_rows.sort(key=lambda r: r["eta"])
            trajectory = [
                f"η={r['eta']:.2f}:{r['verdict']}" for r in drv_rows
            ]
            flip_eta = None
            for r in drv_rows:
                if r["verdict"] in spirals:
                    flip_eta = r["eta"]
                    break
            flips.append(
                {
                    "driver": drv,
                    "scenario": sc,
                    "flip_eta": flip_eta,
                    "trajectory": " -> ".join(trajectory),
                }
            )
    return flips


def store_census(rows: list[dict], flips: list[dict]) -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    rec = ExperimentRecord(
        experiment_id=CENSUS_ID,
        candidate_id="cand-9200b07691c3",
        kind="elasticity_sweep",
        timestamp=datetime.now(UTC),
        git_commit="r45",
        parameters={
            "round": 45,
            "battery": "elasticity_sweep_v1",
            "eta_values": list(ETA_VALUES),
            "scenarios": list(SCENARIOS.keys()),
            "drivers": sorted({r["driver"] for r in rows}),
        },
        results={
            "total_runs": len(rows),
            "rows": rows,
            "flip_points": flips,
            "headline_findings": _summarize(flips),
        },
    )
    with db._session() as s:
        s.execute(
            text("DELETE FROM experiments WHERE experiment_id = :eid"),
            {"eid": rec.experiment_id},
        )
    db.save_experiment(rec)
    print(f"stored {rec.experiment_id}: {len(rows)} runs")


def _summarize(flips: list[dict]) -> dict:
    """Key findings from the flip analysis."""
    stable_at_all = [
        f
        for f in flips
        if f["flip_eta"] is None
        and "stable" in f["trajectory"].lower()
    ]
    spiral_at_zero = [
        f for f in flips if f["flip_eta"] == 0.0
    ]
    flip_at_quarter = [
        f for f in flips if f["flip_eta"] == 0.25
    ]
    flip_at_half = [
        f for f in flips if f["flip_eta"] == 0.5
    ]
    flip_at_three_quarter = [
        f for f in flips if f["flip_eta"] == 0.75
    ]
    flip_at_one = [
        f for f in flips if f["flip_eta"] == 1.0
    ]
    never_spiral = [f for f in flips if f["flip_eta"] is None]

    return {
        "never_spiral_count": len(never_spiral),
        "spiral_at_eta_0_count": len(spiral_at_zero),
        "flip_at_eta_0.25_count": len(flip_at_quarter),
        "flip_at_eta_0.5_count": len(flip_at_half),
        "flip_at_eta_0.75_count": len(flip_at_three_quarter),
        "flip_at_eta_1.0_count": len(flip_at_one),
        "stable_everywhere_examples": [
            f"{f['driver']}/{f['scenario']}" for f in stable_at_all[:5]
        ],
        "spiral_everywhere_examples": [
            f"{f['driver']}/{f['scenario']}" for f in spiral_at_zero[:5]
        ],
    }


def main() -> None:
    rows = run_sweep()
    flips = find_flip_points(rows)

    # Print the sweep table
    print(f"{'driver':26s} {'scenario':16s} ", end="")
    for eta in ETA_VALUES:
        print(f"η={eta:<5.2f} ", end="")
    print("flip_η")
    print("-" * 80)

    current_drv = None
    for f in flips:
        if f["driver"] != current_drv:
            current_drv = f["driver"]
            print()
        # get verdicts at each eta
        drv_rows = [
            r
            for r in rows
            if r["driver"] == f["driver"]
            and r["scenario"] == f["scenario"]
        ]
        drv_rows.sort(key=lambda r: r["eta"])
        short_map = {
            "stable": "STAB",
            "rebased_down": "RBDN",
            "rebased_up": "RBUP",
            "spiral_down": "SPDN",
            "spiral_up": "SPUP",
            "vacuous": "VAC",
        }
        print(f"{f['driver']:26s} {f['scenario']:16s} ", end="")
        for r in drv_rows:
            v = short_map.get(r["verdict"], r["verdict"][:4])
            print(f"{v:>7s} ", end="")
        flip_str = (
            f"{f['flip_eta']:.2f}" if f["flip_eta"] is not None else "none"
        )
        print(f"  {flip_str}")

    summary = _summarize(flips)
    print("\n=== Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    store_census(rows, flips)


if __name__ == "__main__":
    main()
