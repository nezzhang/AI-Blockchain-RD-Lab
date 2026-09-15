# Publication Bundle: Separation-Keyed Fee Smoothing Escrow

Assembled by code from stored evidence only (§2 — no report-writer
LLM). The bundle is the complete public evidence set for the §7
rank-1 research candidate as of 2026-09-15T07:25:47.486574+00:00.

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
sha256sum \
adversarial-bounds.json dossier.md \
    lab-runtime/blockchain_rd_lab/__init__.py \
    lab-runtime/blockchain_rd_lab/formalization/__init__.py \
    lab-runtime/blockchain_rd_lab/simulation/__init__.py \
    lab-runtime/blockchain_rd_lab/simulation/adversarial.py \
    lab-runtime/blockchain_rd_lab/simulation/interpreter.py model-v3.json \
    prior-art.json redteam-history.json release-package.md \
    scenario-results.json score-decomposition.json verify.py

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
