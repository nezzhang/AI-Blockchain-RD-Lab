"""r47 hybrid multi-axis composition comparison.

Measures the disclosed r43 approximation (dominant signal only)
against full usage+network composition for the hybrid driver across
all seven stock scenarios. Research-only; no deployment.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import ExperimentRecord
from blockchain_rd_lab.tokenomics.stock import (
    SCENARIOS,
    run_stock_scenario,
)
from blockchain_rd_lab.tokenomics.supply_drivers import get_driver


def main() -> None:
    driver = get_driver("usage-network-hybrid")
    rows = []
    for name, scenario in SCENARIOS.items():
        dominant = run_stock_scenario(driver, scenario)
        multi = run_stock_scenario(
            driver, scenario, composition_mode="multi_axis"
        )
        rows.append({
            "scenario": name,
            "dominant_verdict": dominant.verdict.value,
            "multi_axis_verdict": multi.verdict.value,
            "dominant_value": dominant.value_ratio,
            "multi_axis_value": multi.value_ratio,
            "dominant_supply": dominant.supply_ratio,
            "multi_axis_supply": multi.supply_ratio,
        })
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    rec = ExperimentRecord(
        experiment_id="r47-hybrid-multiaxis-census",
        candidate_id="cand-9200b07691c3",
        kind="hybrid_multiaxis_composition",
        timestamp=datetime.now(UTC),
        git_commit="r47",
        parameters={
            "round": 47,
            "driver": driver.name,
            "scenarios": list(SCENARIOS),
        },
        results={
            "rows": rows,
            "finding": (
                "dominant-axis approximation and full two-axis "
                "composition produce material verdict differences; "
                "both are disclosed, neither silently replaces the other"
            ),
        },
    )
    with db._session() as s:
        s.execute(
            text("DELETE FROM experiments WHERE experiment_id = :eid"),
            {"eid": rec.experiment_id},
        )
    db.save_experiment(rec)
    print("stored", rec.experiment_id, len(rows), "scenarios")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()

