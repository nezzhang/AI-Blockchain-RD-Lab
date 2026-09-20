# Response: 2026-09-19 audit (interpreter finiteness + tokenomics divergence)

## Verification scope

Both findings were verified by live execution against `main` at commit
`57a4c78` (`fix(r46): self-audit of the elasticity sweep`) before any fix, per
§2 (audits are verified, never trusted). Each fix is at the generator and
pinned by a test that **fails on the pre-fix code** (verified by re-running
the new tests against a `HEAD` worktree / a `git stash` of the fix).

## F1 — Interpreter docstring overclaims: inf/NaN propagate through `*`/`+`/`-`/`/`

**Verdict: CONFIRMED; fixed at the interpreter source.**

The module docstring claimed "deterministic failure, never NaN creep," but
that held only for the guarded ops (`_safe_div`, `_safe_pow`, `ln`, `sqrt`).
Python float `*`/`+`/`-`/`/` overflow to `+/-inf` with **no** `OverflowError`
(unlike `**`), and `inf - inf`, `0 * inf`, `inf / inf` yield NaN. A standalone
`EquationInterpreter.evaluate()` returned `inf`/`NaN` unchecked. The
run-level `_check_nan` caught it before any `SimulationRun` persisted, so no
published number was affected — but the interpreter-level contract was false,
and `initial_state()` accepted caller-supplied `inf`/`nan` overrides.

**Fix** (`simulation/interpreter.py`, `simulation/__init__.py`): every computed
LHS in `evaluate()` is checked with `math.isfinite` and raises `SimulationError`
on a non-finite result; `initial_state()` rejects non-finite overrides; the
docstring now states the source-level guarantee.

**Regression pins** (`tests/test_simulation.py::TestInterpreter`):
`test_mul_overflow_raises_not_silent_inf`, `test_inf_minus_inf_never_returns_nan`,
`test_zero_times_inf_never_returns_nan`, `test_finite_result_does_not_raise`,
`test_initial_state_inf_override_rejected`, `test_initial_state_nan_override_rejected`,
`test_initial_state_finite_override_accepted`. All seven raise-path tests
**fail on pre-fix code** ("DID NOT RAISE SimulationError"); the finite cases
confirm ordinary math is untouched.

## F2 — Tokenomics battery coerces a non-finite edge to `0.0`, hiding a runaway burn

**Verdict: CONFIRMED; fixed at the measurement and the scoring layer.**

`tokenomics/battery.py` had `edge = {k: v if isfinite(v) else 0.0 ...}`. The
edge is `pattern − base`; for `total_burned`, a runaway burn (the death-spiral
signature the battery exists to measure) yields `inf − finite = +inf`, coerced
to `0.0` — reported downstream as "no edge." Proven live: an unbounded driver
burning `-inf`/step produced `headline = 0.0`, which `score_design_with_dynamics`
mapped to death-spiral resistance **10.0 (perfect)**. The structural path
(`_supply_fn_is_bounded`) already scores such a driver 0; only the dynamics
path trusted the coerced headline.

**Corpus impact: NONE.** All 13 registered drivers clamp to `[-1, 1]`
(`_supply_fn_is_bounded` enforces it); a census over every registered driver's
full battery found **no non-finite edge** (pinned by
`test_registered_drivers_never_diverge`). The fix is behavior-preserving on
every committed artifact; no r42/r45 number changes.

**Fix** (`tokenomics/battery.py`, `tokenomics/scoring.py`): non-finite edges
are recorded in a new `SupplyAttackBound.diverged_metrics` and removed from
finite headline arithmetic; a diverged bound-metric dominates the headline
(`headline = math.inf`, note carries "DIVERGED … scored at the floor").
`DynamicsEvidence` gains a disclosed `diverged_surfaces`. In
`score_design_with_dynamics`, a diverged mint/drain/ratchet surface maps the
corresponding dimension to the **FLOOR (0.0)** — never to `10.0`, and never
parsed as vacuous.

**Regression pins** (`tests/test_tokenomics.py::TestDivergenceDisclosure`):
`test_diverging_burn_is_never_a_zero_headline`, `test_divergence_note_discloses`,
`test_registered_drivers_never_diverge` (census), and
`test_diverging_burn_scores_death_spiral_floor`. All four **fail on pre-fix
code** — the scoring pin reproduces the exact bug (`drain_fraction=0.0`).

## Class sweep (the r35/r36 discipline — the pattern one level up)

Grep for `isfinite`/`isnan`/`or 0.0`/`else 0.0` across `src/` found two other
non-finite sites, both in `tokenomics/stock.py` (the r43 stock layer). Both are
**integrator guards, not measurement-neutralizations**, and do not hide a runaway:

- `stock.py:318` (`rate → 0.0` on non-finite) guards the integrator and is
  immediately clamped to `[-1, 1]`; a diverging supply still drives
  `s_cur → 0 → v_next = inf → excesses inf → growing → SPIRAL` verdict. The
  alarm survives to the verdict.
- `stock.py:327-330` guard the representable range on long spirals (a
  deliberate, disclosed modeling bound), with the same SPIRAL propagation.

F2 was the sole site where a non-finite value silently became the *measured
edge that is itself the headline*. No other instance of the class found.

## Validation

- 587 tests passed (576 pre-existing + 11 new pins), no skips introduced
- Ruff clean (`src`, `tests`)
- Mypy clean (60 source files)
- New-pin integrity: each raise/floor test verified to FAIL against pre-fix
  source (interpreter pins via a `HEAD` worktree venv; tokenomics pins via a
  `git stash` of the battery/scoring fix), then PASS against the fix
- No published artifact changed (the F2 census confirms the committed registry
  is fully bounded); `reports/release/bundle-cand-9200b07691c3-VERIFICATION.md`
  was touched only by the verifier's own wall-clock header on a re-run and was
  reverted to keep the working tree scoped to the fix
