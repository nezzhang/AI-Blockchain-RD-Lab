# r50 — instrument calibration, a real bug it caught, and the bundle evidence refresh

## What this is

The last research-integrity round before the §41 human publication gate.
Three moves, three commits:

1. **`d81123d` fix — the anchor-series PRNG was biased since Phase 4.** The
   mulberry32 port in `simulation/_DeterministicRandom` was mangled:
   uniforms averaged ~0.02 instead of 0.5 and the gaussian stream ran at
   mean +3.5 sigma. Every "base" §15 scenario since Phase 4 carried a
   hidden +0.73%/step drift, and near-identical seeds produced
   near-identical streams. Distribution tests (`tests/test_anchor_rng.py`)
   now pin the corrected stream.
2. **`4f30c61` feat — the calibration suite.** Known-answer validation of
   the instruments themselves (the gap r49 left: scores were hardened, but
   nothing had ever checked the §15/§20 batteries against mechanisms whose
   correct verdicts are already established). Four fixtures: a PID peg and
   a Compound/Aave-style kinked rate rule (known-good — must come out
   clean), a procyclical VaR-style buffer and a Terra/Luna-style mint-burn
   (known-flawed — must be caught). `lab calibrate` CLI;
   `reports/calibration-latest.{json,md}`; `tests/test_calibration.py`.
   **The suite's first run is what caught the PRNG bug** — the known-good
   PID peg drifted off-peg for no model-valid reason.
3. **`fb2ba8d` fix — the publication bundle's §15/MC evidence refreshed.**
   The bundle's `scenario-results.json` was generated under the biased
   generator, so its numbers were superseded. Re-ran the §15 battery
   (13 scenarios, steps=60, seed=7) and the 20-trial Monte Carlo from the
   published `model-v3.json` under the repaired generator via
   `scripts/r50_refresh_bundle_sim.py`.

## What the refresh changed (and what it did not)

- **Monte Carlo**: mean_final 1005.6340 → 1005.6172 (0.0017%), p5/p95
  band narrowed (the old band was inflated by the false drift),
  0 failures / 20 trials — unchanged.
- **§15 battery**: 13/13 scenarios still clean, 0 degenerate — the
  qualitative robustness verdict holds. The per-scenario final-state
  values were materially wrong (e.g. whale_attack C_t 0.021 → 0.850) and
  were replaced.
- **Score**: 6.7250 unchanged — the §19 dimensions are evidence-backed
  agent/bridge scores, not computed from the sim aggregates.
- **§20 adversarial bounds**: unaffected. The attack battery drives
  crafted series with no randomness; `adversarial-bounds.json` stands and
  the verifier reproduces all 19 calibrated-sweep headlines identically.

## Provenance discipline (§21 append-only)

- The re-runs are stored as NEW records `cand-9200b07691c3-scenarios-v3-r50`
  / `cand-9200b07691c3-montecarlo-v3-r50`, each naming the record it
  supersedes in `parameters.supersedes`. The biased `-v3` records remain
  in the store; nothing was deleted or rewritten.
- `dossier.md` and `release-package.md` were REGENERATED from the store by
  the §2 code path (not hand-edited) — the dossier lists both the
  superseded and the refreshed records.
- The bundle's `lab-runtime/` now ships the repaired generator, so
  `verify.py` exercises exactly the code that produced the shipped numbers.
- The bundle README carries an r50 disclosure note; `MANIFEST.json` was
  regenerated; `verify.py` re-run → all REPRODUCED.

## Gates

627 pytest ✓, ruff ✓, mypy (64 files) ✓, `lab calibrate` ✓,
bundle `verify.py` exit 0 with zero `[!]` ✓.

## What remains — the §41 human gate

The lab's work is done. `docs/launch/publication-checklist.md` is the
human's checklist: self-service verification of the bundle, review of the
claims surface and launch drafts, then the **publish / hold / revise**
decision — to be recorded by the human, here or in a follow-up doc.
