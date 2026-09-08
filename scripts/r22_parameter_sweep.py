"""Round 22: attack-parameter robustness sweep (stability accrual).

The r21 decision brief's honest read: the successor's evidence is
one census observation vs the incumbent's five battery generations,
and the evidence most directly supports ACCRUE stability evidence
before the human publication decision. But a RE-RUN of the same
battery adds nothing (the battery is deterministic — same spec,
same number). What made the incumbent's record was each NEW
adversarial lens measuring the same construction clean.

The r22 lens: PARAMETER-CALIBRATION ROBUSTNESS. The battery's
defaults (strikes=4, amplitude=0.05, park_shift=-0.6, ...) are
public knowledge; a real attacker does not use the default
calibration. This sweep runs every pattern at its default PLUS
deliberate off-default variants (± amplitude, deeper/shallower
strikes, more/fewer resonance cycles, faster/slower creep) against
BOTH decision candidates — the successor (the stability question)
and the incumbent (the control with five generations of default-
calibration evidence).

A construction whose bound holds only at the default calibration
is a calibration artifact, not a bound. The honest stability
statement is the MAX edge across the whole sweep.

§21 records: dataset='adversarial_patterns', battery
'attack_parameter_sweep', round 22 — one record per candidate,
results.bounds carries every variant run, results.worst_edge is
the sweep max (the number the r21 brief's census-history table
picks up automatically).

Run: .venv/bin/python scripts/r22_parameter_sweep.py
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
from blockchain_rd_lab.simulation.adversarial import (
    AttackPattern,
    AttackPatternBattery,
    PatternSpec,
)

BATTERY = "attack_parameter_sweep"
ROUND = 22

# The decision candidates: the successor (stability question) and
# the incumbent (control — five generations of default-calibration
# evidence to compare against).
CANDIDATES = (
    ("cand-9200b07691c3", "Separation-Keyed (successor)"),
    ("cand-e74d830a9479", "Demand-Index (incumbent)"),
)

# Per pattern: the primary calibration knob, swept around the
# default (the default run is included for reference). Chosen to
# span the honest adversarial range: the attacker can strike
# deeper or shallower, cycle more often or less, grind faster or
# slower — and the classification must hold across all of it.
SWEEP: dict[AttackPattern, list[tuple[str, float]]] = {
    AttackPattern.VOL_OSCILLATION: [
        ("amplitude", 0.02), ("amplitude", 0.10)],
    AttackPattern.WASH_FLOW: [
        ("wash_level", 0.01), ("wash_level", 0.04)],
    AttackPattern.PUMP_UNWIND: [
        ("amplitude", 0.02), ("amplitude", 0.10)],
    AttackPattern.SHOCK_TIMING: [
        ("lag_fraction", 0.1), ("lag_fraction", 0.4)],
    AttackPattern.CRASH_PARK: [
        ("park_shift", -0.3), ("park_shift", -0.9)],
    AttackPattern.DRIFT_CREEP: [
        ("creep_rate", 0.002), ("creep_rate", 0.01)],
    AttackPattern.GRIND_HARVEST: [
        ("harvest_shift", -0.3), ("harvest_shift", -0.9)],
    AttackPattern.RESONANCE: [
        ("strikes", 2), ("strikes", 8), ("strikes", 16),
        ("strike_shift", -0.3), ("strike_shift", -0.9)],
}


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    for cid, label in CANDIDATES:
        m = MathModel.model_validate(json.loads(db.get_latest_math_model(cid)))
        bat = AttackPatternBattery(m)
        bounds, edges = [], []
        # every pattern at DEFAULT calibration first (reference row)
        for kind in AttackPattern:
            r = bat.run_pattern(PatternSpec(kind=kind, steps=60))
            bounds.append(r.model_dump(mode="json"))
            if r.headline is not None:
                edges.append(r.headline)
        # then every off-default variant, TAGGED with its calibration
        # (the §21 record's bounds are plain dicts — the tag renders
        # in the 4b disclosure so 27 runs read as 8 defaults + 19
        # named recalibrations, not 27 ambiguous rows)
        for kind, variants in SWEEP.items():
            for param, value in variants:
                spec = PatternSpec(kind=kind, steps=60)
                setattr(spec, param, value)
                r = bat.run_pattern(spec)
                d = r.model_dump(mode="json")
                d["calibration"] = f"{param}={value}"
                bounds.append(d)
                if r.headline is not None:
                    edges.append(r.headline)
        worst = max(edges) if edges else 0.0
        rec = ExperimentRecord(
            candidate_id=cid,
            dataset="adversarial_patterns",
            parameters={
                "battery": BATTERY, "round": ROUND,
                "variants_per_pattern": 2, "sweep": True},
            results={
                "bounds": bounds,
                "vacuous_count": sum(
                    1 for b in bounds if b.get("vacuous")),
                "worst_edge": worst,
                "sweep_max": worst,
                "default_max": max(
                    (b.get("headline") or 0.0)
                    for b in bounds[:len(AttackPattern)]),
            },
        )
        db.save_experiment(rec)
        over = [e for e in edges if e > 400]
        big = [e for e in edges if e > 150]
        print(f"{label}: {len(bounds)} runs "
              f"(8 default + {len(bounds) - 8} variants)")
        print(f"  sweep max edge: {worst:.4f}  "
              f"median {statistics.median(edges):.4f}")
        print(f"  >150: {len(big)}   >400 (flaw): {len(over)}")
        for b in bounds:
            h = b.get("headline")
            if h is not None and h > 150:
                print(f"    {b['kind'].value:>16}: {h:.2f}")


if __name__ == "__main__":
    main()
