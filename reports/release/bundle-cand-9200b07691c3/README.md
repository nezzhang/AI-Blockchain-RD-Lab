# Publication Bundle: Separation-Keyed Fee Smoothing Escrow

Assembled by code from stored evidence only (§2 — no report-writer
LLM). The bundle is the complete public evidence set for the §7
rank-1 research candidate as of 2026-09-10T02:40:26.126701+00:00.

- **Candidate ID:** `cand-9200b07691c3`
- **Deterministic §19 score:** 6.45
- **Model lineage:** v1 → v2 → v3 (every break/fix measured; the
  history is in `redteam-history.json`, unfiltered)
- **Status:** finalist, rank 1 (recommended)

## Files

| File | Contents |
|---|---|
| `dossier.md` | §23 research dossier, 19 fixed sections |
| `release-package.md` | §27 build-in-public release package |
| `model-v3.json` | final MathModel (machine-readable) |
| `adversarial-bounds.json` | every stored §20 battery census record |
| `redteam-history.json` | every adversarial report filed against the candidate, verbatim |
| `prior-art.json` | §12 prior-art trail |
| `MANIFEST.json` | SHA-256 of every file in this bundle |

## How to verify

Two levels, both self-service:

```bash
# 1. integrity: sha256 of every file vs MANIFEST.json (all files listed)
sha256sum README.md dossier.md release-package.md model-v3.json \
    adversarial-bounds.json redteam-history.json prior-art.json \
    score-decomposition.json verify.py

# 2. substance: re-run the §20 attack battery and §15 scenarios against
#    model-v3.json — recomputes the published headlines
python verify.py .
```

`verify.py` reads only this bundle (never any database), re-runs every
reproducible claim with the deterministic interpreter, and writes a
verification report next to the bundle. Requires the lab package
installed (`pip install -e .` from the repo) — the interpreter is code,
and code is the only evidence that counts (§2).

## Scope and honesty

This is SIMULATION-STAGE evidence: every adversarial bound was
measured against a deterministic equation interpreter under named
attack choreographies, not against deployed software or live
attackers. 5 of the 11 score dimensions are imputed at the 5.0
floor (offline mode, disclosed in the dossier's scoring section).
The residual-attack disclosure in `release-package.md` §4 lists
every attack surface the final model still carries. No token,
no deployment, no live contract — §27/§28.
