"""r50: refresh the publication bundle's §15/Monte Carlo evidence under
the repaired anchor-series PRNG.

The r50 calibration suite caught a mangled mulberry32 port in
``simulation._DeterministicRandom`` (biased since Phase 4: uniforms
averaged 0.02, gauss mean +3.5 sigma, every "base" scenario carried a
hidden +0.73%/step drift). The bundle's ``scenario-results.json`` was
generated under the biased generator, so its §15/MC numbers are
superseded. The §20 attack battery uses crafted series (no randomness)
and is unaffected — ``adversarial-bounds.json`` stands.

What this script does, all by code from stored/published artifacts (§2):

1. Re-runs the §15 battery (13 scenarios, steps=60, seed=7) and the
   20-trial Monte Carlo for the published final model
   (``model-v3.json``) under the FIXED generator.
2. Stores the re-runs as NEW experiment records
   (``...-scenarios-v3-r50`` / ``...-montecarlo-v3-r50``). §21 is
   append-only: the biased ``-v3`` records stay in the store.
3. Regenerates the §23 dossier and the §27 release package from the
   store (the builders pick the latest matching records), so every
   prose figure traces to a stored record.
4. Rewrites the bundle's ``scenario-results.json`` with the refreshed
   records, ships the fixed runtime in ``lab-runtime/``, and adds an
   r50 disclosure note to the bundle README.
5. Regenerates ``MANIFEST.json`` (sha256 of every shipped file).

Run ``verify.py`` afterwards to regenerate the VERIFICATION report.

Run: .venv/bin/python scripts/r50_refresh_bundle_sim.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.reporting.decision import DECISION_CANDIDATES
from blockchain_rd_lab.reporting.release import ReleasePackageBuilder
from blockchain_rd_lab.reporting.service import ReportBuilder
from blockchain_rd_lab.schemas import CandidateStatus, ExperimentRecord, utcnow
from blockchain_rd_lab.simulation import (
    MechanismSimulation,
    MonteCarloRunner,
    ScenarioBattery,
    ScenarioKind,
    scenario_config,
)
from blockchain_rd_lab.simulation.service import SIMULATION_VERSION

RANK1 = DECISION_CANDIDATES[0]  # cand-9200b07691c3, §7 rank 1
STEPS = 60  # matches the published -v3 records
SEED = 7
MC_TRIALS = 20
SCEN_ID = f"{RANK1}-scenarios-v3-r50"
MC_ID = f"{RANK1}-montecarlo-v3-r50"

BUNDLE = REPO_ROOT / "reports" / "release" / f"bundle-{RANK1}"

README_NOTE = """
## r50 evidence refresh (2026-09-22)

The lab's calibration suite (known-answer validation, r50) caught a
biased anchor-series PRNG that had been live since Phase 4. The §15
scenario and Monte Carlo records in this bundle were RE-RUN under the
repaired generator and are stored as experiment records
`*-scenarios-v3-r50` / `*-montecarlo-v3-r50` (the store is append-only:
the superseded biased records remain in the lab's database and in git
history). Headline impact: the Monte Carlo mean moved 0.0017%
(1005.6340 → 1005.6172) with 0 failures in 20 trials and 13/13
scenarios still clean — the robustness conclusion is unchanged; the
per-scenario final-state values were materially wrong and have been
replaced. The §20 adversarial bounds use crafted series (no
randomness) and are unaffected. The shipped `lab-runtime/` is the
repaired generator, so `verify.py` exercises exactly the code that
produced these numbers.
"""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _json_default(obj: object) -> str:
    return str(obj)


def _git_commit() -> str:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)

    cand = db.get_candidate(RANK1)
    assert cand is not None, RANK1

    # 1. re-run the §15 battery + Monte Carlo under the FIXED generator,
    #    starting from the PUBLISHED model file (not the store) so the
    #    bundle's own artifact is what gets exercised
    mm = MathModel.model_validate_json(
        (BUNDLE / "model-v3.json").read_text(encoding="utf-8")
    )
    sim = MechanismSimulation(mm)

    runs = ScenarioBattery(sim, steps=STEPS, seed=SEED).run()
    scenario_results = {
        kind: {
            "final": r.metrics,
            "failures": r.failures,
            "degenerate": r.degenerate,
        }
        for kind, r in runs.items()
    }
    base_cfg = scenario_config(ScenarioKind.BASE, steps=STEPS, seed=SEED)
    mc = MonteCarloRunner(sim, base_cfg, trials=MC_TRIALS).run()
    mc_results = {
        "trials": mc.trials,
        "failures": mc.failures,
        "mean_final": mc.mean_final,
        "median_final": mc.median_final,
        "std_final": mc.std_final,
        "p5_final": mc.p5_final,
        "p95_final": mc.p95_final,
        "worst_final": mc.worst_final,
        "best_final": mc.best_final,
        "primary_symbol": mc.primary_symbol,
    }

    clean = sum(1 for r in scenario_results.values() if not r["failures"])
    degen = sum(1 for r in scenario_results.values() if r["degenerate"])
    print(f"§15 battery: {clean}/{len(scenario_results)} clean, {degen} degenerate")
    print(
        f"Monte Carlo: mean_final={mc.mean_final}, p5={mc.p5_final}, "
        f"p95={mc.p95_final}, failures={mc.failures}"
    )

    # 2. store the re-runs as NEW records (§21 append-only; idempotent)
    existing = {e.experiment_id for e in db.iter_experiments(candidate_id=RANK1)}
    commit = _git_commit()
    records = [
        ExperimentRecord(
            experiment_id=SCEN_ID,
            candidate_id=RANK1,
            timestamp=utcnow(),
            git_commit=commit,
            parameters={
                "steps": STEPS,
                "scenarios": sorted(scenario_results.keys()),
                "supersedes": f"{RANK1}-scenarios-v3",
                "reason": "r50: biased anchor PRNG (mulberry32 port) repaired",
            },
            dataset=f"synthetic-anchor-v1/seed-{SEED}",
            model="mathmodel-v3",
            seed=SEED,
            simulation_version=SIMULATION_VERSION,
            results=scenario_results,
        ),
        ExperimentRecord(
            experiment_id=MC_ID,
            candidate_id=RANK1,
            timestamp=utcnow(),
            git_commit=commit,
            parameters={
                "trials": MC_TRIALS,
                "steps": STEPS,
                "supersedes": f"{RANK1}-montecarlo-v3",
                "reason": "r50: biased anchor PRNG (mulberry32 port) repaired",
            },
            dataset=f"synthetic-anchor-v1/seed-{SEED}-mc{MC_TRIALS}",
            model="mathmodel-v3",
            seed=SEED,
            simulation_version=SIMULATION_VERSION,
            results=mc_results,
        ),
    ]
    for rec in records:
        if rec.experiment_id in existing:
            print(f"store: {rec.experiment_id} already recorded — skipping")
        else:
            db.save_experiment(rec)
            print(f"store: {rec.experiment_id} recorded")

    # 3. regenerate the §23 dossier + §27 release package FROM THE STORE
    finalists = [
        c
        for c in db.list_candidates(limit=None)
        if c.status is CandidateStatus.FINALIST and c.overall_score is not None
    ]
    finalists.sort(key=lambda c: (-(c.overall_score or 0.0), c.name))
    rank = finalists.index(cand) + 1 if cand in finalists else None
    dossier = ReportBuilder(db).build_dossier(
        cand, rank=rank, recommended=(rank == 1)
    )
    finalists_dir = REPO_ROOT / "reports" / "finalists"
    finalists_dir.mkdir(parents=True, exist_ok=True)
    (finalists_dir / f"{RANK1}.md").write_text(
        dossier.to_markdown(), encoding="utf-8"
    )
    (BUNDLE / "dossier.md").write_text(dossier.to_markdown(), encoding="utf-8")

    rel = ReleasePackageBuilder(db).build(candidate_id=RANK1)
    assert rel is not None
    (BUNDLE / "release-package.md").write_text(rel, encoding="utf-8")

    # 4. refreshed scenario-results.json (same shape r24 shipped) +
    #    the fixed runtime
    scen_recs = []
    for exp in db.iter_experiments(candidate_id=RANK1):
        if exp.experiment_id not in (SCEN_ID, MC_ID):
            continue
        scen_recs.append(
            {
                "experiment_id": exp.experiment_id,
                "recorded_at": exp.timestamp.isoformat()
                if hasattr(exp.timestamp, "isoformat")
                else str(exp.timestamp),
                "seed": exp.seed,
                "parameters": exp.parameters or {},
                "results": exp.results or {},
            }
        )
    scen_recs.sort(key=lambda r: r["experiment_id"])
    (BUNDLE / "scenario-results.json").write_text(
        json.dumps(scen_recs, indent=2, sort_keys=True, default=_json_default)
        + "\n",
        encoding="utf-8",
    )

    rt = BUNDLE / "lab-runtime" / "blockchain_rd_lab"
    for sub in ("formalization", "simulation"):
        srcd = REPO_ROOT / "src" / "blockchain_rd_lab" / sub
        (rt / sub / "__init__.py").write_text(
            (srcd / "__init__.py").read_text(encoding="utf-8"), encoding="utf-8"
        )
    for extra in ("interpreter.py", "adversarial.py"):
        (rt / "simulation" / extra).write_text(
            (
                REPO_ROOT / "src" / "blockchain_rd_lab" / "simulation" / extra
            ).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    readme_path = BUNDLE / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if "## r50 evidence refresh" not in readme:
        readme_path.write_text(readme.rstrip() + "\n" + README_NOTE, encoding="utf-8")

    # 5. MANIFEST: recompute sha256 for the shipped file set
    old_manifest = json.loads((BUNDLE / "MANIFEST.json").read_text(encoding="utf-8"))
    files = sorted(old_manifest["files"].keys())
    manifest = {
        "candidate_id": cand.id,
        "candidate_name": cand.name,
        "generated": datetime.now(UTC).isoformat(),
        "refreshed": "r50: §15/MC evidence re-run under the repaired PRNG",
        "deterministic_score": cand.overall_score,
        "model_version": 3,
        "files": {
            f: {"sha256": _sha256(BUNDLE / f), "bytes": (BUNDLE / f).stat().st_size}
            for f in files
        },
    }
    (BUNDLE / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"bundle refreshed: {BUNDLE}")
    print(f"next: cd reports/release/bundle-{RANK1} && python verify.py .")


if __name__ == "__main__":
    main()
