# Fix List — Round 2 — `cand-9200b07691c3` Publication Bundle

**Method this round:** every fix from round 1 was checked by actually executing
the bundle's own code (interpreter, scenario battery, Monte Carlo, and the
full attack-pattern battery — 8 default + 19 calibrated variants), not just
by re-reading text. All of it reproduced exactly against the published
values. Round-1 fixes #1–#4 are confirmed resolved under real execution, not
just inspection — no further action needed on those.

## SHOULD FIX

### 1. `release-package.md` §4b silently omits 2 of 19 calibrated attack records

`adversarial-bounds.json` contains 19 calibrated attack-pattern variants, but
§4b's "Measured Attack-Pattern Bounds" only narrates 17 of them. Missing:

- `pump_unwind @amplitude=0.02` — measured edge **+0.337374** on `C_t_drawn`
- `pump_unwind @amplitude=0.1` — measured edge **+0.999925** on `C_t_drawn`

`pump_unwind` appears exactly once in the current markdown (the
default-calibration line only). These two numbers aren't out of line with
the pattern's other readings, but they're measured, stored evidence that
isn't reaching the disclosure document — same class of bug as the round-1
dossier issue: whatever generates §4b isn't iterating the full calibration
set for every pattern kind.

**Fix:** whatever assembles §4b should iterate every record in
`adversarial-bounds.json` for a given `kind`, not a hardcoded/partial subset.
Regenerate from source; verify afterward that every `calibration`-tagged
record in the JSON has a corresponding line in the markdown (count should be
19, not 17).

## OPTIONAL / MINOR

### 2. `verify.py`'s docstring has a stale usage example

```
Usage:
    .venv/bin/python scripts/r25_verify_bundle.py \
        reports/release/bundle-cand-9200b07691c3
```
This predates the round-1 fix that made the runtime self-contained. The
README now correctly documents `python verify.py .` as the invocation; the
module docstring should say the same thing instead of the old path.

## Verification checklist

- [ ] Count of calibration-tagged records in `adversarial-bounds.json` per
      pattern `kind` equals the count of `@...` lines under that kind in
      `release-package.md` §4b (currently 19 vs 17)
- [ ] `verify.py`'s docstring `Usage:` matches the README's actual invocation
