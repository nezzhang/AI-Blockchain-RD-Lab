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
    bounds = []
    for exp in db.iter_experiments(candidate_id=RANK1):
        res = exp.results or {}
        if "bounds" not in res:
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

    # 5. every red-team report ever filed against it, verbatim
    rt = db.list_redteam_results(candidate_id=RANK1)
    rtp = out / "redteam-history.json"
    rtp.write_text(
        json.dumps(rt, indent=2, sort_keys=True,
                   default=_json_default) + "\n", encoding="utf-8")

    # 6. §12 prior-art trail
    pa = db.list_prior_art(candidate_id=RANK1)
    pap = out / "prior-art.json"
    pap.write_text(
        json.dumps(pa, indent=2, sort_keys=True,
                   default=_json_default) + "\n", encoding="utf-8")

    # 7. README: what this is, how to verify, how to cite
    score = cand.overall_score
    readme = f"""# Publication Bundle: {cand.name}

Assembled by code from stored evidence only (§2 — no report-writer
LLM). The bundle is the complete public evidence set for the §7
rank-1 research candidate as of {generated}.

- **Candidate ID:** `{cand.id}`
- **Deterministic §19 score:** {score}
- **Model lineage:** v1 → v2 → v3 (every break/fix measured; the
  history is in `redteam-history.json`, unfiltered)
- **Status:** finalist, rank 1 (recommended)

## Files

| File | Contents |
|---|---|
| `dossier.md` | §23 research dossier, 19 fixed sections |
| `release-package.md` | §27 build-in-public release package |
| `model-v{model['version']}.json` | final MathModel (machine-readable) |
| `adversarial-bounds.json` | every stored §20 battery census record |
| `redteam-history.json` | every adversarial report filed against the candidate, verbatim |
| `prior-art.json` | §12 prior-art trail |
| `MANIFEST.json` | SHA-256 of every file in this bundle |

## How to verify

```bash
sha256sum dossier.md release-package.md model-v{model['version']}.json \\
    adversarial-bounds.json redteam-history.json prior-art.json
# compare against MANIFEST.json
```

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
    files = [
        "README.md", "dossier.md", "release-package.md", modelp.name,
        "adversarial-bounds.json", "redteam-history.json", "prior-art.json",
    ]
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
