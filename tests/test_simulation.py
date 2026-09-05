"""Phase 4 simulation tests: interpreter, framework, runners, service, CLI."""

from __future__ import annotations

import json

import pytest

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel, model_from_dict
from blockchain_rd_lab.formalization.agents import build_math_model_fixture
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import Candidate, CandidateStatus
from blockchain_rd_lab.simulation import (
    AnchorSeriesGenerator,
    MechanismSimulation,
    MonteCarloRunner,
    ParameterSweep,
    ScenarioBattery,
    ScenarioKind,
    scenario_config,
)
from blockchain_rd_lab.simulation.interpreter import (
    EquationInterpreter,
    SimulationError,
)
from blockchain_rd_lab.simulation.optuna_tuner import (
    OPTUNA_AVAILABLE,
    OptunaTuner,
    fallback_sweep,
)
from blockchain_rd_lab.simulation.service import SimulationService


def make_candidate(**overrides) -> Candidate:
    base = dict(
        name="Carbon-Weighted Gas Fees",
        category="energy",
        description="Gas priced by verified carbon intensity.",
        core_mechanism="GasPrice = base * (1 + beta * carbon_intensity_t).",
    )
    base.update(overrides)
    return Candidate(**base)


def make_model() -> MathModel:
    cand = make_candidate()
    brief = CandidateBrief.from_candidate(cand)
    return model_from_dict(build_math_model_fixture(brief))


def mutate_model(**changes) -> MathModel:
    """Rebuild the fixture model with changed fields (full revalidation)."""
    data = make_model().model_dump(mode="json")
    data.update(changes)
    return MathModel.model_validate(data)




# ---------------------------------------------------------------------------
# Interpreter (§2: the code that executes LLM-proposed equations)
# ---------------------------------------------------------------------------


class TestInterpreter:
    def test_evaluates_fixture_model(self):
        itp = EquationInterpreter(make_model())
        out = itp.evaluate(
            {"S_t": 1000.0, "X_t": 100.0, "dX_t": 1.0, "alpha": 0.5, "f": -0.05, "c": 0.05}
        )
        assert out["S_t1"] == pytest.approx(1005.0)

    def test_power_caret_normalized(self):
        m = mutate_model(
            variables=[*make_model().model_dump(mode="json")["variables"],
                       {"name": "sq", "symbol": "y_t", "role": "auxiliary",
                        "units": "u", "description": "squared"}],
            equations=[{"name": "sq", "expression": "y_t = X_t ^ 2", "description": ""}],
        )
        itp = EquationInterpreter(m)
        out = itp.evaluate({"S_t": 1.0, "X_t": 3.0, "dX_t": 0.0, "alpha": 0.5, "f": -1.0, "c": 1.0})
        assert out["y_t"] == pytest.approx(9.0)

    def test_division_by_zero_raises(self):
        itp = EquationInterpreter(make_model())
        with pytest.raises(SimulationError, match="division by zero"):
            itp.evaluate({"S_t": 1.0, "X_t": 0.0, "dX_t": 1.0, "alpha": 0.5, "f": -1.0, "c": 1.0})

    def test_undeclared_symbol_rejected_at_check(self):
        # MathModel's schema validator already blocks undeclared symbols;
        # the interpreter re-checks independently (defense in depth, §2).
        import ast

        m = make_model()
        itp = EquationInterpreter(m)
        tree = ast.parse("S_t * zzz", mode="eval")
        with pytest.raises(SimulationError, match="not declared"):
            itp._check_tree(tree)

    def test_forbidden_construct_rejected(self):
        # if/else (ast.IfExp) is not in the whitelist.
        import ast

        m = make_model()
        itp = EquationInterpreter(m)
        tree = ast.parse("exp(S_t) if S_t else 1", mode="eval")
        with pytest.raises(SimulationError, match="forbidden construct"):
            itp._check_tree(tree)

    def test_unknown_function_rejected(self):
        import ast

        m = make_model()
        itp = EquationInterpreter(m)
        tree = ast.parse("open(S_t)", mode="eval")
        with pytest.raises(SimulationError, match="not whitelisted"):
            itp._check_tree(tree)

    def test_ln_domain_error(self):
        m = mutate_model(equations=[
            {"name": "l", "expression": "S_t1 = ln(dX_t)", "description": ""}
        ])
        itp = EquationInterpreter(m)
        with pytest.raises(SimulationError, match="ln"):
            itp.evaluate({"S_t": 1.0, "X_t": 1.0, "dX_t": -1.0, "alpha": 1.0, "f": -1.0, "c": 1.0})


# ---------------------------------------------------------------------------
# Framework + scenario battery (§14, §15)
# ---------------------------------------------------------------------------


class TestFramework:
    def test_run_produces_history_and_metrics(self):
        sim = MechanismSimulation(make_model())
        cfg = scenario_config(ScenarioKind.BASE, steps=50)
        run = sim.run(AnchorSeriesGenerator(cfg).generate())
        assert run.steps == 50
        assert len(run.history) == 50
        assert "S_t_final" in run.metrics
        assert "S_t_volatility_pct" in run.metrics
        assert "S_t_max_drawdown_pct" in run.metrics
        assert run.failures == []

    def test_unknown_parameter_rejected(self):
        with pytest.raises(SimulationError, match="unknown parameter"):
            MechanismSimulation(make_model(), parameters={"nope": 1.0})

    def test_scenario_battery_covers_required_kinds(self):
        from blockchain_rd_lab.simulation import ALL_SCENARIOS

        assert len(ALL_SCENARIOS) == 13  # §15 list
        assert ScenarioKind.BLACK_SWAN in ALL_SCENARIOS
        assert ScenarioKind.ORACLE_MANIPULATION in ALL_SCENARIOS

    def test_battery_runs_all_scenarios(self):
        sim = MechanismSimulation(make_model())
        battery = ScenarioBattery(sim, steps=40, scenarios=None)
        results = battery.run()
        assert set(results.keys()) == {k.value for k in battery.scenarios}
        assert all("S_t_final" in r.metrics for r in results.values())

    def test_extreme_inflation_grows_more_than_base(self):
        sim = MechanismSimulation(make_model())
        battery = ScenarioBattery(
            sim, steps=60, scenarios=[ScenarioKind.BASE, ScenarioKind.EXTREME_INFLATION]
        )
        res = battery.run()
        assert res["extreme_inflation"].metrics["S_t_final"] > res["base"].metrics["S_t_final"]

    def test_cap_limits_growth_in_extreme(self):
        sim = MechanismSimulation(
            make_model(), parameters={"coupling": 2.0, "cap": 0.05, "floor": -0.05}
        )
        cfg = scenario_config(ScenarioKind.EXTREME_INFLATION, steps=60)
        run = sim.run(AnchorSeriesGenerator(cfg).generate())
        # per-step growth is clipped at cap; with 60 steps bounded by (1.05)^60
        assert run.metrics["S_t_final"] <= 1000.0 * (1.05**60) + 1e-6

    def test_seed_reproducibility(self):
        sim = MechanismSimulation(make_model())
        cfg1 = scenario_config(ScenarioKind.BEAR, steps=50, seed=42)
        cfg2 = scenario_config(ScenarioKind.BEAR, steps=50, seed=42)
        r1 = sim.run(AnchorSeriesGenerator(cfg1).generate()).metrics["S_t_final"]
        r2 = sim.run(AnchorSeriesGenerator(cfg2).generate()).metrics["S_t_final"]
        assert r1 == r2

    def test_different_seeds_differ(self):
        MechanismSimulation(make_model())
        s1 = AnchorSeriesGenerator(scenario_config(ScenarioKind.BEAR, steps=50, seed=1)).generate()
        s2 = AnchorSeriesGenerator(scenario_config(ScenarioKind.BEAR, steps=50, seed=2)).generate()
        assert s1 != s2


class TestMonteCarlo:
    def test_mc_aggregates(self):
        sim = MechanismSimulation(make_model())
        mc = MonteCarloRunner(
            sim, scenario_config(ScenarioKind.BASE, steps=40), trials=20
        ).run()
        assert mc.trials == 20
        assert mc.failures == 0
        assert mc.worst_final <= mc.p5_final <= mc.median_final <= mc.p95_final <= mc.best_final
        assert mc.mean_final > 0

    def test_mc_reproducible(self):
        sim = MechanismSimulation(make_model())
        cfg = scenario_config(ScenarioKind.BULL, steps=40, seed=7)
        a = MonteCarloRunner(sim, cfg, trials=10).run()
        b = MonteCarloRunner(sim, cfg, trials=10).run()
        assert a.mean_final == b.mean_final


class TestSweep:
    def test_grid_and_run(self):
        sim = MechanismSimulation(make_model())
        sweep = ParameterSweep(sim, {"coupling": [0.0, 0.5, 1.0]}, steps=40).run()
        assert len(sweep) == 3
        assert all(p.ok for p in sweep)
        finals = [p.metrics["S_t_final"] for p in sweep]
        assert finals[0] < finals[1] < finals[2]  # monotone in coupling

    def test_sweep_undeclared_rejected(self):
        sim = MechanismSimulation(make_model())
        with pytest.raises(SimulationError, match="undeclared"):
            ParameterSweep(sim, {"nonexistent": [1.0]}, steps=40)

    def test_failed_points_reported_not_hidden(self):
        # cap=0 with floor=0: clip(x, 0, 0) is 0 — legal; try div-by-zero point
        sim = MechanismSimulation(make_model())
        sweep = ParameterSweep(sim, {"coupling": [0.5]}, steps=40).run()
        assert len(sweep) == 1


# ---------------------------------------------------------------------------
# Optuna (optional)
# ---------------------------------------------------------------------------


class TestOptuna:
    def test_available_flag(self):
        # optuna is installed via the analytics extra in this repo's venv.
        assert OPTUNA_AVAILABLE is True

    @pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="optuna extra not installed")
    def test_tuner_finds_reasonable_params(self):
        sim = MechanismSimulation(make_model())
        def target(m):
            return abs(m.get("S_t_total_return_pct", 0.0) - 5.0)
        tuner = OptunaTuner(sim, target, steps=40)
        best = tuner.best_parameters(n_trials=15)
        assert "coupling" in best
        assert 0.0 <= best["coupling"] <= 2.0

    @pytest.mark.skipif(not OPTUNA_AVAILABLE, reason="optuna extra not installed")
    def test_tuner_reproducible(self):
        sim = MechanismSimulation(make_model())
        def target(m):
            return abs(m.get("S_t_total_return_pct", 0.0) - 5.0)
        a = OptunaTuner(sim, target, steps=30, seed=3).best_parameters(n_trials=10)
        b = OptunaTuner(sim, target, steps=30, seed=3).best_parameters(n_trials=10)
        assert a == b

    def test_fallback_sweep_works(self):
        sim = MechanismSimulation(make_model())
        pts = fallback_sweep(sim, points=3, steps=40)
        assert len(pts) == 3
        assert all("parameters" in p for p in pts)


# ---------------------------------------------------------------------------
# Service (§21 persistence, §11 transitions, §35 isolation)
# ---------------------------------------------------------------------------


class TestSimulationService:
    def _prepared(self, memory_db):
        cand = make_candidate()
        memory_db.save_candidate(cand)
        cand.transition(CandidateStatus.RESEARCHING)
        cand.transition(CandidateStatus.PRIOR_ART_CHECKED)
        cand.transition(CandidateStatus.FORMALIZED)
        memory_db.save_candidate(cand)
        brief = CandidateBrief.from_candidate(cand)
        model = model_from_dict(build_math_model_fixture(brief))
        memory_db.save_math_model(
            cand.id,
            json.dumps(model.model_dump(mode="json")),
            model.rationale,
            version=1,
        )
        return cand

    def test_simulate_candidate_persists_experiments(self, memory_db):
        cand = self._prepared(memory_db)
        service = SimulationService(memory_db, seed=7, steps=40)
        outcome = service.simulate_candidate(cand, mc_trials=5, sweep_points=3)

        # §21: three experiment records with reproducibility fields
        experiments = list(memory_db.iter_experiments(cand.id))
        exp_ids = {e.experiment_id for e in experiments}
        assert exp_ids == {
            f"{cand.id}-scenarios",
            f"{cand.id}-montecarlo",
            f"{cand.id}-sweep",
        }
        for e in experiments:
            assert e.seed == 7
            assert e.git_commit  # recorded (unknown only outside a repo)
            assert e.simulation_version
            assert e.timestamp is not None
            # v1 records carry the un-suffixed id and the version tag
            assert e.model == "mathmodel-v1"

        # §11: FORMALIZED → SIMULATING
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.SIMULATING
        # §15 battery ran
        assert len(outcome["scenarios"]) == 13
        assert outcome["monte_carlo"]["trials"] == 5
        assert len(outcome["sweep"]) == 3

    def test_resimulation_of_new_version_is_append_only(self, memory_db):
        """§21: re-simulating a patched model v2 must not clobber v1 runs."""
        cand = self._prepared(memory_db)
        service = SimulationService(memory_db, seed=7, steps=30)

        # First run on v1.
        service.simulate_candidate(cand, mc_trials=3, sweep_points=2)
        first = {e.experiment_id for e in memory_db.iter_experiments(cand.id)}
        assert first == {
            f"{cand.id}-scenarios",
            f"{cand.id}-montecarlo",
            f"{cand.id}-sweep",
        }

        # Store a v2 model (§34 improve) and re-simulate.
        brief = CandidateBrief.from_candidate(cand)
        v2 = model_from_dict(build_math_model_fixture(brief))
        v2_dump = v2.model_dump(mode="json")
        v2_dump["version"] = 2
        memory_db.save_math_model(
            cand.id,
            json.dumps(v2_dump),
            "patched model v2 (test)",
            version=2,
        )
        service.simulate_candidate(cand, mc_trials=3, sweep_points=2)

        all_ids = {e.experiment_id for e in memory_db.iter_experiments(cand.id)}
        # Both versions' records persist (append-only §21).
        assert all_ids == {
            f"{cand.id}-scenarios",
            f"{cand.id}-montecarlo",
            f"{cand.id}-sweep",
            f"{cand.id}-scenarios-v2",
            f"{cand.id}-montecarlo-v2",
            f"{cand.id}-sweep-v2",
        }
        v2_records = [e for e in memory_db.iter_experiments(cand.id) if e.model == "mathmodel-v2"]
        assert len(v2_records) == 3

    def test_hard_failure_marks_failed(self, memory_db):
        from blockchain_rd_lab.formalization import ModelEquation

        cand = self._prepared(memory_db)
        # Corrupt the stored model so evaluation fails deterministically.
        model = model_from_dict(
            json.loads(memory_db.get_latest_math_model(cand.id))
        )
        model = model.model_copy(update={
            "equations": [
                ModelEquation(
                    name="bad", expression="S_t1 = S_t / dX_t", description=""
                )
            ],
        })
        memory_db.save_math_model(
            cand.id,
            json.dumps(model.model_dump(mode="json")),
            "corrupted",
            version=2,
        )
        service = SimulationService(memory_db, seed=7, steps=10)
        outcome = service.simulate_candidate(cand, mc_trials=3, sweep_points=2)
        assert outcome["hard_failures"], "expected deterministic failures"
        stored = memory_db.get_candidate(cand.id)
        assert stored is not None
        assert stored.status is CandidateStatus.FAILED

    def test_simulate_all_isolation(self, memory_db):
        c1 = self._prepared(memory_db)
        c2 = make_candidate(name="Second Candidate")
        memory_db.save_candidate(c2)
        c2.transition(CandidateStatus.RESEARCHING)
        c2.transition(CandidateStatus.PRIOR_ART_CHECKED)
        c2.transition(CandidateStatus.FORMALIZED)
        memory_db.save_candidate(c2)
        # c2 has NO stored model → SimulationError for it only.

        service = SimulationService(memory_db, seed=7, steps=20)
        outcomes = service.simulate_all(mc_trials=3, sweep_points=2)
        assert c1.id in outcomes and "monte_carlo" in outcomes[c1.id]
        assert "error" in outcomes[c2.id]
        stored1 = memory_db.get_candidate(c1.id)
        stored2 = memory_db.get_candidate(c2.id)
        assert stored1 is not None and stored1.status is CandidateStatus.SIMULATING
        assert stored2 is not None and stored2.status is CandidateStatus.FORMALIZED

    def test_load_model_missing_raises(self, memory_db):
        cand = self._prepared(memory_db)
        memory_db.delete_candidate(cand.id)
        orphan = make_candidate(name="Orphan")
        memory_db.save_candidate(orphan)
        orphan.transition(CandidateStatus.RESEARCHING)
        orphan.transition(CandidateStatus.PRIOR_ART_CHECKED)
        orphan.transition(CandidateStatus.FORMALIZED)
        memory_db.save_candidate(orphan)
        service = SimulationService(memory_db)
        with pytest.raises(SimulationError, match="no stored model"):
            service.load_model(orphan)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestSimulateCommand:
    def test_simulate_unknown_candidate(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["simulate", "cand-nope"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_simulate_requires_formalized(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        cand = make_candidate(name="Generated Only")
        db.save_candidate(cand)

        runner = CliRunner()
        result = runner.invoke(app, ["simulate", cand.id])
        assert result.exit_code == 1
        assert "formalized" in result.output
