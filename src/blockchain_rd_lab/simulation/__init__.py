"""Simulation framework (Phase 4, §14/§15).

Generic interface: parameters, initial_state, transition(), observe(),
metrics(), run(). The MechanismStep executes Phase-3 MathModel equations
via the safe interpreter; scenario generators produce input series;
runners execute trials deterministically (seed control, §21).

Scenario coverage per §15 — never only show favorable scenarios:
base, bull, bear, extreme inflation, extreme deflation, liquidity crisis,
bank run, oracle failure, oracle manipulation, governance attack,
whale attack, market crash, black swan.
"""

from __future__ import annotations

import enum
import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.simulation.interpreter import (
    EquationInterpreter,
    SimulationError,
)


class ScenarioKind(enum.StrEnum):
    """§15 scenario list — the required stress battery."""

    BASE = "base"
    BULL = "bull"
    BEAR = "bear"
    EXTREME_INFLATION = "extreme_inflation"
    EXTREME_DEFLATION = "extreme_deflation"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    BANK_RUN = "bank_run"
    ORACLE_FAILURE = "oracle_failure"
    ORACLE_MANIPULATION = "oracle_manipulation"
    GOVERNANCE_ATTACK = "governance_attack"
    WHALE_ATTACK = "whale_attack"
    MARKET_CRASH = "market_crash"
    BLACK_SWAN = "black_swan"


ALL_SCENARIOS: tuple[ScenarioKind, ...] = tuple(ScenarioKind)


# ---------------------------------------------------------------------------
# Input series generation (deterministic per seed)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioConfig:
    """Parameters that shape a scenario's anchor-delta series."""

    kind: ScenarioKind = ScenarioKind.BASE
    steps: int = 120
    mean_delta_pct: float = 0.0
    vol_pct: float = 0.005
    shock_step: int | None = None
    shock_pct: float = 0.0
    freeze_after_shock: bool = False
    seed: int = 7


class AnchorSeriesGenerator:
    """Deterministic anchor (X_t, dX_t) series for a scenario (§15).

    Phase 4 runs on synthetic series calibrated to scenario shapes; the
    historical-simulation track replays recorded datasets (see
    HistoricalReplay) and real datasets arrive with the data phase.
    """

    def __init__(self, config: ScenarioConfig) -> None:
        self.cfg = config

    def generate(self) -> list[dict[str, float]]:
        cfg = self.cfg
        rng = _DeterministicRandom(cfg.seed)
        x = 1000.0
        series: list[dict[str, float]] = []
        for t in range(cfg.steps):
            if cfg.freeze_after_shock and cfg.shock_step is not None and t > cfg.shock_step:
                dx = 0.0  # oracle stalled: no more reports (§15 oracle failure)
            else:
                pct = rng.gauss(cfg.mean_delta_pct, cfg.vol_pct)
                if cfg.shock_step is not None and t == cfg.shock_step:
                    pct += cfg.shock_pct
                    if cfg.freeze_after_shock:
                        dx = x * pct
                        series.append(self._row(x, dx))
                        x += dx
                        continue
                dx = x * pct
            series.append(self._row(x, dx))
            x += dx
        return series

    @staticmethod
    def _row(x: float, dx: float) -> dict[str, float]:
        return {"X_t": x, "dX_t": dx}


class _DeterministicRandom:
    """Small deterministic PRNG (mulberry32) — same series for same seed (§21)."""

    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF or 1

    def _next(self) -> int:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = ((t ^ (t >> 15)) * t) & 0xFFFFFFFF
        t = (t ^ (t + (t >> 7))) & t & 0xFFFFFFFF  # keep 32-bit
        return t

    def uniform(self) -> float:
        return (self._next() >> 8) / 16777216.0

    def gauss(self, mu: float, sigma: float) -> float:
        # Box-Muller with two uniforms.
        u1 = max(self.uniform(), 1e-12)
        u2 = self.uniform()
        return mu + sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


# ---------------------------------------------------------------------------
# Scenario library (§15)
# ---------------------------------------------------------------------------


def scenario_config(kind: ScenarioKind, steps: int = 120, seed: int = 7) -> ScenarioConfig:
    """Standard §15 scenario shapes, parameterized on the anchor series."""
    table: dict[ScenarioKind, dict[str, Any]] = {
        ScenarioKind.BASE: dict(mean_delta_pct=0.0002, vol_pct=0.002),
        ScenarioKind.BULL: dict(mean_delta_pct=0.001, vol_pct=0.003),
        ScenarioKind.BEAR: dict(mean_delta_pct=-0.001, vol_pct=0.004),
        ScenarioKind.EXTREME_INFLATION: dict(
            mean_delta_pct=0.02, vol_pct=0.01,
            shock_step=steps // 3, shock_pct=0.15,
        ),
        ScenarioKind.EXTREME_DEFLATION: dict(
            mean_delta_pct=-0.02, vol_pct=0.01,
            shock_step=steps // 3, shock_pct=-0.15,
        ),
        ScenarioKind.LIQUIDITY_CRISIS: dict(
            mean_delta_pct=-0.002, vol_pct=0.02,
            shock_step=steps // 2, shock_pct=-0.10,
        ),
        ScenarioKind.BANK_RUN: dict(
            mean_delta_pct=0.0002, vol_pct=0.004,
            shock_step=steps // 2, shock_pct=-0.30,
        ),
        ScenarioKind.ORACLE_FAILURE: dict(
            mean_delta_pct=0.0002, vol_pct=0.002,
            shock_step=steps // 3, shock_pct=0.0, freeze_after_shock=True,
        ),
        ScenarioKind.ORACLE_MANIPULATION: dict(
            mean_delta_pct=0.0002, vol_pct=0.002,
            shock_step=steps // 2, shock_pct=0.50,  # attacker spikes the report
        ),
        ScenarioKind.GOVERNANCE_ATTACK: dict(
            mean_delta_pct=0.0005, vol_pct=0.003,
            shock_step=steps // 2, shock_pct=0.25,
        ),
        ScenarioKind.WHALE_ATTACK: dict(
            mean_delta_pct=0.0003, vol_pct=0.005,
            shock_step=(2 * steps) // 3, shock_pct=0.35,
        ),
        ScenarioKind.MARKET_CRASH: dict(
            mean_delta_pct=-0.003, vol_pct=0.015,
            shock_step=steps // 2, shock_pct=-0.25,
        ),
        ScenarioKind.BLACK_SWAN: dict(
            mean_delta_pct=0.0002, vol_pct=0.002,
            shock_step=int(steps * 0.9), shock_pct=-0.60,
        ),
    }
    cfg_kwargs = dict(table[kind])
    return ScenarioConfig(kind=kind, steps=steps, seed=seed, **cfg_kwargs)


# ---------------------------------------------------------------------------
# Simulation interface (§14)
# ---------------------------------------------------------------------------


class MechanismSimulation:
    """Generic simulation of a MathModel over an input series (§14).

    parameters     — from model parameters (defaults, overridable)
    initial_state  — initial values for state variables
    transition()   — one step: evaluate equations with current symbols
    observe()      — record step observables
    metrics()      — final deterministic metrics
    run()          — full loop with invariant checks
    """

    def __init__(
        self,
        model: MathModel,
        parameters: dict[str, float] | None = None,
    ) -> None:
        self.model = model
        self.interp = EquationInterpreter(model)
        self.parameters: dict[str, float] = {
            p.name: p.default for p in model.parameters
        }
        if parameters:
            unknown = set(parameters) - set(self.parameters)
            if unknown:
                raise SimulationError(
                    f"unknown parameter(s): {sorted(unknown)}; "
                    f"declared: {sorted(self.parameters)}"
                )
            self.parameters.update(parameters)
        self._state_vars = [v for v in model.variables if v.role.value == "state"]
        self._input_vars = [v for v in model.variables if v.role.value == "input"]

    def initial_state(self, overrides: dict[str, float] | None = None) -> dict[str, float]:
        """Initial state values: 1000.0 per state var unless overridden.

        Convention: state quantities are supply-like magnitudes; callers
        pass explicit overrides for anything else.
        """
        state: dict[str, float] = {v.symbol: 1000.0 for v in self._state_vars}
        if overrides:
            state.update(overrides)
        return state

    def transition(
        self,
        symbols: dict[str, float | list[float]],
    ) -> dict[str, float]:
        """One step: evaluate all equations; returns computed LHS values."""
        return self.interp.evaluate(symbols)

    def observe(self, step: int, symbols: dict[str, float]) -> dict[str, float]:
        return {"step": float(step), **{k: v for k, v in symbols.items()}}

    def run(
        self,
        series: Sequence[dict[str, float]],
        initial_state: dict[str, float] | None = None,
    ) -> SimulationRun:
        """Execute the full loop; checks invariants each step (§15)."""
        state = self.initial_state(initial_state)
        state_symbols: dict[str, float | list[float]] = dict(state)
        observations: list[dict[str, float]] = []
        history: list[dict[str, float]] = []
        failures: list[str] = []

        for t, row in enumerate(series):
            step_symbols: dict[str, float | list[float]] = {
                **{
                    p.symbol: self.parameters[p.name]
                    for p in self.model.parameters
                },
                **state_symbols,
                **dict(row),
            }
            try:
                computed = self.transition(step_symbols)
            except SimulationError as exc:
                failures.append(f"step {t}: {exc}")
                break
            for lhs, value in computed.items():
                step_symbols[lhs] = value

            # Roll state forward: an equation may write the *next* state
            # under a stepped symbol (e.g. S_t1 for state S_t). Match by
            # suffix family so the loop actually feeds back.
            self._roll_state_forward(computed, state_symbols)

            obs = self.observe(
                t,
                {k: float(v) for k, v in step_symbols.items() if isinstance(v, (int, float))},
            )
            observations.append(obs)
            history.append(dict(obs))

        run = SimulationRun(
            steps=len(history),
            final_state={
                k: float(v) for k, v in state_symbols.items() if isinstance(v, (int, float))
            },
            history=history,
            failures=failures,
            parameters=dict(self.parameters),
        )
        run.metrics = self.metrics(run)
        return run

    def _roll_state_forward(
        self,
        computed: dict[str, float],
        state_symbols: dict[str, float | list[float]],
    ) -> None:
        """Feed computed outputs back into state for the next step.

        An LHS exactly matching a state symbol updates it directly; an LHS
        matching a state symbol plus a time-step suffix (S_t1 for S_t,
        S_next for S) steps the state forward.
        """
        state_names = {v.symbol for v in self._state_vars}
        for lhs, value in computed.items():
            if lhs in state_names:
                state_symbols[lhs] = value
                continue
            for name in state_names:
                if lhs.startswith(name):
                    suffix = lhs[len(name):]
                    if suffix and all(ch.isdigit() or ch in "_next" for ch in suffix):
                        state_symbols[name] = value
                        break

    def metrics(self, run: SimulationRun) -> dict[str, float]:
        """Deterministic summary metrics over the run history."""
        state_syms = [v.symbol for v in self._state_vars]
        primary = state_syms[0] if state_syms else None
        out: dict[str, float] = dict(run.final_state)
        if primary and run.history:
            path = [row[primary] for row in run.history if primary in row]
            if path:
                out[f"{primary}_final"] = path[-1]
                out[f"{primary}_min"] = min(path)
                out[f"{primary}_max"] = max(path)
                if path[0] != 0:
                    out[f"{primary}_total_return_pct"] = (path[-1] / path[0] - 1.0) * 100
                if len(path) > 1:
                    rets = [
                        path[i] / path[i - 1] - 1
                        for i in range(1, len(path))
                        if path[i - 1] != 0
                    ]
                    if rets:
                        out[f"{primary}_volatility_pct"] = statistics.pstdev(rets) * 100
                        out[f"{primary}_max_drawdown_pct"] = _max_drawdown_pct(path)
        out["n_steps"] = float(run.steps)
        out["n_failures"] = float(len(run.failures))
        return out


def _max_drawdown_pct(path: list[float]) -> float:
    peak = path[0]
    mdd = 0.0
    for x in path:
        peak = max(peak, x)
        if peak > 0:
            mdd = max(mdd, (peak - x) / peak)
    return mdd * 100


class SimulationRun(BaseModel):
    """One executed simulation (§14 run() output)."""

    model_config = ConfigDict(validate_assignment=True)

    steps: int = 0
    final_state: dict[str, float] = Field(default_factory=dict)
    history: list[dict[str, float]] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    parameters: dict[str, float] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Runners: Monte Carlo, scenario battery, historical replay, sweeps
# ---------------------------------------------------------------------------


class MonteCarloRunner:
    """N randomized trials under one scenario (§14 Monte Carlo)."""

    def __init__(
        self,
        sim: MechanismSimulation,
        config: ScenarioConfig,
        trials: int = 100,
    ) -> None:
        self.sim = sim
        self.config = config
        self.trials = trials

    def run(self) -> MonteCarloResult:
        runs: list[SimulationRun] = []
        state_syms = [v.symbol for v in self.sim._state_vars]
        primary = state_syms[0] if state_syms else None
        for i in range(self.trials):
            cfg = ScenarioConfig(
                kind=self.config.kind,
                steps=self.config.steps,
                mean_delta_pct=self.config.mean_delta_pct,
                vol_pct=self.config.vol_pct,
                shock_step=self.config.shock_step,
                shock_pct=self.config.shock_pct,
                freeze_after_shock=self.config.freeze_after_shock,
                seed=self.config.seed + i,  # distinct but reproducible (§21)
            )
            series = AnchorSeriesGenerator(cfg).generate()
            runs.append(self.sim.run(series))
        return MonteCarloResult.from_runs(
            runs,
            primary_symbol=primary or "",
            trials=self.trials,
        )


class MonteCarloResult(BaseModel):
    """Aggregated Monte Carlo statistics (deterministic)."""

    model_config = ConfigDict(validate_assignment=True)

    trials: int = 0
    failures: int = 0
    mean_final: float = 0.0
    median_final: float = 0.0
    std_final: float = 0.0
    p5_final: float = 0.0
    p95_final: float = 0.0
    worst_final: float = 0.0
    best_final: float = 0.0
    primary_symbol: str = ""

    @classmethod
    def from_runs(
        cls, runs: list[SimulationRun], primary_symbol: str, trials: int
    ) -> MonteCarloResult:
        finals: list[float] = []
        failures = 0
        for r in runs:
            if r.failures:
                failures += 1
            if primary_symbol:
                key = f"{primary_symbol}_final"
                if key in r.metrics:
                    finals.append(r.metrics[key])
        if not finals:
            return cls(trials=trials, failures=failures, primary_symbol=primary_symbol)
        finals.sort()
        n = len(finals)
        return cls(
            trials=trials,
            failures=failures,
            mean_final=statistics.fmean(finals),
            median_final=statistics.median(finals),
            std_final=statistics.pstdev(finals),
            p5_final=finals[max(0, int(0.05 * n) - 1)],
            p95_final=finals[min(n - 1, int(0.95 * n))],
            worst_final=finals[0],
            best_final=finals[-1],
            primary_symbol=primary_symbol,
        )


class ScenarioBattery:
    """Run the full §15 scenario battery over a simulation."""

    def __init__(
        self,
        sim: MechanismSimulation,
        steps: int = 120,
        seed: int = 7,
        scenarios: Sequence[ScenarioKind] | None = None,
    ) -> None:
        self.sim = sim
        self.steps = steps
        self.seed = seed
        self.scenarios = list(scenarios) if scenarios else list(ALL_SCENARIOS)

    def run(self) -> dict[str, SimulationRun]:
        out: dict[str, SimulationRun] = {}
        for kind in self.scenarios:
            cfg = scenario_config(kind, steps=self.steps, seed=self.seed)
            series = AnchorSeriesGenerator(cfg).generate()
            out[kind.value] = self.sim.run(series)
        return out


class HistoricalReplay:
    """Historical simulation: replay a recorded series through the model.

    The series is a list of {"X_t": ..., "dX_t": ...} rows (synthetic in the
    offline lab; real datasets plug in unchanged later). Deterministic —
    no randomness at all (§21).
    """

    def __init__(self, sim: MechanismSimulation) -> None:
        self.sim = sim

    def run(self, series: Sequence[dict[str, float]]) -> SimulationRun:
        return self.sim.run(series)


class ParameterSweep:
    """Deterministic grid sweep over declared parameters.

    Each point runs the scenario battery per §15-lite (base + extremes) to
    keep sweep cost bounded; points whose runs fail are reported, not
    hidden (§29: do not hide failed experiments).
    """

    def __init__(
        self,
        sim: MechanismSimulation,
        sweep_params: dict[str, Sequence[float]],
        scenario: ScenarioKind = ScenarioKind.BASE,
        steps: int = 120,
        seed: int = 7,
    ) -> None:
        unknown = set(sweep_params) - set(sim.parameters)
        if unknown:
            raise SimulationError(f"sweep on undeclared parameter(s): {sorted(unknown)}")
        self.sim = sim
        self.sweep_params = sweep_params
        self.scenario = scenario
        self.steps = steps
        self.seed = seed

    def grid(self) -> list[dict[str, float]]:
        keys = sorted(self.sweep_params)
        points: list[dict[str, float]] = [{}]
        for k in keys:
            values = list(self.sweep_params[k])
            if not values:
                raise SimulationError(f"empty sweep range for {k}")
            points = [dict(p, **{k: v}) for p in points for v in values]
        return points

    def run(self) -> list[SweepPoint]:
        cfg = scenario_config(self.scenario, steps=self.steps, seed=self.seed)
        series = AnchorSeriesGenerator(cfg).generate()
        out: list[SweepPoint] = []
        for point in self.grid():
            try:
                run = self.sim.run(series, initial_state=None) if not point else None
                # Rebuild simulation with swept parameters (MechanismSimulation
                # is cheap to construct; this keeps it immutable).
                sim = MechanismSimulation(self.sim.model, parameters=point)
                run = sim.run(series)
                out.append(
                    SweepPoint(
                        parameters=point,
                        ok=True,
                        metrics=run.metrics,
                        failures=run.failures,
                    )
                )
            except SimulationError as exc:
                out.append(
                    SweepPoint(
                        parameters=point,
                        ok=False,
                        metrics={},
                        failures=[str(exc)],
                    )
                )
        return out


class SweepPoint(BaseModel):
    """One parameter-sweep grid point outcome."""

    model_config = ConfigDict(frozen=True)

    parameters: dict[str, float]
    ok: bool
    metrics: dict[str, float]
    failures: list[str]
