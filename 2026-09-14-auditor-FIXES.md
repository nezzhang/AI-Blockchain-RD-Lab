# Audit Findings — 2026-09-14

Repository audited: `nezzhang/AI-Blockchain-RD-Lab` (`main`)

Scope: `AUDITING.md` load-bearing table, with explicit checks of §19 scorer, §20 gate, §15/§20 attack battery, and §14 interpreter. Findings from rounds 27–30 were excluded per `CLAUDE.md`.

> Audit execution note: the execution environment could not resolve `github.com`, so a filesystem `git clone` was not possible. The audit was performed against the public `main` source served by GitHub Raw, including the exact files named by `AUDITING.md`, and the relevant existing test files. No claim below depends on an uninspected local checkout.

## F1 — HIGH: §20 “profitability” is an LLM-controlled trust bit, so a fatal flaw can survive the gate

### Status
**Confirmed. New; not a round-27–30 re-report.**

### Root cause
`RedTeamReport.strongest_attack_is_profitable` is a free boolean supplied by the Red Team agent schema. `RedTeamService._apply_findings()` confirms a fatal flaw only when:

```text
rt.verdict == "fatal"
and rt.strongest_attack_is_profitable
```

There is no deterministic recomputation of profitability, no cross-check against `AttackVector.profitable_for_attacker`, and no requirement that the boolean be backed by a simulation/battery result. The service therefore treats an LLM assertion as the decisive economic predicate while documenting the gate as deterministic.

Relevant source:
- `src/blockchain_rd_lab/redteam/__init__.py`: `RedTeamReport` defines `strongest_attack_is_profitable: bool = False`.
- `src/blockchain_rd_lab/redteam/service.py`: `_apply_findings()` uses that boolean directly at the fatal-flaw gate.

### Why the existing test suite does not protect the boundary
`tests/test_redteam.py::TestFatalFlawGate::test_fatal_verdict_nonprofitable_not_confirmed` deliberately sets the same boolean to `False` and expects a fatal verdict to remain `RED_TEAM`. That test validates the current trust boundary; it does not establish that the profitability claim was independently proven.

### Exploit / failure mode
A red-team model can return:

```json
{
  "verdict": "fatal",
  "strongest_attack": "...profitable attack narrative...",
  "strongest_attack_is_profitable": false
}
```

The candidate is not rejected even though the `verdict` says `fatal`. Nothing in the deterministic layer checks whether the attack actually has positive economic edge.

This directly violates the claimed property “fatal only when the strongest attack is also profitable” as a deterministic evidence rule: the decisive fact is still supplied by the LLM.

### Remediation
Make profitability an evidence-derived field, not an agent assertion. The minimum safe design is:

1. Persist the attack identity/parameters and a deterministic payoff/edge calculation.
2. Require the fatal verdict to reference a stored attack whose computed attacker payoff is strictly positive under an explicit cost model.
3. Fail closed when profitability is unknown or unmeasured.
4. Keep the LLM field only as a hypothesis/comment, never as the gate predicate.
5. Add a regression test in which the LLM says `false` while the deterministic fixture reports positive attacker edge; the candidate must still be rejected.

---

## F2 — MEDIUM: calibrated attack patterns can be re-tested with default parameters during long-window transit classification

### Status
**Confirmed. New; not a round-27–30 re-report.**

### Root cause
In `simulation/adversarial.py`, the first run uses the caller's full `PatternSpec`. For long-window confirmation, the code constructs a new `PatternSpec` with only:

```python
PatternSpec(
    kind=spec.kind,
    steps=spec.steps * 2,
    park_at=...,
)
```

All other parameters silently revert to dataclass defaults: `amplitude=0.05`, `creep_rate=0.005`, `grind_fraction=0.5`, `harvest_shift=-0.6`, etc.

The first run can therefore produce a real edge under a calibrated variant (for example `pump_unwind` amplitude 0.02 or 0.10), then the transit test can decide whether that edge is “in transit” by running a **different attack** at the default calibration.

### Why this matters to disclosure
The long-window result is not merely an independent confirmation window; it is used to remove `*_drawn` metrics from `bound_candidates` and place them in `in_transit` instead. That is a classification decision that can suppress the headline edge.

Because calibration tags are explicitly part of the published adversarial census, resetting the calibration during this decision breaks the meaning of the calibrated result: the classifier is no longer answering “does this same attack remain a transient?”, but “does the default attack eventually re-base?”.

### Concrete source-level proof
For any calibrated spec such as:

```python
PatternSpec(
    kind=AttackPattern.PUMP_UNWIND,
    steps=60,
    amplitude=0.02,
)
```

the current long-window constructor creates a new object whose `amplitude` is **0.05**, not **0.02**.

The same reset affects other non-default fields whenever supplied by a caller.

### Existing tests / auditability
The inspected red-team tests cover the §20 fatal-flaw branch, schema validation, and service isolation, but do not pin preservation of `PatternSpec` calibration across long-window classification. The round-29/30 history fixes publication completeness and verifier reproduction of calibrated headlines; they do not fix this execution-time calibration reset.

### Remediation
Clone the complete pattern spec while changing only the window length and fields intentionally tied to the doubled horizon. For example:

```python
long_spec = spec.model_copy(
    update={
        "steps": spec.steps * 2,
        "park_at": min(spec.park_at * 2, spec.steps * 2 - 2),
    }
)
```

Add a regression test asserting that every attack parameter except explicitly horizon-scaled fields is identical between the short and long specs.

---

## F3 — MEDIUM: `e` and `pi` are valid MathModel syntax but the interpreter rejects them

### Status
**Confirmed. New; not a round-27–30 re-report.**

### Root cause
The formalization layer explicitly treats `e` and `pi` as mathematical constants. `MathModel.referenced_symbols()` excludes `_MATH_CONSTANTS`, so a model JSON equation such as:

```text
y_t = exp(1)
```

is fine, and an equation using a named constant such as:

```text
y_t = e ^ X_t
```

is not rejected by the model's undeclared-symbol integrity check.

However, `EquationInterpreter._check_tree()` allows a bare `Name` only when it is declared or is a whitelisted function. It does **not** exempt `_MATH_CONSTANTS`. Therefore a valid model containing `e` or `pi` fails at interpreter validation with “symbol 'e' used but not declared” (or the analogous `pi` error).

### Why this is a fidelity bug
`AUDITING.md` asks whether arithmetic “faithfully expresses the model JSON”. Here the model schema and interpreter disagree on the language accepted by the system. A model can pass §13 validation and still be un-executable solely because it uses a documented constant.

### Existing tests / auditability
`tests/test_simulation.py::TestInterpreter` covers power-caret normalization, division-by-zero, undeclared symbols, forbidden constructs, unknown functions, and `ln` domain failure. It does not contain an `e`/`pi` execution case.

### Remediation
Add a constants map, e.g.:

```python
_CONSTANTS = {"e": math.e, "pi": math.pi}
```

Then:
- exempt `_MATH_CONSTANTS` from the undeclared-symbol rejection in `_check_tree()`; and
- resolve those names in `_eval_node()` to the corresponding numeric constants.

Add tests for both constants and for exact model-JSON round-tripping of equations using them.

---

## §19 imputation-floor hypothesis — investigated, but not filed as a new vulnerability

The scorer does indeed assign missing dimensions the configured `5.0` floor and has no completeness requirement. That is already explicitly disclosed by the repository as an honest weakness: 5/11 dimensions are imputed at the offline floor.

I did **not** find a new candidate-controlled bypass in the inspected §19 path that is distinct from that disclosed weakness. The scorer iterates only configured dimensions, and the ranking service does not let unknown extra dimensions inflate the score. The more serious issue is methodological: “missing” is treated as neutral 5.0 rather than insufficient evidence.

I therefore did not re-file the known weakness as a new finding.

---

## Rounds 27–30 exclusion check

The following classes were deliberately not re-reported because `CLAUDE.md` records them as fixed:

- round-27 stale/superseded red-team dossier verdicts;
- round-27 duplicated/mis-routed dossier sections and missing imputed-dimension disclosure;
- round-27 bundle dependency/verification/runtime closure issues;
- round-27 verification timestamp/template and prior-art dedupe/backing-file defects;
- round-28 README checksum coverage generation;
- round-29 calibration-line dedupe/completeness in release §4b;
- round-30 verifier coverage of default + calibrated attack headlines;
- round-30 manifest/README/prose-to-JSON publication consistency checks.

These findings above concern live §20 trust semantics, live attack-classification execution, and live interpreter/model-language fidelity instead.
