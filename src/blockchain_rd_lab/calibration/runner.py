"""Calibration runner: execute fixtures through the lab's own batteries.

The runner uses the SAME public instrument entry points the pipeline and
the bundle verifier use — ScenarioBattery over MechanismSimulation (§15)
and AttackPatternBattery (§20) — so a calibration result is a statement
about the shipped instruments, not a parallel reimplementation.
"""

from __future__ import annotations

from blockchain_rd_lab.calibration import (
    CalibrationFixture,
    CalibrationReport,
    CheckKind,
    CheckResult,
    Expectation,
    FixtureOutcome,
    RatioDirection,
)
from blockchain_rd_lab.calibration.fixtures import all_fixtures
from blockchain_rd_lab.simulation import MechanismSimulation, ScenarioBattery, SimulationRun
from blockchain_rd_lab.simulation.adversarial import AttackBound, AttackPatternBattery


class CalibrationRunner:
    """Runs fixtures through the §15/§20 batteries and checks expectations."""

    def __init__(self, steps: int = 120, attack_steps: int = 60, seed: int = 7) -> None:
        self.steps = steps
        self.attack_steps = attack_steps
        self.seed = seed

    def run_suite(self, fixtures: list[CalibrationFixture] | None = None) -> CalibrationReport:
        report = CalibrationReport(
            steps=self.steps, attack_steps=self.attack_steps, seed=self.seed
        )
        for fixture in fixtures if fixtures is not None else all_fixtures():
            report.outcomes.append(self.run_fixture(fixture))
        return report

    def run_fixture(self, fixture: CalibrationFixture) -> FixtureOutcome:
        outcome = FixtureOutcome(
            fixture_id=fixture.fixture_id,
            title=fixture.title,
            referent=fixture.referent,
            consensus=fixture.consensus,
            ground_truth=fixture.ground_truth,
        )
        try:
            runs = ScenarioBattery(
                MechanismSimulation(fixture.model), steps=self.steps, seed=self.seed
            ).run()
            bounds = AttackPatternBattery(fixture.model).run_all(steps=self.attack_steps)
        except Exception as exc:
            # An instrument error on a known answer is a finding too —
            # every check fails with the error disclosed (§29).
            for exp in fixture.expectations:
                outcome.checks.append(
                    CheckResult(
                        label=exp.label(), passed=False,
                        measured=f"instrument error: {type(exc).__name__}: {exc}",
                        rationale=exp.rationale,
                    )
                )
            return outcome

        outcome.scenarios_total = len(runs)
        outcome.scenarios_clean = sum(1 for r in runs.values() if not r.failures)
        outcome.degenerate_scenarios = sorted(k for k, r in runs.items() if r.degenerate)
        measurable = [b for b in bounds if not b.vacuous and b.headline is not None]
        if measurable:
            strongest = max(measurable, key=lambda b: b.headline or 0.0)
            outcome.strongest_headline = strongest.headline
            outcome.strongest_attack = (
                f"{strongest.kind.value} = {strongest.headline:g} "
                f"({strongest.headline_metric})"
            )
        outcome.checks = [self._check(e, runs, bounds) for e in fixture.expectations]
        return outcome

    # -- expectation evaluation ------------------------------------------------

    def _check(
        self,
        exp: Expectation,
        runs: dict[str, SimulationRun],
        bounds: list[AttackBound],
    ) -> CheckResult:
        if exp.kind is CheckKind.SCENARIOS_CLEAN:
            clean = sum(1 for r in runs.values() if not r.failures)
            failed = sorted(k for k, r in runs.items() if r.failures)
            return CheckResult(
                label=exp.label(),
                passed=clean == len(runs),
                measured=f"{clean}/{len(runs)} clean"
                + (f"; failures in: {', '.join(failed)}" if failed else ""),
                rationale=exp.rationale,
            )
        if exp.kind is CheckKind.NO_DEGENERATE:
            deg = sorted(k for k, r in runs.items() if r.degenerate)
            return CheckResult(
                label=exp.label(),
                passed=not deg,
                measured=(
                    f"{len(deg)}/{len(runs)} degenerate"
                    + (f": {', '.join(deg)}" if deg else "")
                ),
                rationale=exp.rationale,
            )
        if exp.kind is CheckKind.MAX_ATTACK_HEADLINE:
            measurable = [b for b in bounds if not b.vacuous and b.headline is not None]
            if not measurable:
                return CheckResult(
                    label=exp.label(),
                    passed=True,
                    measured="all patterns vacuous — no measurable attacker edge",
                    rationale=exp.rationale,
                )
            strongest = max(measurable, key=lambda b: b.headline or 0.0)
            headline = strongest.headline or 0.0
            return CheckResult(
                label=exp.label(),
                passed=headline <= exp.threshold,
                measured=f"strongest: {strongest.kind.value} = {headline:g} "
                f"({strongest.headline_metric})",
                rationale=exp.rationale,
            )
        if exp.kind is CheckKind.MIN_PATTERN_EDGE:
            bound = next((b for b in bounds if b.kind is exp.pattern), None)
            if bound is None or bound.vacuous or bound.headline is None:
                return CheckResult(
                    label=exp.label(),
                    passed=False,
                    measured=(
                        "vacuous — the battery produced NO measurement for this "
                        "pattern (instrument blind spot on a known answer)"
                    ),
                    rationale=exp.rationale,
                )
            return CheckResult(
                label=exp.label(),
                passed=bound.headline >= exp.threshold,
                measured=f"{bound.kind.value} = {bound.headline:g} ({bound.headline_metric})",
                rationale=exp.rationale,
            )
        # STATE_RATIO
        assert exp.scenario is not None and exp.symbol is not None
        run = runs.get(exp.scenario.value)
        if run is None:
            return CheckResult(
                label=exp.label(), passed=False,
                measured=f"scenario {exp.scenario.value} not in battery output",
                rationale=exp.rationale,
            )
        path = [float(row[exp.symbol]) for row in run.history if exp.symbol in row]
        if len(path) < 2 or path[0] == 0.0:
            return CheckResult(
                label=exp.label(), passed=False,
                measured=f"no usable {exp.symbol} trajectory in {exp.scenario.value}",
                rationale=exp.rationale,
            )
        ratio = path[-1] / path[0]
        passed = (
            ratio >= exp.threshold
            if exp.direction is RatioDirection.ABOVE
            else ratio <= exp.threshold
        )
        return CheckResult(
            label=exp.label(),
            passed=passed,
            measured=f"{path[-1]:g} / {path[0]:g} = {ratio:g}",
            rationale=exp.rationale,
        )

