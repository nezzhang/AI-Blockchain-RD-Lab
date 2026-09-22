"""Calibration suite: known-answer validation of the lab's instruments.

The lab's scores are only meaningful if its deterministic instruments
(§14 interpreter, §15 scenario battery, §20 attack-pattern battery)
behave correctly on mechanisms whose properties are ALREADY KNOWN from
established consensus. This package encodes such mechanisms as ordinary
MathModels ("fixtures"), runs them through the SAME batteries real
candidates face, and checks the instrument output against the known
ground truth:

- KNOWN_GOOD fixtures (negative controls): the batteries must NOT
  report a fatal attacker edge. A fatal headline here is a false
  positive — an instrument finding, reported, never hidden (§29).
- KNOWN_FLAWED fixtures (positive controls): the batteries MUST surface
  the known failure mode. A miss here means the instrument is blind to
  a flaw class the real world has already paid for.

Honesty protocol (§2, §29): expectations declare what ESTABLISHED
CONSENSUS predicts the instrument should find, tagged FACT (directly
documented property of the referent) or INFERENCE (encoding-level
expectation). When instrument output disagrees with consensus, the
check FAILS and the report says so — a failing calibration is a finding
about the instrument, not a defect to be tuned away.

Scope: this suite calibrates the DETERMINISTIC instruments only. The
LLM-judged scoring dimensions need blinded fixtures (the judge must not
know it is scoring EIP-1559); that is a separate stage.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.simulation import ScenarioKind
from blockchain_rd_lab.simulation.adversarial import AttackPattern


class ConsensusClass(enum.StrEnum):
    """What established knowledge says about the fixture's referent."""

    KNOWN_GOOD = "known_good"
    KNOWN_FLAWED = "known_flawed"


class CheckKind(enum.StrEnum):
    """Deterministic expectation types the runner can evaluate."""

    SCENARIOS_CLEAN = "scenarios_clean"  # no hard failures in any §15 run
    NO_DEGENERATE = "no_degenerate"  # no §15 run flagged degenerate
    MAX_ATTACK_HEADLINE = "max_attack_headline"  # strongest §20 edge <= threshold
    MIN_PATTERN_EDGE = "min_pattern_edge"  # named §20 pattern edge >= threshold
    STATE_RATIO = "state_ratio"  # final/first of a state under a §15 scenario


class RatioDirection(enum.StrEnum):
    ABOVE = "above"
    BELOW = "below"


class Expectation(BaseModel):
    """One consensus-grounded, deterministically checkable expectation.

    `rationale` must cite the ground truth and tag it FACT or INFERENCE
    (§29 research-integrity discipline applies to calibration too).
    """

    model_config = ConfigDict(frozen=True)

    kind: CheckKind
    # MIN_PATTERN_EDGE only:
    pattern: AttackPattern | None = None
    # STATE_RATIO only:
    scenario: ScenarioKind | None = None
    symbol: str | None = None
    direction: RatioDirection = RatioDirection.ABOVE
    # MAX_ATTACK_HEADLINE / MIN_PATTERN_EDGE / STATE_RATIO:
    threshold: float = 0.0
    rationale: str = Field(min_length=10, max_length=1000)

    @model_validator(mode="after")
    def _params_present(self) -> Expectation:
        if self.kind is CheckKind.MIN_PATTERN_EDGE:
            if self.pattern is None:
                raise ValueError("min_pattern_edge requires a pattern")
            if self.threshold <= 0:
                raise ValueError("min_pattern_edge requires threshold > 0")
        if self.kind is CheckKind.MAX_ATTACK_HEADLINE and self.threshold <= 0:
            raise ValueError("max_attack_headline requires threshold > 0")
        if self.kind is CheckKind.STATE_RATIO:
            if self.scenario is None or self.symbol is None:
                raise ValueError("state_ratio requires scenario and symbol")
            if self.threshold <= 0:
                raise ValueError("state_ratio requires threshold > 0")
        return self

    def label(self) -> str:
        """Short human-readable description for reports."""
        if self.kind is CheckKind.SCENARIOS_CLEAN:
            return "§15 battery: no hard failures"
        if self.kind is CheckKind.NO_DEGENERATE:
            return "§15 battery: no degenerate runs"
        if self.kind is CheckKind.MAX_ATTACK_HEADLINE:
            return f"§20 strongest attack edge ≤ {self.threshold:g}"
        if self.kind is CheckKind.MIN_PATTERN_EDGE:
            assert self.pattern is not None
            return f"§20 {self.pattern.value} edge ≥ {self.threshold:g}"
        assert self.scenario is not None and self.symbol is not None
        op = "≥" if self.direction is RatioDirection.ABOVE else "≤"
        return f"§15 {self.scenario.value}: {self.symbol} final/initial {op} {self.threshold:g}"


class CalibrationFixture(BaseModel):
    """A known mechanism encoded as a MathModel, plus what the lab's
    instruments MUST report about it if they are working."""

    model_config = ConfigDict(frozen=True)

    fixture_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    referent: str = Field(min_length=1, max_length=300)
    consensus: ConsensusClass
    ground_truth: str = Field(min_length=10, max_length=2000)
    model: MathModel
    expectations: list[Expectation] = Field(min_length=1)


class CheckResult(BaseModel):
    """Outcome of evaluating one expectation against measured runs."""

    model_config = ConfigDict(frozen=True)

    label: str
    passed: bool
    measured: str
    rationale: str


class FixtureOutcome(BaseModel):
    """Everything the instruments measured about one fixture, plus the
    pass/fail of each consensus-grounded expectation."""

    model_config = ConfigDict(validate_assignment=True)

    fixture_id: str
    title: str
    referent: str
    consensus: ConsensusClass
    ground_truth: str
    scenarios_clean: int = 0
    scenarios_total: int = 0
    degenerate_scenarios: list[str] = Field(default_factory=list)
    strongest_attack: str = "none measured"
    strongest_headline: float | None = None
    checks: list[CheckResult] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


class CalibrationReport(BaseModel):
    """The full suite result. `ok` is the publication-grade signal:
    every consensus-grounded expectation met by the instruments."""

    model_config = ConfigDict(validate_assignment=True)

    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    steps: int = 120
    attack_steps: int = 60
    seed: int = 7
    outcomes: list[FixtureOutcome] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.outcomes) and all(o.passed for o in self.outcomes)

    @property
    def passed(self) -> int:
        return sum(1 for o in self.outcomes if o.passed)

    def to_markdown(self) -> str:
        lines = [
            "# Calibration Report — known-answer validation of the lab instruments",
            "",
            f"Generated: {self.generated_at} · §15 battery steps={self.steps} · "
            f"§20 attack steps={self.attack_steps} · seed={self.seed}",
            "",
            "Known mechanisms with established-consensus properties are run "
            "through the SAME deterministic batteries real candidates face "
            "(§15 scenario battery, §20 attack-pattern battery). The "
            "instruments' output is checked against the known ground truth. "
            "A failed check is a finding ABOUT THE INSTRUMENT — reported, "
            "never hidden (§29).",
            "",
            "**Scope:** this suite calibrates the deterministic instruments "
            "only. LLM-judged scoring dimensions require blinded fixtures "
            "(the judge must not know it is scoring a famous mechanism) — a "
            "separate stage.",
            "",
            f"**OVERALL: {'CALIBRATION-PASS' if self.ok else 'CALIBRATION-FAIL'}** "
            f"— {self.passed}/{len(self.outcomes)} fixtures meet every "
            "consensus-grounded expectation.",
            "",
            "| Fixture | Referent | Consensus | §15 clean | Degenerate | "
            "Strongest §20 edge | Checks |",
            "|---|---|---|---|---|---|---|",
        ]
        for o in self.outcomes:
            lines.append(
                f"| {o.title} | {o.referent} | {o.consensus.value} | "
                f"{o.scenarios_clean}/{o.scenarios_total} | "
                f"{len(o.degenerate_scenarios)} | {o.strongest_attack} | "
                f"{'✅ all pass' if o.passed else '❌ FAIL'} |"
            )
        for o in self.outcomes:
            lines += [
                "",
                f"## {o.title}",
                "",
                f"- **Referent:** {o.referent}",
                f"- **Consensus class:** {o.consensus.value}",
                f"- **Ground truth:** {o.ground_truth}",
                f"- **§15 battery:** {o.scenarios_clean}/{o.scenarios_total} clean"
                + (
                    f"; degenerate: {', '.join(o.degenerate_scenarios)}"
                    if o.degenerate_scenarios
                    else ""
                ),
                f"- **§20 strongest edge:** {o.strongest_attack}",
                "",
                "| Check | Result | Measured | Ground truth |",
                "|---|---|---|---|",
            ]
            for c in o.checks:
                lines.append(
                    f"| {c.label} | {'✅' if c.passed else '❌'} | "
                    f"{c.measured} | {c.rationale} |"
                )
        lines += [
            "",
            "## What this validates — and what it does not",
            "",
            "- PASS means: on these known answers, the interpreter, §15 "
            "battery, and §20 battery produce output consistent with "
            "established consensus. It does NOT prove the instruments "
            "catch every flaw class — only the classes these fixtures "
            "exercise.",
            "- The fixtures are *encodings* of the referents' core "
            "dynamics in the lab's linear-recurrence DSL, not full "
            "implementations. Encoding fidelity is stated per fixture as "
            "INFERENCE where applicable.",
            "- A FAIL marks an instrument blind spot or over-fire, with "
            "the measurement disclosed — the calibration suite's primary "
            "product is exactly these findings.",
            "",
        ]
        return "\n".join(lines)

