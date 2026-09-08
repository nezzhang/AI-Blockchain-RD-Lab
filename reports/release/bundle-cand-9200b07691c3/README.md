# Publication Bundle: Separation-Keyed Fee Smoothing Escrow

Assembled by code from stored evidence only (§2 — no report-writer
LLM). The bundle is the complete public evidence set for the §7
rank-1 research candidate as of 2026-09-08T13:48:51.542306+00:00.

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

```bash
sha256sum dossier.md release-package.md model-v3.json \
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
