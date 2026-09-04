# Phase 3 Report — Formalization (Mathematical Models)

**Status:** complete
**Principle:** LLM proposes. Code tests. Evidence decides. (§2)
**Scope:** §38 Phase 3 — mathematical model schema, Mechanism Designer,
equation storage, assumptions (§13).

## Implemented

| Component | File(s) | Notes |
|-----------|---------|-------|
| MathModel schema | `src/blockchain_rd_lab/formalization/__init__.py` | `MathModel` (variables with roles/units, parameters with range+default, equations, assumptions with `critical` flag, constraints/invariants/failure conditions, open questions, rationale); `ModelEquation` enforces ASCII pseudo-math, exactly one `=`, balanced parentheses, banned constructs (`==`, `<=`, `+=`...); `ModelParameter` enforces `min ≤ default ≤ max` |
| Deterministic integrity checks (§2) | same | `referenced_symbols` / `declared_symbols` / `undeclared_symbols` / `unused_symbols` — every identifier in an equation must be a declared variable or parameter symbol (function whitelist: `ln exp sqrt abs max min sum mean std clip`); `open_questions` required (§13: never assume the first equation is correct) |
| Mechanism Designer agent | `formalization/agents.py` | `MechanismDesignerAgent` (name `quant`, strong tier, temp 0.2 per `config/agents.yaml`); prompt encodes §13 discipline: declare every symbol, ASCII pseudo-math, explicit assumptions/invariants, alpha/smoothing/lag/caps/floors/uncertainty/oracle-frequency/statistical-confidence as open questions, no mid-equation symbol invention; oracle-required candidates must define oracle input variables, reporting frequency, revision policy |
| Equation storage | `database/__init__.py` | New `math_models` table (candidate_id, version, model_json, rationale, created_at) — models are **versioned, never overwritten**; `save_math_model`, `latest_model_version`, `get_latest_math_model`, `list_math_models` |
| FormalizationService | `formalization/service.py` | Per-candidate loop with §35 failure isolation; assigns next version on store; transition PRIOR_ART_CHECKED → FORMALIZED (§11); offline `_formalize_one_fixture`/`formalize_all_fixtures` path uses the exact same validation + storage code with deterministic fixture proposals; run artifact `formalization/models/formalization-latest.json` |
| Fixture models | `formalization/agents.py::build_math_model_fixture` | Generic anchor-coupled supply rule: `g_raw_t = alpha * dX_t / X_t`, `g_t = clip(g_raw_t, f, c)`, `S_t1 = S_t * (1 + g_t)` with declared variables/parameters, critical assumption (truthful oracle), invariant + failure condition, four §13 open questions |
| CLI | `cli.py` | `lab formalize [--mock-fixtures] [--limit] [candidate_id]` (replaces stub); dry-mock real-provider path fails closed with §30 hint; single-candidate and batch modes; Rich summary table |

## Evidence (E2E demo, `database/lab.db`)

- `lab formalize --mock-fixtures` over the 15 PRIOR_ART_CHECKED
  candidates from Phase 2: **15/15 formalized, 0 failed**, 15 model
  versions stored (`math_models` rows), run artifact written.
- State after: `formalized = 15`, `prior_art_checked = 0` (§11 machine
  respected; single transition, no status mutations outside
  `Candidate.transition()`).
- Stored seed-candidate model verified round-trip: 3 equations, 6
  variables, 3 parameters, 4 open questions — integrity checks clean
  (`undeclared_symbols() == ∅`, `unused_symbols() == ∅`).

## Tests

- 147 passing (was 123): `tests/test_formalization.py` adds 25 tests —
  equation syntax gates (unicode math, `==`, double assignment, unbalanced
  parens), parameter range/default validation, model integrity
  (undeclared-symbol rejection, function whitelist, required open
  questions), agent happy path + failure + wrong payload + §13 prompt
  assertions, service happy path / version increment / per-candidate
  failure isolation (failed candidate left PRIOR_ART_CHECKED for retry),
  offline fixture path, DB save/list/versioning round-trips.
- CLI stub test updated: `formalize` removed from stub list (simulate is
  now the PHASE 4 pointer).

## Lint

- `ruff check src tests` — all checks pass.

## Type checking

- `mypy` — no issues in 30 source files.

## Deliberate Non-Goals (Phase discipline, §39)

- No simulation of the equations — Monte Carlo / historical / sweeps are
  Phase 4. The model schema is designed to be machine-executable later
  (ASCII expressions, declared symbols, whitelisted functions) but nothing
  executes them yet.
- No adversarial review of the models (Phase 5 red team), no scoring
  changes.
- No Optuna, no DuckDB analytics store (Phase 4).

## Known Limitations

- Equation validation is *structural* (ASCII, one `=`, balanced parens,
  declared symbols) — it does not yet parse full grammar or type-check
  units; a stricter evaluator arrives with the Phase 4 simulation engine,
  which will be the first real executor of these expressions.
- Offline fixtures produce the same generic supply-rule shape for every
  candidate; per-category model diversity requires a real provider.
- The designer's alternative-parameterization requirement is enforced only
  through `open_questions` (≥1 required); richer "propose N variants"
  discipline can be layered on in the improvement loop (§11 IMPROVEMENT).
- Model versioning counts monotonically per candidate; no diffing between
  versions yet.

## Next phase

Phase 4 — Simulation (§38, §14): generic simulation interface
(parameters, initial_state, transition(), observe(), metrics(), run()),
Monte Carlo, historical simulation, parameter sweeps, Optuna — executing
the Phase 3 equations as the first consumers of `math_models`.
