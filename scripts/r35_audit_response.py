"""r35: external-audit response — the SUPPRESSION-VECTOR STORE AUDIT.

The 2026-09-15 audit's F1 evidence was refuted (the live public main
ships the r33 measured gate; the auditor quoted the pre-r33 blob
daf394f — its own header says it retained the prior audit's file).
But the finding's STRONGEST form was real: until r35, the agent's
`strongest_attack_is_profitable` boolean was the gate's TRIGGER — an
agent asserting profitable=false SUPPRESSED the measurement entirely,
shielding a stored model the battery would convict at worst-edge 2266.

r35 removed the trigger (every fatal verdict is measured; the boolean
is pure metadata). This script closes the loop the round's response
left open: DID THE SUPPRESSION VECTOR EVER FIRE ON REAL DATA?

Method (§2: measure, don't infer):
  1. Enumerate EVERY red-team report ever filed (all candidates, all
     rounds — list_redteam_results(None), newest first).
  2. For each candidate that EVER received a fatal verdict, check
     whether its fatal report carried profitable=false — the exact
     input that pre-r35 skipped measurement for.
  3. For every such candidate, run TODAY's gate (r35 semantics) on
     its latest stored MathModel: measure the battery's worst headline
     edge vs FLAW_EDGE_THRESHOLD. A conviction (>400) would mean the
     pre-r35 suppression LET A FLAWED MODEL ESCAPE — a live §11-class
     store correction question for the operator. An acquittal means
     the vector never fired on this corpus: the fix is preventive,
     not corrective.
  4. Store ONE §21 census record (round 35, this audit tag). This
     script is IDEMPOTENT: it purges its own prior same-tag records
     first (the r34 store-hygiene discipline — accumulate-then-purge
     is evidence debt).

Read-only on the corpus: REJECTED is terminal by design; §11
corrections remain the operator's decision (§2). This script measures
and documents; it changes no candidate status.
"""

from __future__ import annotations

import json

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import ExperimentORM, LabDatabase
from blockchain_rd_lab.simulation.adversarial import (
    FLAW_EDGE_THRESHOLD,
    AttackPattern,
    AttackPatternBattery,
    PatternSpec,
)

AUDIT_TAG = "2026-09-15 F1 suppression-vector store audit"
CENSUS_PARAMETERS = {
    "battery": "attack_patterns_v8_pin_counterfactual",
    "round": 35,
    "audit": AUDIT_TAG,
    "scope": (
        "every candidate that EVER received a fatal red-team verdict "
        "with strongest_attack_is_profitable=false — the pre-r35 "
        "suppression trigger; measured under the r35 gate (every "
        "fatal verdict measured, boolean is metadata)"
    ),
}


def measure_model(model_json: str) -> tuple[dict | None, float]:
    """Run the default-calibration battery on the parsed model.

    Returns (worst row, worst headline edge). worst row is None when
    no run produces a headline (all vacuous) — never conflated with 0.
    """
    spec = json.loads(model_json)
    battery = AttackPatternBattery(spec)
    worst_row: dict | None = None
    worst_edge = -1.0
    for kind in AttackPattern:
        ps = PatternSpec(kind=kind, steps=60)
        bound = battery.run(ps)
        row = json.loads(bound.model_dump_json())
        headline = row.get("headline_edge")
        if headline is not None and headline > worst_edge:
            worst_edge = headline
            worst_row = row
    return worst_row, max(worst_edge, 0.0)


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)

    # ---- 1. every red-team report ever filed --------------------------
    rows = db.list_redteam_results(None)
    print(f"{len(rows)} adversarial reports filed, all candidates")

    # ---- 2. fatal verdicts per candidate ------------------------------
    fatal_by_cand: dict[str, dict] = {}
    for row in rows:
        rep = row["report_json"]
        if isinstance(rep, str):
            rep = json.loads(rep)
        if (
            row["agent_name"] == "red_team"
            and rep.get("verdict") == "fatal"
            and row["candidate_id"] not in fatal_by_cand
        ):
            fatal_by_cand[row["candidate_id"]] = {
                "report_id": row["id"],
                "created_at": row["created_at"],
                "profitable": rep.get("strongest_attack_is_profitable"),
                "strongest_attack": rep.get("strongest_attack", ""),
            }
    print(f"{len(fatal_by_cand)} candidates have EVER received a "
          f"fatal red-team verdict")
    for cid, info in sorted(fatal_by_cand.items()):
        print(f"  {cid}: profitable={info['profitable']} "
              f"({info['created_at']}) — {info['strongest_attack'][:60]}")

    # ---- 3. the suppression-vector exposure set ------------------------
    # Pre-r35, fatal + profitable=false SKIPPED the measurement. Any
    # candidate in this set whose stored model measures >400 today was
    # shielded by the vector (convicted-under-denial).
    exposed = {
        cid: info
        for cid, info in fatal_by_cand.items()
        if info["profitable"] is False
    }
    print(f"\n{len(exposed)} candidates were EXPOSED to the pre-r35 "
          f"suppression trigger (fatal + profitable=false):")
    if not exposed:
        print("  (none — the vector never fired on real data)")

    findings: list[dict] = []
    for cid in sorted(exposed):
        model_json = db.get_latest_math_model(cid)
        if model_json is None:
            findings.append({
                "candidate_id": cid,
                "class": "unmeasured_no_model",
                "note": "fatal + profitable=false, NO stored MathModel — "
                        "pre-r35 recorded the verdict without measuring; "
                        "r35 gate also fails closed for rejection "
                        "(nothing to measure). Status unchanged.",
            })
            print(f"  {cid}: no stored model — unmeasured, fail-closed "
                  f"(unchanged)")
            continue
        worst_row, worst_edge = measure_model(model_json)
        findings.append({
            "candidate_id": cid,
            "class": "measured",
            "worst_headline_edge": worst_edge,
            "worst_pattern": (
                worst_row["kind"] if worst_row else None
            ),
            "threshold": FLAW_EDGE_THRESHOLD,
            "would_convict_today": worst_edge > FLAW_EDGE_THRESHOLD,
        })
        verdict = ("WOULD CONVICT TODAY — the pre-r35 suppression "
                   "SHIELDED a flawed model (§11 operator question)"
                   if worst_edge > FLAW_EDGE_THRESHOLD
                   else "acquits under today's gate — the suppression "
                        "never fired with a conviction behind it")
        print(f"  {cid}: worst headline edge {worst_edge:.4f} "
              f"(threshold {FLAW_EDGE_THRESHOLD}) — {verdict}")

    # ---- 4. one idempotent §21 census record ---------------------------
    with db._session() as s:
        q = s.query(ExperimentORM).filter(
            ExperimentORM.candidate_id == "AUDIT-CORPUS"
        ).all()
        for row in q:
            p = json.loads(row.parameters_json)
            if p.get("audit") == AUDIT_TAG:
                print(f"purging prior audit record {row.experiment_id}")
                s.delete(row)
        s.commit()

    from blockchain_rd_lab.schemas import ExperimentRecord

    record = ExperimentRecord(
        candidate_id="AUDIT-CORPUS",
        parameters=CENSUS_PARAMETERS,
        results={
            "reports_scanned": len(rows),
            "candidates_with_fatal_ever": len(fatal_by_cand),
            "exposed_to_suppression_trigger": len(exposed),
            "findings": findings,
            "suppression_ever_convicted": any(
                f.get("would_convict_today") is True for f in findings
            ),
        },
        dataset="redteam-gate-audit",
        model="gate:r35-suppression-vector-audit",
    )
    db.save_experiment(record)
    print(f"\nstored §21 census record {record.experiment_id} "
          f"(candidate AUDIT-CORPUS, round 35)")
    print("read-only on the corpus — §11 corrections remain the "
          "operator's decision (§2)")


if __name__ == "__main__":
    main()
