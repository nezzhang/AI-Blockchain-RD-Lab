"""r33: external-audit response — re-measure the published §20 record
under the fixed battery (audit F2 long-window spec preservation; the
r33 pin counterfactual) and store the corrected census.

The audit (2026-09-14-auditor-FIXES.md) found the r19 long-window
transit confirmation rebuilt the doubled-window spec from
kind/steps/park_at alone, silently resetting every other calibration
field to dataclass defaults — a calibrated variant's transit decision
was made by a DIFFERENT (default) attack. The fix (model_copy) ships
with this round; this script re-sweeps every calibrated variant BOTH
decision candidates were measured under and diffs against the
PUBLISHED bundle (reports/release/bundle-cand-9200b07691c3/
adversarial-bounds.json), so every drift is named, measured, and
re-stored — never silently absorbed.

Also stores the gate-v2 re-evaluation record for the one historical
§20 gate rejection (Population-Linked Supply, cand-7f2f07fd4e9a): the
audit-F1 finding — the rejection rested on the agent's
profitability assertion with ZERO battery evidence behind it. The
record documents the evidence class; §11 corrections remain the
operator's decision (§2).

§21: every re-measured row is stored as an experiment record tagged
round 33. The bundle is regenerated through the r24 builder
afterward (never hand-patched).
"""

from __future__ import annotations

import json

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.schemas import ExperimentRecord
from blockchain_rd_lab.simulation.adversarial import (
    FLAW_EDGE_THRESHOLD,
    AttackPattern,
    AttackPatternBattery,
    PatternSpec,
)

SUCCESSOR = "cand-9200b07691c3"
INCUMBENT = "cand-e74d830a9479"
GATE_REJECTED = "cand-7f2f07fd4e9a"  # Population-Linked Supply (audit F1)

# The r22 calibration grid, exactly as swept then (kind, spec field,
# value) — 19 calibrated variants + 8 defaults = 27 rows.
SWEEP: list[tuple[str, str, float]] = [
    ("vol_oscillation", "amplitude", 0.02),
    ("vol_oscillation", "amplitude", 0.10),
    ("wash_flow", "wash_level", 0.01),
    ("wash_flow", "wash_level", 0.04),
    ("pump_unwind", "amplitude", 0.02),
    ("pump_unwind", "amplitude", 0.10),
    ("shock_timing", "lag_fraction", 0.1),
    ("shock_timing", "lag_fraction", 0.4),
    ("crash_park", "park_shift", -0.3),
    ("crash_park", "park_shift", -0.9),
    ("drift_creep", "creep_rate", 0.002),
    ("drift_creep", "creep_rate", 0.01),
    ("grind_harvest", "harvest_shift", -0.3),
    ("grind_harvest", "harvest_shift", -0.9),
    ("resonance", "strikes", 2.0),
    ("resonance", "strikes", 8.0),
    ("resonance", "strikes", 16.0),
    ("resonance", "strike_shift", -0.3),
    ("resonance", "strike_shift", -0.9),
]


def bound_row(bound) -> dict:
    return json.loads(bound.model_dump_json())


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)

    # The published BASELINE per candidate: the successor's is the
    # bundle JSON; the incumbent's is its own r22 §21 sweep record
    # (the bundle holds the SUCCESSOR only).
    bundle_path = (
        REPO_ROOT / "reports" / "release" / f"bundle-{SUCCESSOR}"
        / "adversarial-bounds.json"
    )
    published = json.loads(bundle_path.read_text())
    pub_rows: dict[tuple[str, str], dict] = {}
    for rec in published:
        # BASELINE = the published generations only (r20 defaults +
        # r22 sweep). A regenerated bundle may already carry this
        # round's own r33 record — comparing against it would compare
        # the new measurement against itself (no-drift tautology).
        if rec.get("parameters", {}).get("round") not in (20, 22):
            continue
        for b in rec["bounds"]:
            pub_rows[(b["kind"], b.get("calibration", ""))] = b
    inc_rows: dict[tuple[str, str], dict] = {}
    for r in db.iter_experiments(INCUMBENT):
        if r.parameters.get("round") == 22:  # the published generation
            for b in r.results.get("bounds", []):
                inc_rows[(b["kind"], b.get("calibration", ""))] = b
    baselines = {SUCCESSOR: pub_rows, INCUMBENT: inc_rows}

    for cid, name in ((SUCCESSOR, "successor"), (INCUMBENT, "incumbent")):
        raw = db.get_latest_math_model(cid)
        assert raw, f"no model for {cid}"
        mm = MathModel.model_validate(json.loads(raw))
        bat = AttackPatternBattery(mm)

        rows: list[dict] = []
        drifts: list[str] = []
        # defaults (8) + calibrated (19)
        runs: list[tuple[str, str]] = [(k.value, "") for k in AttackPattern]
        for kind, field, val in SWEEP:
            # the calibration tag must match the r22 format EXACTLY
            # (strikes=2 not 2.0; amplitude=0.02 not 0.020) — the
            # §4b/JSON completeness check keys on the tag string.
            runs.append((kind, f"{field}={val:g}"))

        baseline = baselines[cid]
        for kind, cal in runs:
            spec = PatternSpec(kind=AttackPattern(kind), steps=60)
            if cal:
                field, val = cal.split("=")
                setattr(spec, field, float(val))
            bound = bat.run_pattern(spec)
            row = bound_row(bound)
            if cal:
                row["calibration"] = cal
            rows.append(row)

            pub = baseline.get((kind, cal))
            if pub is None:
                continue  # not in this candidate's published record
            ph = pub.get("headline")
            nh = row.get("headline")
            if ph != nh:
                drifts.append(
                    f"{name} {kind} @{cal or 'default'}: "
                    f"headline {ph} -> {nh}"
                )
            if pub.get("in_transit") != row.get("in_transit"):
                drifts.append(
                    f"{name} {kind} @{cal or 'default'}: "
                    f"in_transit {pub.get('in_transit')} -> "
                    f"{row.get('in_transit')}"
                )
            if pub.get("regime_tracking") != row.get("regime_tracking"):
                drifts.append(
                    f"{name} {kind} @{cal or 'default'}: "
                    f"regime_tracking {pub.get('regime_tracking')} -> "
                    f"{row.get('regime_tracking')}"
                )

        worst = max(
            (r["headline"] for r in rows if r["headline"] is not None),
            default=None,
        )
        print(f"\n== {name} ({cid}): 27 rows re-measured, "
              f"worst headline {worst}")
        for d in drifts:
            print("  DRIFT:", d)
        if not drifts:
            print("  no drift vs published bundle")

        # §21: store the corrected census (r33 tag)
        record = ExperimentRecord(
            candidate_id=cid,
            parameters={
                "battery": "attack_patterns_v8_pin_counterfactual",
                "round": 33,
                "sweep": True,
                "audit": "2026-09-14 F2 fix + r33 pin counterfactual",
            },
            results={
                "bounds": rows,
                "worst_edge": worst,
                "vacuous_count": sum(
                    1 for r in rows if r["vacuous"]
                ),
                "drift_vs_published": drifts,
            },
            dataset="adversarial-battery",
            model="attack_patterns_v8",
        )
        db.save_experiment(record)
        print(f"  stored exp {record.experiment_id} (r33 census)")

    # -- audit F1 store note: the one historical gate rejection --------
    gate_rows = db.list_redteam_results(GATE_REJECTED)
    fatal = None
    for row in gate_rows:
        rep = row["report_json"]
        if isinstance(rep, str):
            rep = json.loads(rep)
        if rep.get("verdict") == "fatal":
            fatal = rep
    if fatal is not None:
        record = ExperimentRecord(
            candidate_id=GATE_REJECTED,
            parameters={
                "gate": "fatal_flaw_v2_measured",
                "audit": "2026-09-14 F1 re-evaluation",
                "agent_verdict": "fatal",
                "agent_strongest_attack": fatal.get(
                    "strongest_attack", ""
                ),
                "agent_profitability_hypothesis": True,
                "note": (
                    "historical §20 rejection (2026-09-04) re-evaluated "
                    "under gate v2: the candidate has NO stored MathModel "
                    "and NO battery records — the rejection rested on the "
                    "agent's profitability assertion alone. Gate v2 "
                    "fails closed for rejection on unmeasured claims. "
                    "§11 correction remains the operator's decision (§2); "
                    "this record documents the evidence class only."
                ),
            },
            results={
                "measured_evidence": None,
                "confirmed": False,
                "threshold": FLAW_EDGE_THRESHOLD,
            },
            dataset="redteam-gate",
            model="battery:attack_patterns@r33",
        )
        db.save_experiment(record)
        print(f"\ngate-v2 re-evaluation stored for {GATE_REJECTED} "
              f"(exp {record.experiment_id})")


if __name__ == "__main__":
    main()
