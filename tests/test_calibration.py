"""Calibration-suite tests: the known-answer contract for the instruments.

The suite IS the test — `test_suite_passes` runs every fixture through
the shipped §15/§20 batteries and asserts the instruments meet the
consensus-grounded expectations. The remaining tests pin the harness's
own honesty: the checker must discriminate (negative control), must
disclose instrument errors instead of crashing, and the report must
render and round-trip.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from blockchain_rd_lab.calibration import (
    CalibrationFixture,
    CalibrationReport,
    CheckKind,
    ConsensusClass,
    Expectation,
)
from blockchain_rd_lab.calibration.fixtures import all_fixtures
from blockchain_rd_lab.calibration.runner import CalibrationRunner
from blockchain_rd_lab.cli import app
from blockchain_rd_lab.simulation import ScenarioKind
from blockchain_rd_lab.simulation.adversarial import FLAW_EDGE_THRESHOLD

runner = CliRunner()


@pytest.fixture(scope="module")
def report() -> CalibrationReport:
    return CalibrationRunner().run_suite()


class TestFixtures:
    def test_unique_ids_and_valid_models(self) -> None:
        fixtures = all_fixtures()
        ids = [f.fixture_id for f in fixtures]
        assert len(ids) == len(set(ids))
        for f in fixtures:
            assert f.model.undeclared_symbols() == set()
            declared = f.model.declared_symbols()
            for e in f.expectations:
                if e.kind is CheckKind.STATE_RATIO:
                    assert e.symbol in declared

    def test_both_consensus_classes_present(self) -> None:
        classes = {f.consensus for f in all_fixtures()}
        # a suite with only good news would be marketing, not calibration
        assert ConsensusClass.KNOWN_GOOD in classes
        assert ConsensusClass.KNOWN_FLAWED in classes

    def test_fixture_serializes(self) -> None:
        for f in all_fixtures():
            restored = CalibrationFixture.model_validate_json(f.model_dump_json())
            assert restored.fixture_id == f.fixture_id


class TestSuite:
    def test_suite_passes(self, report: CalibrationReport) -> None:
        """THE calibration: the instruments judge every known answer
        consistently with established consensus."""
        assert report.ok, [
            (o.fixture_id, c.label, c.measured)
            for o in report.outcomes
            for c in o.checks
            if not c.passed
        ]

    def test_known_good_fixtures_not_flagged(self, report: CalibrationReport) -> None:
        for o in report.outcomes:
            if o.consensus is ConsensusClass.KNOWN_GOOD:
                assert o.strongest_headline is None or (
                    o.strongest_headline <= FLAW_EDGE_THRESHOLD
                ), f"{o.fixture_id}: false-positive fatal edge {o.strongest_attack}"

    def test_known_flawed_fixtures_are_detected(self, report: CalibrationReport) -> None:
        by_id = {o.fixture_id: o for o in report.outcomes}
        ratchet = by_id["fixture-vol-keyed-retention-ratchet"]
        assert ratchet.strongest_headline is not None
        assert ratchet.strongest_headline >= FLAW_EDGE_THRESHOLD
        mint_burn = by_id["fixture-reflexive-mint-burn"]
        s_check = next(
            c for c in mint_burn.checks if "bank_run" in c.label and "S_t" in c.label
        )
        assert s_check.passed, s_check.measured


class TestHarnessHonesty:
    def test_negative_control_discriminates(self) -> None:
        """An impossible expectation MUST fail — the checker checks."""
        fixture = next(
            f for f in all_fixtures() if f.fixture_id == "fixture-reflexive-mint-burn"
        )
        impossible = Expectation(
            kind=CheckKind.STATE_RATIO,
            scenario=ScenarioKind.BASE,
            symbol="S_t",
            threshold=1.0e30,
            rationale="NEGATIVE CONTROL: no mechanism grows 1e30x in calm markets",
        )
        broken = fixture.model_copy(
            update={"expectations": [*fixture.expectations, impossible]}
        )
        outcome = CalibrationRunner().run_fixture(broken)
        assert not outcome.passed
        assert any("1e+30" in c.label and not c.passed for c in outcome.checks)

    def test_instrument_error_is_disclosed_not_raised(self) -> None:
        """A model today's interpreter cannot run must produce failed
        checks carrying the error — never a crash, never a pass (§29)."""
        fixture = all_fixtures()[0]
        # model_copy skips validation — exactly how a malformed stored
        # record reaches the runner; a dependency cycle raises at
        # interpreter construction.
        cycled = fixture.model.model_copy(
            update={
                "equations": [
                    fixture.model.equations[0].model_copy(
                        update={"name": "loop_a", "expression": "loop_a = loop_b + 1.0"}
                    ),
                    fixture.model.equations[1].model_copy(
                        update={"name": "loop_b", "expression": "loop_b = loop_a + 1.0"}
                    ),
                ],
                "variables": [
                    *fixture.model.variables,
                    fixture.model.variables[2].model_copy(
                        update={"name": "loop_a", "symbol": "loop_a"}
                    ),
                    fixture.model.variables[2].model_copy(
                        update={"name": "loop_b", "symbol": "loop_b"}
                    ),
                ],
            }
        )
        bad = fixture.model_copy(update={"model": cycled})
        outcome = CalibrationRunner().run_fixture(bad)
        assert not outcome.passed
        assert any("instrument error" in c.measured for c in outcome.checks)


class TestReport:
    def test_markdown_sections(self, report: CalibrationReport) -> None:
        md = report.to_markdown()
        assert "CALIBRATION-PASS" in md
        assert "What this validates" in md
        for o in report.outcomes:
            assert o.title in md
            assert o.referent in md

    def test_json_roundtrip(self, report: CalibrationReport) -> None:
        restored = CalibrationReport.model_validate_json(report.model_dump_json())
        assert restored.ok == report.ok
        assert len(restored.outcomes) == len(report.outcomes)


class TestCli:
    def test_calibrate_command(self, tmp_lab_dir) -> None:
        result = runner.invoke(app, ["calibrate"])
        assert result.exit_code == 0, result.output
        assert "CALIBRATION-PASS" in result.output
        artifacts = tmp_lab_dir / "reports"
        assert (artifacts / "calibration-latest.md").exists()
        data = json.loads((artifacts / "calibration-latest.json").read_text())
        assert len(data["outcomes"]) == len(all_fixtures())

