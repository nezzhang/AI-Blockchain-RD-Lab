# Audit Response — 2026-09-14-auditor-FIXES.md (round 33)

Response discipline (§2, applied to audits): every finding was
verified against the store and by live execution BEFORE any fix;
every fix is at the generator; every fix is pinned by a probe the
day it ships. Verdict per finding: **all three findings were
correct.** None was wrong.

## F1 (HIGH) — the §20 gate trusted an LLM-supplied profit bit

**Confirmed.** `rt.strongest_attack_is_profitable` was a free field
on the agent's report, and the deterministic gate keyed its
rejection decision on it — deterministic code asserting a trust bit.

Store ground truth, measured before fixing: of 16 REJECTED
candidates, exactly ONE was rejected by the §20 gate
(Population-Linked Supply, cand-7f2f07fd4e9a, 2026-09-04) — and
that candidate has NO stored MathModel and ZERO battery records.
The one historical gate rejection rested entirely on the assertion.
(F1 was real but latent: no measured-flaw rejection was ever issued
on an unverified claim.)

**Fix (as specified by the audit):** the gate now MEASURES.

- fatal + profitable rejects ONLY when the deterministic battery's
  worst headline edge on the latest stored model exceeds
  `FLAW_EDGE_THRESHOLD = 400.0` — now a canonical library constant in
  `simulation/adversarial.py`, the same number every census since
  r16 used, so gate and censuses can no longer drift apart.
- Fail-closed for rejection when unmeasured: no stored model,
  vacuous bounds, or all edges under threshold → NOT rejected by
  the gate (the fatal flag alone still surfaces in the flaw
  description).
- The LLM boolean is demoted to a recorded HYPOTHESIS (audit
  point 4).
- Every gate evaluation persists a §21 record
  (`fatal_flaw_v2_measured`: verdict, hypothesis, measured
  evidence, decision) — the audit trail audit point 5 asked for.

The historical rejection carries a gate-v2 re-evaluation record
documenting its evidence class (assertion-only). §11 correction
remains the operator's decision; REJECTED is terminal by design —
no resurrection path exists, and none was added.

**Pinned by** 3 probes in `tests/test_redteam.py`, including the
audit's own regression: fatal+profitable+healthy-measured-model →
NOT rejected (with the §21 record showing unmeasured-under-threshold
evidence); a genuinely flawed model (the r20 multiplicative-ratchet
class, measured worst edge 2266.29) → REJECTED with the measurement
cited in the flaw description.

## F2 (MEDIUM) — long-window calibration reset

**Confirmed by execution.** The r19 long-window transit confirmation
rebuilt the doubled-window `PatternSpec` from kind/steps/park_at
alone; every other calibration field silently reset to dataclass
defaults — a calibrated variant's transit decision was made by the
DEFAULT attack.

**Fix:** `spec.model_copy(update={"steps": spec.steps*2,
"park_at": ...})` — the full calibration is carried into the doubled
window.

## F3 (MEDIUM) — e/pi interpreter rejection

**Confirmed by execution.** `e` and `pi` are §13-valid symbols
(`MathModel._MATH_CONSTANTS`) but `EquationInterpreter` rejected
models using them ("used but not declared") — a schema-valid model
that could not execute.

**Fix:** the interpreter resolves bare `e`/`pi` to their constants
(`_CONSTANTS` in `simulation/interpreter.py`). Declared variables
still win — the schema is the contract (pinned: a model declaring
`e=42` reads 42, not 2.718...).

## The F2 fix's own finding: the pin ambiguity

Re-sweeping the calibrated grid under the fixed constructor surfaced
a classification ambiguity the r18 pin rule cannot resolve by
POSITION: on the successor, `crash_park @park_shift=-0.9` reads
`L_f_drawn = 900.0` — L_f (the fast EMA) ends at 100.0, which is
BOTH its clip floor AND the crashed level.

- The r18 Cyclic precedent (drained pool stopped at a floor that
  coincides with the level) says: pin = disclosed edge.
- But L_f measured INERT: relaxing the floor to −1e9 and re-running
  the SAME attack leaves the trajectory identical — the EMA
  converged to its fixed point (the level); the clip never bound.
  (The X→50 probe is the only case where that floor binds.)

Position cannot tell a stopped drain from a converged EMA whose
level coincides with its bound. **The counterfactual can.**

**Fix:** `_pin_is_load_bearing(model, spec, battery, sym)` in
`simulation/adversarial.py` — relax that one state's clip bound,
re-run the same attack: final value unchanged → inert bound → the
state ARRIVED (classified by the layers that follow); final value
moves out of `[lo, hi]` → load-bearing pin → the r18 rule stands.
Wired at all four classification guard sites (level-arrival,
EMA-shape filter, long-window confirmation, resonance quiet-tail).
Fail-closed: an unbuildable counterfactual is treated as
load-bearing (the first draft failed OPEN here — caught live before
commit; it would have exonerated Cyclic's genuinely drained Z_t
pool back into regime_tracking, the exact anti-hiding regression).

**Pinned by** 6 probes in `tests/test_degenerate_detection.py`
(`TestRound33AuditFixes`), including all three historical pin
lineages: Cyclic Z_t load-bearing (headline 509.71 stays disclosed),
the wage-pool W_t (60-step draining transit → 120/240
pinned-and-convicted), the swap-board B_t conviction, inert-pin
exoneration (the 900.0 case → regime_tracking), and the
fail-closed branches.

## Re-sweep under the fixed battery (r33 §21 census records)

Both decision candidates, 8 defaults + all 19 calibrations (27 rows
each), diffed against the PUBLISHED generations (r20/r22):

- **Incumbent (cand-e74d830a9479): ZERO drift.** All 27 rows
  reproduce the published numbers exactly. The r22 claim "zero
  edges >150 in 54 runs" SURVIVES the fixed battery (worst 33.25).
- **Successor (cand-9200b07691c3): 4 drifts, each an honesty
  improvement**, never a hidden regression:
  - `crash_park @-0.9`: L_f_drawn 900.0 moves in_transit →
    regime_tracking (the measured exoneration above; the honest
    headline G_t_drawn 0.8692 is unchanged).
  - `grind_harvest @-0.9`: headline 0.8634 → 0.9739, its transit
    decision now made by its OWN attack at the doubled window
    (F2's exact victim class).
  - `pump_unwind @amplitude=0.02`: headline 0.3374 → 0.0, with
    C_t honestly in_transit (confirmed by its own low-amplitude
    attack at the doubled window — a fourth F2 victim surfaced by
    the corrected sweep grid).
  - The published worst headline is UNCHANGED at 32.6375
    (wash_flow @0.04 — not park-style, unaffected as predicted).

## Verifier defects the regeneration surfaced (also fixed)

Both fixed at the one source (`scripts/r25_verify_bundle.py`) and
re-shipped in the bundle:

1. `sorted()` over tuples containing dicts — a TypeError under a
   fresh Python 3.12 (the r30 isolated run's interpreter differs
   from this machine's `/usr/bin/python3`, which is Xcode's 3.9).
   Lesson: the isolated-environment proof must pin the interpreter,
   not just the PATH.
2. Census generation overlap: the bundle JSON now carries the
   r20+r22+r33 records; the calibrated re-run comparison and the
   §4b completeness check must take the NEWEST record per
   kind+calibration / count DISTINCT pairs — the same rule §4b
   renders by.

## End state

- Gates: ruff clean, mypy clean (53 files), **457 tests passed**
  (+8: 2 net gate probes + 6 TestRound33AuditFixes).
- Bundle regenerated through the builder (never hand-patched);
  isolated verify (`/usr/bin/env -i`, framework Python 3.12, no
  lab paths importable): **exit 0 — 51 REPRODUCED + 2 CONSISTENT +
  0 NOT-REPRODUCIBLE**; 8/8 default + 19/19 calibrated headlines
  reproduce from the published files alone.
- AUDITING.md updated: the §20 gate row now points at the measured
  gate (`redteam/service.py`), the test count is current, and the
  round pointer covers r27-33 (four external audits).
