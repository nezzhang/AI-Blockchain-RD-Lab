"""Optuna integration for simulation-based parameter search (§38 Phase 4).

Optuna is an OPTIONAL extra (`pip install '.[optuna]'`). When absent, the
lab falls back to the deterministic ParameterSweep — the pipeline never
requires it (§30 cost discipline: Optuna studies are opt-in and their
budget is bounded by n_trials).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from blockchain_rd_lab.simulation import (
    AnchorSeriesGenerator,
    MechanismSimulation,
    ScenarioKind,
    scenario_config,
)
from blockchain_rd_lab.simulation.interpreter import SimulationError

try:
    import optuna

    OPTUNA_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the extra
    optuna = None  # type: ignore[assignment]
    OPTUNA_AVAILABLE = False


class OptunaUnavailableError(SimulationError):
    """Raised when Optuna features are requested without the extra installed."""


class OptunaTuner:
    """Tune model parameters against a scalar objective over a scenario.

    The objective is DETERMINISTIC (fixed seed + scenario) so Optuna's
    search is reproducible; the tuner minimizes by default.
    """

    def __init__(
        self,
        sim: MechanismSimulation,
        objective_metric: Callable[[dict[str, float]], float],
        scenario: ScenarioKind = ScenarioKind.BASE,
        steps: int = 120,
        seed: int = 7,
    ) -> None:
        if not OPTUNA_AVAILABLE:
            raise OptunaUnavailableError(
                "optuna is not installed; install with: "
                "uv pip install -e '.[optuna]'  (or use ParameterSweep)"
            )
        self.sim = sim
        self.objective_metric = objective_metric
        self.cfg = scenario_config(scenario, steps=steps, seed=seed)
        self.series = AnchorSeriesGenerator(self.cfg).generate()

    def best_parameters(self, n_trials: int = 50) -> dict[str, float]:
        """Run the study; returns the best parameter set (min objective)."""
        model = self.sim.model
        param_names = [p.name for p in model.parameters]

        def objective(trial: Any) -> float:
            overrides = {
                p.name: trial.suggest_float(p.name, p.min_value, p.max_value)
                for p in model.parameters
            }
            sim = MechanismSimulation(model, parameters=overrides)
            run = sim.run(self.series)
            if run.failures:
                return float("inf")  # broken points sort last (§15 honesty)
            return self.objective_metric(run.metrics)

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=self.cfg.seed),
        )
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        best = study.best_params
        # Rebuild in declared order with float coercion.
        return {name: float(best[name]) for name in param_names if name in best}


def fallback_sweep(
    sim: MechanismSimulation,
    points: int = 5,
    steps: int = 120,
    seed: int = 7,
) -> list[dict[str, Any]]:
    """Deterministic grid sweep used when Optuna is unavailable."""
    from blockchain_rd_lab.simulation import ParameterSweep

    if not sim.model.parameters:
        return []
    first = sim.model.parameters[0]
    lo, hi = first.min_value, first.max_value
    span = (hi - lo) / max(points - 1, 1)
    grid = [lo + i * span for i in range(points)]
    out = ParameterSweep(sim, {first.name: grid}, steps=steps, seed=seed).run()
    return [
        {"parameters": p.parameters, "ok": p.ok, "metrics": p.metrics}
        for p in out
    ]
