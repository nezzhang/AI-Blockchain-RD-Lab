"""Round 18: corpus census under the 7-pattern battery + §21 records.

Stores one §21 experiment record per ranked candidate under battery
`attack_patterns_v5_grind_harvest` (the r17 6-pattern battery +
GRIND_HARVEST + the r18 pin-aware-arrival and heal-contradiction
classification fixes).

Run: .venv/bin/python scripts/r18_census.py
"""

from __future__ import annotations

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

BATTERY = "attack_patterns_v5_grind_harvest"
ROUND = 18


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
                __import__("json").loads(db.get_latest_math_model(c.id)))
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
    for w, n, _cid in rows[:10]:
        print(f"  worst {w:7.2f}  {n}")
    import statistics
    med = statistics.median(w for w, _, _ in rows) if rows else 0
    above = sum(1 for w, _, _ in rows if w > 400)
    print(f"\ncensus: {len(rows)} ranked stored; median worst-edge "
          f"{med:.1f}; edges>400: {above}")


if __name__ == "__main__":
    main()
