# Phase 4 Report — Simulation

**Status:** complete
**Principle:** LLM proposes. Code tests. Evidence decides. (§2)
**Scope:** §38 Phase 4 — simulation framework, Monte Carlo, historical
simulation, parameter sweeps, Optuna (§14 interface, §15 scenario battery,
§21 reproducibility).

## Implemented

| Component | File(s) | Notes |
|-----------|---------|-------|
| Safe equation interpreter | `simulation/interpreter.py` | Executes Phase-3 `MathModel` equations via whitelisted Python AST evaluation: `LHS = RHS` split, only arithmetic + whitelisted functions (`ln log exp sqrt abs max min sum mean std clip`), `^`→`**`, constants `e`/`pi`; AST node/operator/function whitelists reject everything else; undeclared symbols double-checked (defense in depth under the §13 schema validator); division by zero, `ln`/`sqrt` domain errors, and overflow raise `SimulationError` — deterministic failure, never NaN creep |
| Simulation interface (§14) | `simulation/__init__.py::MechanismSimulation` | `parameters` (model defaults, overridable, unknown names rejected), `initial_state()`, `transition()` (one equation pass), `observe()`, `metrics()` (final/min/max/total return/volatility/max drawdown), `run()` (full loop with state roll-forward: LHS `S_t1` steps state `S_t` by symbol-family matching) |
| §15 scenario battery | `SimulationRun`/`ScenarioBattery`/`ScenarioKind` | All 13 required scenarios: base, bull, bear, extreme inflation, extreme deflation, liquidity crisis, bank run, oracle failure (report freeze), oracle manipulation (spike), governance attack, whale attack, market crash, black swan — never only favorable scenarios |
| Monte Carlo (§14) | `MonteCarloRunner`/`MonteCarloResult` | N trials under one scenario; seed-derived distinct-but-reproducible trial seeds; aggregates mean/median/std/p5/p95/worst/best + failure count |
| Historical simulation (§14) | `HistoricalReplay` + `AnchorSeriesGenerator` | Replays a recorded anchor series (`X_t`, `dX_t`) through the model — fully deterministic, no randomness; synthetic series today, real datasets plug in unchanged |
| Parameter sweeps | `ParameterSweep`/`SweepPoint` | Deterministic grid over declared parameters (undeclared names rejected); failed points reported, never hidden (§29) |
| Optuna integration | `simulation/optuna_tuner.py` | Optional extra (`[analytics]`, optuna 4.9.0 installed); `OptunaTuner` TPE search over parameter ranges against a caller-defined scalar objective (deterministic: fixed seed + scenario); broken grid points score `inf`; `fallback_sweep` for no-optuna environments |
| Orchestration + §21 records | `simulation/service.py::SimulationService` | Per candidate: load latest stored model → 13-scenario battery + Monte Carlo + first-parameter sweep → persists THREE `ExperimentRecord`s (id, candidate, timestamp, git_commit, parameters, dataset, model, seed, simulation_version, results); transitions FORMALIZED → SIMULATING; deterministic hard failures mark FAILED (§11); `simulate_all` isolates per-candidate failures (§35) and writes `simulation/runs/simulation-latest.json` |
| CLI | `cli.py` | `lab simulate [candidate_id] [--trials --sweep-points --seed --steps --limit]` (replaces stub); pre-conditions enforced (must be FORMALIZED/SIMULATING) |

## Evidence (E2E demo, `database/lab.db`)

- `lab simulate --trials 20 --steps 60` over the 15 FORMALIZED candidates:
  **15/15 simulated, 0 hard failures**, all now SIMULATING (§11).
- 45 experiment rows (3 per candidate: `-scenarios`, `-montecarlo`,
  `-sweep`), each carrying seed=7, `simulation_version=sim-0.1.0`, and
  `git_commit=04d8710…` — a researcher can reproduce any run (§21).
- Scenario battery sanity: extreme_inflation final (5.21× initial) >
  base (1.24×) > black_swan (1.18× with 5% max drawdown); oracle failure
  freezes anchor deltas after the shock step and stays near base.
- Optuna smoke: 20-trial TPE search converged on coupling 0.237 /
  floor -0.0166 / cap 0.0372 for a 10% total-return target.
- Run artifact: `simulation/runs/simulation-latest.json` (15 candidates,
  MC means, hard failures, errors).

## Tests

- 177 passing (was 147): `tests/test_simulation.py` adds 30 tests —
  interpreter (fixture evaluation, `^` power, div-by-zero, undeclared
  symbol, forbidden construct, unknown function, `ln` domain), framework
  (history/metrics, unknown parameter rejection, 13-scenario coverage,
  battery full run, inflation>base ordering, cap bounds compounding,
  seed reproducibility, seed divergence), Monte Carlo (aggregate
  ordering worst≤p5≤median≤p95≤best, reproducibility), sweep (grid
  monotonicity in coupling, undeclared rejection, failure reporting),
  Optuna (availability, parameter discovery, reproducibility, fallback
  sweep), service (3 experiment records with §21 fields, FORMALIZED→
  SIMULATING, corrupted model → FAILED, §35 isolation across candidates,
  missing-model error), CLI (unknown candidate exit 1, status
  precondition).
- `tests/test_cli.py` stub list updated (simulate implemented; redteam is
  the new PHASE 5 pointer).

## Lint

- `ruff check src tests` — all checks pass.

## Type checking

- `mypy` — no issues in 33 source files.

## Bugs found and fixed

- `_fn_sqrt` referenced before definition in `_FUNCTIONS` — reordered.
- Interpreter parsed whole equations in `eval` mode (assignments are a
  SyntaxError) — split `LHS = RHS`, evaluate RHS only, bind to LHS.
- AST operator objects (`ast.Div` inside `BinOp`) tripped the node
  whitelist — added explicit operator/unaryop whitelisting with
  per-BinOp operator checks.
- `MechanismSimulation.run()` never fed computed outputs back into state
  (`S_t1` → `S_t`) so supply stayed at its initial value — added
  `_roll_state_forward` with symbol-family matching.
- Arbitrary initial state 1.0 — changed to a documented 1000.0
  supply-like convention.
- `model_copy(update={...})` with plain dicts bypassed Pydantic field
  validation in tests (serialization warnings, silent type drift) —
  rebuilt via full `model_validate` or proper model objects.

## Deliberate Non-Goals (Phase discipline, §39)

- No adversarial/red-team analysis of simulation results (Phase 5).
- No scoring changes and no ranking (Phase 6) — simulation results are
  recorded but do not yet feed `scoring/`.
- No real historical datasets — the historical track runs on synthetic
  anchor series; real data ingestion is a later data phase (§22).
- No agent-based simulation yet (§14 lists it; the equation-driven
  interface is the Phase 4 scope) and no DuckDB analytics store.
- No GUI/visualization.

## Known Limitations

- All 15 demo candidates share the generic fixture model, so E2E rows
  are identical by design; model diversity requires a real provider.
- Interpreter supports scalar math plus sequence functions (`sum`, `mean`,
  `std` over Python lists) but no stochastic primitives *inside*
  equations — randomness lives in the scenario generators (seeded), which
  keeps models reproducible.
- `_roll_state_forward` matches `S_t1`/`S_next`-style suffixes; models
  using entirely unrelated LHS names for state updates would need an
  explicit mapping (a §13 open question the designer must answer).
- Optuna studies are in-memory; best parameters are returned, not yet
  persisted as experiment records (future: tune-then-store flow).
- Metrics are state-path-based (first state variable); richer metric
  selection arrives with scoring integration (Phase 6).

## Next phase

Phase 5 — Adversarial Testing (§38, §17): game-theoretic analysis,
attack vectors (§15 attack scenarios provide inputs), red-team agents
critiquing mechanisms and models; state SIMULATING → RED_TEAM; findings
feed the fatal-flaw gate so confirmed flaws cap scores (§20).
