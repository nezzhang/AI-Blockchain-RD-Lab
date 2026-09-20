"""Round 24: assemble the complete §27 publication bundle for the
§7 rank-1 finalist — every file that exists about the candidate,
assembled BY CODE from stored evidence only (§2: no report-writer
LLM), with a SHA-256 manifest so any recipient can verify the
bundle's integrity.

The human §27/§41 approval for publishing the rank-1 is in hand
(session record, this round). The lab's part under §28/§41 remains
STAGING: the bundle is the verbatim material for the human to
post; the physical act of posting (git push / blog / forum) uses
this repo's identity and is NOT executed by the lab.

Bundle layout (reports/release/bundle-<cid>/):
- README.md               — what this is, how to verify, how to cite
- dossier.md              — the §23 19-section research dossier
- release-package.md      — the §27 build-in-public package
- model-v3.json           — the final MathModel, machine-readable
- adversarial-bounds.json — every stored §20 battery census record
                             for the candidate (default + sweep
                             calibrations, all classifications)
- redteam-history.json    — every adversarial report ever filed
                             against it, verbatim (the full v1→v3
                             break/fix history, unfiltered)
- prior-art.json          — §12 prior-art trail for the candidate
- MANIFEST.json           — sha256 of every file above + generation
                             metadata (deterministic scoring reads
                             from the store, not from this script)

Run: .venv/bin/python scripts/r24_publication_bundle.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from blockchain_rd_lab.config import REPO_ROOT, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.reporting.decision import DECISION_CANDIDATES
from blockchain_rd_lab.reporting.release import ReleasePackageBuilder
from blockchain_rd_lab.schemas import CandidateStatus
from blockchain_rd_lab.scoring import ScoringEngine

RANK1 = DECISION_CANDIDATES[0]  # cand-9200b07691c3, §7 rank 1


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _json_default(obj: object) -> str:
    return str(obj)


def main() -> None:
    db = LabDatabase(REPO_ROOT / load_config().storage.database)
    rb = ReleasePackageBuilder(db)
    eng = ScoringEngine()

    cand = db.get_candidate(RANK1)
    assert cand is not None, RANK1

    out = REPO_ROOT / "reports" / "release" / f"bundle-{RANK1}"
    out.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(UTC).isoformat()

    # 1. dossier: the stored §23 dossier file, copied verbatim (it is
    #    itself code-assembled; the manifest pins its exact bytes)
    src = REPO_ROOT / "reports" / "finalists" / f"{RANK1}.md"
    dossier = out / "dossier.md"
    dossier.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    # 2. release package: rebuilt from the store for this bundle
    rel = rb.build(candidate_id=RANK1)
    assert rel is not None
    relp = out / "release-package.md"
    relp.write_text(rel, encoding="utf-8")

    # 3. final MathModel, machine-readable (the row is raw JSON)
    model_raw = db.get_latest_math_model(RANK1)
    assert model_raw is not None
    model = json.loads(model_raw)
    modelp = out / f"model-v{model['version']}.json"
    modelp.write_text(
        json.dumps(model, indent=2, sort_keys=True,
                   default=_json_default) + "\n", encoding="utf-8")

    # 4. every adversarial-pattern census record for the candidate
    # r48: scope to the §20 MECHANISM battery. The store also holds the §17
    # supply-attack census (parameters.battery="supply_attack_patterns*"),
    # whose pattern kinds (wash_mint, creep, round_trip, burn_park) are NOT
    # §20 AttackPattern values — the shipped verify.py re-runs every record
    # here as a §20 PatternSpec, so a supply census row makes the bundle
    # fail its own verifier. Exclude exactly that census tag; genuine §20
    # records carry attack_patterns* / attack_parameter_sweep / no tag and
    # must all ship.
    bounds = []
    for exp in db.iter_experiments(candidate_id=RANK1):
        res = exp.results or {}
        if "bounds" not in res:
            continue
        batt = str((exp.parameters or {}).get("battery", ""))
        if batt.startswith("supply_attack_patterns"):
            continue
        bounds.append({
            "experiment_id": exp.experiment_id,
            "recorded_at": exp.timestamp.isoformat()
            if hasattr(exp.timestamp, "isoformat") else str(exp.timestamp),
            "parameters": exp.parameters or {},
            "bounds": res["bounds"],
            "vacuous_count": res.get("vacuous_count"),
            "worst_edge": res.get("worst_edge"),
        })
    bpath = out / "adversarial-bounds.json"
    bpath.write_text(
        json.dumps(bounds, indent=2, sort_keys=True,
                   default=_json_default) + "\n", encoding="utf-8")

    # 4b. §15 scenario battery + Monte Carlo records for the FINAL
    # model version — r27 audit fix #6: the prose's "13/13 clean"
    # and mean_final/failures figures get the same raw backing file
    # treatment the attack bounds already had
    ver_suffix = f"-v{model['version']}"
    scen_recs = {}
    for exp in db.iter_experiments(candidate_id=RANK1):
        if not exp.experiment_id.endswith(ver_suffix):
            continue
        res = exp.results or {}
        if "bounds" in res:
            continue  # adversarial census, already shipped
        if not any(k in res for k in ("base", "trials")):
            continue
        scen_recs[exp.experiment_id] = {
            "experiment_id": exp.experiment_id,
            "recorded_at": exp.timestamp.isoformat()
            if hasattr(exp.timestamp, "isoformat") else str(exp.timestamp),
            "seed": exp.seed,
            "parameters": exp.parameters or {},
            "results": res,
        }
    spath = out / "scenario-results.json"
    spath.write_text(
        json.dumps(list(scen_recs.values()), indent=2, sort_keys=True,
                   default=_json_default) + "\n", encoding="utf-8")

    # 5. every red-team report ever filed against it, verbatim
    rt = db.list_redteam_results(candidate_id=RANK1)
    rtp = out / "redteam-history.json"
    rtp.write_text(
        json.dumps(rt, indent=2, sort_keys=True,
                   default=_json_default) + "\n", encoding="utf-8")

    # 6. §12 prior-art trail — DEDUPED on identical finding content
    # (r27 audit fix #5: one review recorded under two source rows
    # double-counted "searches recorded"; the row carries the full
    # multi-source review, so the duplicate is the same search)
    pa_all = db.list_prior_art(candidate_id=RANK1)
    pa_seen: dict[str, dict] = {}
    for row in pa_all:
        key = row["finding"]
        if key in pa_seen:
            # record the merge on the kept row, never silently drop
            kept = pa_seen[key]
            merged = kept.setdefault("merged_source_ids", [])
            if row["source_id"] not in merged:
                merged.append(row["source_id"])
        else:
            pa_seen[key] = row
    pa = list(pa_seen.values())
    for row in pa:
        row.setdefault("merged_source_ids", [])
    pap = out / "prior-art.json"
    pap.write_text(
        json.dumps(pa, indent=2, sort_keys=True,
                   default=_json_default) + "\n", encoding="utf-8")

    # 7. score decomposition: the §19 breakdown behind the headline
    res = eng.score(cand)
    sd = out / "score-decomposition.json"
    sd.write_text(
        json.dumps({
            "candidate_id": cand.id,
            "overall_score": res.overall_score,
            "fatal_flaw_applied": res.fatal_flaw_applied,
            "fatal_flaw_count": res.fatal_flaw_count,
            "notes": res.notes,
            "recomputation": (
                "overall = sum(dimension.score * dimension.weight) "
                "over the dimensions below; missing agent-authored "
                "evidence imputes at the 5.0 floor (flagged)"
            ),
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "score": d.score,
                    "weight": d.weight,
                    "weighted": d.weighted,
                    "imputed": d.imputed,
                }
                for d in res.dimensions
            ],
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # 8. the verifier ships INSIDE the bundle: heavy study is
    # self-service — a critic needs nothing but the bundle itself
    vsrc = REPO_ROOT / "scripts" / "r25_verify_bundle.py"
    (out / "verify.py").write_text(
        vsrc.read_text(encoding="utf-8"), encoding="utf-8")

    # 8b. the deterministic RUNTIME ships inside the bundle (r27
    # audit fix #3): verify.py's whole dependency closure is 4
    # files (formalization schema, simulation init, interpreter,
    # adversarial battery) + stdlib + pydantic — small enough to
    # ship, so the substance tier is self-service, not repo-dependent
    rt = out / "lab-runtime" / "blockchain_rd_lab"
    rt.mkdir(parents=True, exist_ok=True)
    for sub in ("formalization", "simulation"):
        srcd = REPO_ROOT / "src" / "blockchain_rd_lab" / sub
        dstd = rt / sub
        dstd.mkdir(exist_ok=True)
        for fn in ("__init__.py",):
            (dstd / fn).write_text(
                (srcd / fn).read_text(encoding="utf-8"), encoding="utf-8")
    for extra in ("interpreter.py", "adversarial.py"):
        (rt / "simulation" / extra).write_text(
            (REPO_ROOT / "src" / "blockchain_rd_lab" / "simulation" / extra
             ).read_text(encoding="utf-8"), encoding="utf-8")
    # the namespace package root needs an __init__ so
    # 'blockchain_rd_lab' resolves as a package on sys.path
    (rt / "__init__.py").write_text(
        "# namespace root of the shipped runtime (r27)\n",
        encoding="utf-8")

    # 9. README: what this is, how to verify, how to cite
    score = cand.overall_score
    # r48 (audit 2026-09-20, F3): the rank label is COMPUTED from the
    # store's current finalist standings, never asserted — the drift fix
    # re-scored the corpus and this candidate's standing moved (it was
    # published as rank 1 at 6.45; its scores recompute to 5.95, rank 5).
    # A bundle that claims a rank the store contradicts is the same
    # prose-drifts-from-data failure this repo exists to prevent.
    _finalists = [
        c for c in db.list_candidates(limit=None)
        if c.status is CandidateStatus.FINALIST and c.overall_score is not None
    ]
    _finalists.sort(key=lambda c: (-(c.overall_score or 0.0), c.name))
    _rank = _finalists.index(cand) + 1 if cand in _finalists else None
    _n_fin = len(_finalists)
    if _rank == 1:
        _status_line = f"finalist, rank 1 of {_n_fin} (recommended)"
    elif _rank is not None:
        _status_line = (
            f"finalist, rank {_rank} of {_n_fin} (the §7 recommended "
            f"candidate is {_finalists[0].name})"
        )
    else:
        _status_line = "finalist (rank not computable from the store)"
    # the shipped file list — computed ONCE, used by both the README's
    # sha256sum command (generated from the manifest keys, so it can
    # never drift from what ships) and the manifest itself
    files = [
        "README.md", "dossier.md", "release-package.md", modelp.name,
        "adversarial-bounds.json", "redteam-history.json", "prior-art.json",
        "score-decomposition.json", "scenario-results.json", "verify.py",
    ] + [r.relative_to(out).as_posix()
         for r in sorted((out / "lab-runtime").rglob("*.py"))]
    # wrap the names at ~72 cols for the README command block
    _names = sorted(f for f in files if f != "README.md")
    _lines: list[str] = []
    _cur = ""
    for _n in _names:
        if _cur and len(_cur) + 1 + len(_n) > 72:
            _lines.append(_cur)
            _cur = _n
        else:
            _cur = f"{_cur} {_n}".strip()
    if _cur:
        _lines.append(_cur)
    files_block = " \\\n    ".join(_lines)
    readme = f"""# Publication Bundle: {cand.name}

Assembled by code from stored evidence only (§2 — no report-writer
LLM). The bundle is the complete public evidence set for this
research candidate as of {generated}.

- **Candidate ID:** `{cand.id}`
- **Deterministic §19 score:** {score}
- **Model lineage:** v1 → v2 → v3 (every break/fix measured; the
  history is in `redteam-history.json`, unfiltered)
- **Status:** {_status_line}

## Files

| File | Contents |
|---|---|
| `dossier.md` | §23 research dossier, 19 fixed sections |
| `release-package.md` | §27 build-in-public release package |
| `model-v{model['version']}.json` | final MathModel (machine-readable) |
| `adversarial-bounds.json` | every stored §20 battery census record |
| `scenario-results.json` | §15 scenarios + Monte Carlo records for the final model |
| `redteam-history.json` | every adversarial report filed against the candidate, verbatim |
| `prior-art.json` | §12 prior-art trail |
| `score-decomposition.json` | §19 score breakdown (recomputable) |
| `verify.py` | the external verifier — run it, check this bundle yourself |
| `lab-runtime/` | deterministic runtime: interpreter, §15 + §20 batteries, MathModel schema |
| `MANIFEST.json` | SHA-256 of every file in this bundle |

## How to verify

Two levels, both self-service:

```bash
# 1. integrity: sha256 of EVERY file vs MANIFEST.json — the file
#    list below is GENERATED from the manifest keys, so it can
#    never drift from what actually ships
sha256sum \\
{files_block}

# 2. substance: re-run the §20 attack battery, §15 scenarios, and §19
#    score arithmetic against the PUBLISHED model — the deterministic
#    runtime ships in lab-runtime/ (interpreter + both batteries +
#    MathModel schema; needs only Python 3.12+ and pydantic)
python verify.py .
```

`verify.py` reads only this bundle (never any database), re-runs every
reproducible claim with the deterministic interpreter in `lab-runtime/`,
and writes a verification report beside the bundle. No lab package
install needed — the interpreter is code, and the code ships with the
claims (§2).

## Scope and honesty

This is SIMULATION-STAGE evidence: every adversarial bound was
measured against a deterministic equation interpreter under named
attack choreographies, not against deployed software or live
attackers. 5 of the 11 score dimensions are imputed at the 5.0
floor (offline mode, disclosed in the dossier's scoring section).
The residual-attack disclosure in `release-package.md` §4 lists
every attack surface the final model still carries. No token,
no deployment, no live contract — §27/§28.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")

    # 8. MANIFEST: sha256 of every file, written last
    # (the file list was computed before the README so both share
    # one source of truth — the sha256sum command cannot drift)
    manifest = {
        "candidate_id": cand.id,
        "candidate_name": cand.name,
        "generated": generated,
        "deterministic_score": score,
        "model_version": model["version"],
        "files": {
            f: {"sha256": _sha256(out / f), "bytes": (out / f).stat().st_size}
            for f in files
        },
    }
    (out / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    print(f"bundle: {out}")
    for f in sorted(out.iterdir()):
        print(f"  {f.name:28} {f.stat().st_size:>8} bytes")


if __name__ == "__main__":
    main()
