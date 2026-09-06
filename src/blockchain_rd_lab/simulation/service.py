"""Phase 4 orchestration: simulate formalized candidates (§14, §15, §21).

Per candidate: load latest MathModel → run the §15 scenario battery →
Monte Carlo under base scenario → parameter sweep on coupling-like
parameters → persist ONE ExperimentRecord per candidate per run type with
full reproducibility fields (seed, parameters, results, §21).

State: FORMALIZED → SIMULATING → (SIMULATING | FAILED | RED_TEAM).
Simulation failures mark the candidate FAILED (§11); successes leave it
SIMULATING, ready for Phase 5 red team. Failures are recorded honestly —
never only favorable scenarios (§15, §29).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import model_from_dict
from blockchain_rd_lab.schemas import (
    Candidate,
    CandidateStatus,
    ExperimentRecord,
    utcnow,
)
from blockchain_rd_lab.simulation import (
    MonteCarloRunner,
    ParameterSweep,
    ScenarioBattery,
    ScenarioKind,
)
from blockchain_rd_lab.simulation.interpreter import SimulationError

SIMULATION_VERSION = "sim-0.1.0"


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


class SimulationService:
    """Runs the Phase 4 simulation battery over formalized candidates."""

    def __init__(self, database: LabDatabase, seed: int = 7, steps: int = 120) -> None:
        self.database = database
        self.seed = seed
        self.steps = steps

    # -- model access ----------------------------------------------------------

    def load_model(self, candidate: Candidate):
        dump = self.database.get_latest_math_model(candidate.id)
        if dump is None:
            raise SimulationError(f"no stored model for {candidate.id}")
        return model_from_dict(json.loads(dump))

    # -- experiment records (§21) ----------------------------------------------

    def _record(
        self,
        candidate_id: str,
        experiment_id: str,
        parameters: dict[str, Any],
        results: dict[str, Any],
        dataset: str,
        model_version: int = 1,
    ) -> ExperimentRecord:
        # §21 append-only discipline: a re-simulated model version gets a
        # distinct experiment id so the v1 evidence is never clobbered.
        suffix = "" if model_version <= 1 else f"-v{model_version}"
        return ExperimentRecord(
            experiment_id=f"{experiment_id}{suffix}",
            candidate_id=candidate_id,
            timestamp=utcnow(),
            git_commit=_git_commit(),
            parameters=parameters,
            dataset=dataset,
            model=f"mathmodel-v{model_version}",
            seed=self.seed,
            simulation_version=SIMULATION_VERSION,
            results=results,
        )

    # -- per-candidate battery ----------------------------------------------------

    def simulate_candidate(
        self,
        candidate: Candidate,
        mc_trials: int = 30,
        sweep_points: int = 5,
    ) -> dict[str, Any]:
        """Full battery for one candidate; persists 3 ExperimentRecords.

        Returns {"scenarios": {...}, "monte_carlo": {...}, "sweep": [...]}.
        """
        model = self.load_model(candidate)
        model_version = int(getattr(model, "version", 1))

        # Enter SIMULATING once (idempotent for re-runs).
        if candidate.status is CandidateStatus.FORMALIZED:
            candidate.transition(CandidateStatus.SIMULATING)
            self.database.save_candidate(candidate)

        from blockchain_rd_lab.simulation import MechanismSimulation

        sim = MechanismSimulation(model)

        # 1) §15 scenario battery
        battery = ScenarioBattery(sim, steps=self.steps, seed=self.seed)
        runs = battery.run()
        scenario_results = {
            kind: {
                "final": r.metrics,
                "failures": r.failures,
                "degenerate": r.degenerate,
            }
            for kind, r in runs.items()
        }
        self.database.save_experiment(
            self._record(
                candidate_id=candidate.id,
                experiment_id=f"{candidate.id}-scenarios",
                model_version=model_version,
                parameters={"steps": self.steps, "scenarios": [k.value for k in battery.scenarios]},
                results=scenario_results,
                dataset=f"synthetic-anchor-v1/seed-{self.seed}",
            )
        )

        # 2) Monte Carlo under base scenario
        from blockchain_rd_lab.simulation import scenario_config

        base_cfg = scenario_config(ScenarioKind.BASE, steps=self.steps, seed=self.seed)
        mc = MonteCarloRunner(sim, base_cfg, trials=mc_trials).run()
        mc_results = {
            "trials": mc.trials,
            "failures": mc.failures,
            "mean_final": mc.mean_final,
            "median_final": mc.median_final,
            "std_final": mc.std_final,
            "p5_final": mc.p5_final,
            "p95_final": mc.p95_final,
            "worst_final": mc.worst_final,
            "best_final": mc.best_final,
            "primary_symbol": mc.primary_symbol,
        }
        self.database.save_experiment(
            self._record(
                candidate_id=candidate.id,
                experiment_id=f"{candidate.id}-montecarlo",
                model_version=model_version,
                parameters={"trials": mc_trials, "steps": self.steps},
                results=mc_results,
                dataset=f"synthetic-anchor-v1/seed-{self.seed}-mc{mc_trials}",
            )
        )

        # 3) Parameter sweep on the first declared parameter (bounded grid)
        sweep_results: list[dict[str, Any]] = []
        if model.parameters:
            first = model.parameters[0]
            lo, hi = first.min_value, first.max_value
            span = (hi - lo) / max(sweep_points - 1, 1)
            grid = [lo + i * span for i in range(sweep_points)]
            sweep = ParameterSweep(
                sim, {first.name: grid}, steps=self.steps, seed=self.seed
            ).run()
            sweep_results = [
                {
                    "parameters": p.parameters,
                    "ok": p.ok,
                    "final": p.metrics,
                    "failures": p.failures,
                }
                for p in sweep
            ]
        self.database.save_experiment(
            self._record(
                candidate_id=candidate.id,
                experiment_id=f"{candidate.id}-sweep",
                model_version=model_version,
                parameters={"sweep_points": sweep_points, "steps": self.steps},
                results={"points": sweep_results},
                dataset=f"synthetic-anchor-v1/seed-{self.seed}",
            )
        )

        # Failed simulations (deterministic errors) mark the candidate FAILED.
        hard_failures = [
            (k, r["failures"])
            for k, r in scenario_results.items()
            if r["failures"]
        ]
        # §15 evidence quality: degenerate runs (states pinned at clip
        # bounds / frozen — every scenario indistinguishable) are NOT
        # clean evidence. The candidate stays simulating-resubmittable:
        # the model must be re-authored to the battery's input contract
        # (X_t anchor level ~1000, dX_t delta, states seed at 1000) —
        # the formalize prompt now states it. Reported, never hidden (§29).
        degenerate_scenarios = [
            k for k, r in scenario_results.items() if r.get("degenerate")
        ]
        if hard_failures:
            if candidate.status is CandidateStatus.SIMULATING:
                candidate.transition(CandidateStatus.FAILED)
                self.database.save_candidate(candidate)
        elif degenerate_scenarios:
            if candidate.status is CandidateStatus.SIMULATING:
                # §11: SIMULATING → FAILED is the honest transition for a
                # model that cannot exercise dynamics under the battery's
                # inputs — resubmit a corrected model (same idea, fresh
                # version) rather than advance on vacuous evidence.
                candidate.transition(CandidateStatus.FAILED)
                self.database.save_candidate(candidate)
        else:
            self.database.save_candidate(candidate)  # persist updated_at

        return {
            "scenarios": scenario_results,
            "monte_carlo": mc_results,
            "sweep": sweep_results,
            "hard_failures": hard_failures,
            "degenerate_scenarios": degenerate_scenarios,
        }

    def simulate_all(
        self,
        limit: int | None = None,
        mc_trials: int = 30,
        sweep_points: int = 5,
        only_status: CandidateStatus | None = CandidateStatus.FORMALIZED,
        artifacts_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Simulate every candidate in the given state (§35 isolation)."""
        candidates = self.database.list_candidates(status=only_status, limit=limit)
        outcomes: dict[str, Any] = {}
        for cand in candidates:
            try:
                outcomes[cand.id] = self.simulate_candidate(
                    cand, mc_trials=mc_trials, sweep_points=sweep_points
                )
            except SimulationError as exc:
                # Isolation (§35): record and continue with the next candidate.
                outcomes[cand.id] = {"error": str(exc)}
        if artifacts_dir is not None:
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            (artifacts_dir / "simulation-latest.json").write_text(
                json.dumps(
                    {
                        cid: {
                            "mc_mean": o.get("monte_carlo", {}).get("mean_final"),
                            "hard_failures": o.get("hard_failures", []),
                            "error": o.get("error"),
                        }
                        for cid, o in outcomes.items()
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        return outcomes
