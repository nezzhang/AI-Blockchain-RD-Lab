"""Round 10: adversarial residual bounding for the 9 finalists.

Runs the §20 AttackPatternBattery (vol_oscillation, wash_flow,
pump_unwind, shock_timing) against each finalist's FINAL model version
and persists the results as §21 ExperimentRecords — the quantitative
residual the release package's §4 disclosure can cite (bounded by
measurement, not by claim).

Honesty rules (§20):
- headline=None + vacuous=True means the model saturated (no measurable
  edge) — NEVER reported as "bounded by zero".
- The edge is attacker-favorable by construction; a negative edge means
  the pattern HURT the attacker relative to a matched base run.
"""

from __future__ import annotations

import json
import sys

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import ExperimentRecord, LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.schemas import CandidateStatus
from blockchain_rd_lab.simulation.adversarial import AttackPatternBattery
from blockchain_rd_lab.simulation.service import (
    SIMULATION_VERSION,
    _git_commit,
    utcnow,
)


def main(store: bool = False) -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    finalists = [
        c for c in db.list_candidates(limit=None)
        if c.status is CandidateStatus.FINALIST
    ]
    finalists.sort(key=lambda c: (-(c.overall_score or 0.0), c.name))
    print(f"finalists: {len(finalists)}")
    if not finalists:
        return

    failures = []
    for cand in finalists:
        model_json = db.get_latest_math_model(cand.id)
        if model_json is None:
            failures.append((cand.id, "no stored model"))
            continue
        model = MathModel.model_validate(json.loads(model_json))
        battery = AttackPatternBattery(model)
        bounds = battery.run_all(steps=60)

        # Summarize honestly: headline None → vacuous (never "0.0").
        lines = []
        vacuous = 0
        for b in bounds:
            if b.vacuous or b.headline is None:
                vacuous += 1
                lines.append(f"  {b.kind.value:16s} VACUOUS (no measurable edge)")
            elif b.headline == 0.0:
                # measured: metrics extracted, no positive attacker edge
                measured = ", ".join(sorted(b.edge)) or "none"
                lines.append(f"  {b.kind.value:16s} BOUNDED-0 (measured: {measured})")
            else:
                lines.append(
                    f"  {b.kind.value:16s} headline {b.headline:+9.4f}"
                    f" on {b.headline_metric}"
                )
        print(f"{cand.name[:52]:52s} v{model.version}"
              f" {len(bounds) - vacuous}/{len(bounds)} bounded")
        for ln in lines:
            print(ln)

        if not store:
            continue
        record = ExperimentRecord(
            candidate_id=cand.id,
            timestamp=utcnow(),
            git_commit=_git_commit(),
            parameters={"battery": "attack_patterns", "steps": 60},
            dataset="adversarial_patterns",
            model=f"mathmodel-v{model.version}",
            seed=None,
            simulation_version=SIMULATION_VERSION,
            results={
                "bounds": [b.model_dump(mode="json") for b in bounds],
                "vacuous_count": vacuous,
                "bounded_count": len(bounds) - vacuous,
            },
        )
        db.save_experiment(record)
        print(f"    stored {record.experiment_id}")

    if failures:
        raise SystemExit(f"failures: {failures}")
    if not store:
        print("dry run — pass --store to persist §21 records")


if __name__ == "__main__":
    main(store="--store" in sys.argv)
