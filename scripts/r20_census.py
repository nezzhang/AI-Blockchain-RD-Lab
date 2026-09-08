"""Round 20: census under the full 8-pattern battery.

Re-run every ranked candidate under attack_patterns_v7_resonance
(the 8-pattern battery incl. RESONANCE with the quiet-tail
classification layer) and store §21 records.

Run: .venv/bin/python scripts/r20_census.py
"""

from __future__ import annotations

import json
import statistics

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import (
    ExperimentRecord,
    LabDatabase,
)
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.schemas import CandidateStatus
from blockchain_rd_lab.simulation.adversarial import (
    AttackPattern,
    AttackPatternBattery,
    PatternSpec,
)

BATTERY = "attack_patterns_v7_resonance"
ROUND = 20


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    ranked = [
        c for c in db.list_candidates(limit=None)
        if c.status in (CandidateStatus.FINALIST, CandidateStatus.SCORED)
    ]
    rows = []
    for c in ranked:
        try:
            m = MathModel.model_validate(
                json.loads(db.get_latest_math_model(c.id)))
        except Exception as exc:
            print(f"  skip {c.id}: {exc}")
            continue
        b = AttackPatternBattery(m)
        bounds, worst, vac = [], 0.0, 0
        for k in AttackPattern:
            r = b.run_pattern(PatternSpec(kind=k, steps=60))
            if r.headline is None:
                vac += 1
            worst = max(worst, r.headline or 0.0)
            bounds.append(r.model_dump(mode="json"))
        rec = ExperimentRecord(
            candidate_id=c.id,
            dataset="adversarial_patterns",
            parameters={"battery": BATTERY, "round": ROUND},
            results={"bounds": bounds, "vacuous_count": vac,
                     "worst_edge": worst},
        )
        db.save_experiment(rec)
        rows.append((worst, c.name[:38], c.id))
    rows.sort(reverse=True)
    for w, n, _c in rows[:8]:
        print(f"  worst {w:7.2f}  {n}")
    med = statistics.median(w for w, _, _ in rows) if rows else 0
    above = sum(1 for w, _, _ in rows if w > 400)
    print(f"\ncensus: {len(rows)} ranked stored; median worst-edge "
          f"{med:.1f}; edges>400: {above}")


if __name__ == "__main__":
    main()
