"""Formalization schemas (Phase 3, §13).

Every serious candidate must eventually have equations. A MathModel is the
LLM's *proposal*; deterministic code validates its structural integrity
(symbol references, equation sanity) before anything is stored (§2).
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VariableRole(enum.StrEnum):
    """What role a variable plays in the mechanism."""

    STATE = "state"          # endogenous, evolves over time
    INPUT = "input"          # exogenous (e.g., oracle-reported)
    OUTPUT = "output"        # mechanism computes/publishes it
    AUXILIARY = "auxiliary"  # helper quantity


class ModelVariable(BaseModel):
    """One variable of the mathematical model."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    symbol: str = Field(min_length=1, max_length=16)
    role: VariableRole = VariableRole.STATE
    units: str = Field(default="dimensionless", max_length=64)
    description: str = Field(min_length=3, max_length=500)


class ModelParameter(BaseModel):
    """One tunable parameter with its plausible range."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    symbol: str = Field(min_length=1, max_length=16)
    description: str = Field(min_length=3, max_length=500)
    min_value: float = Field(ge=-1e12, le=1e12)
    max_value: float = Field(ge=-1e12, le=1e12)
    default: float = Field(ge=-1e12, le=1e12)

    @model_validator(mode="after")
    def _range_ok(self) -> ModelParameter:
        if self.min_value > self.max_value:
            raise ValueError(f"parameter {self.name}: min_value > max_value")
        if not (self.min_value <= self.default <= self.max_value):
            raise ValueError(
                f"parameter {self.name}: default outside [{self.min_value}, {self.max_value}]"
            )
        return self


class ModelEquation(BaseModel):
    """One equation of the model, in restricted math-pseudo syntax.

    Deterministically checkable: ASCII only, one '=' (no '==', '<=', etc.),
    balanced parentheses, no banned constructs (§2).
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=80)
    expression: str = Field(min_length=3, max_length=500)
    description: str = Field(default="", max_length=500)

    @field_validator("expression")
    @classmethod
    def _ascii(cls, v: str) -> str:
        try:
            v.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(
                "expression must be ASCII (use * / ^ not × ÷)"  # noqa: RUF001 -- banned chars
            ) from exc
        return v.strip()

    @field_validator("expression")
    @classmethod
    def _single_assignment(cls, v: str) -> str:
        if v.count("=") != 1:
            raise ValueError("expression must contain exactly one '=' (assignment)")
        for banned in ("==", "<=", ">=", "!=", "+=", "-="):
            if banned in v:
                raise ValueError(f"expression must not contain '{banned}'")
        return v

    @field_validator("expression")
    @classmethod
    def _balanced_parens(cls, v: str) -> str:
        depth = 0
        for ch in v:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    raise ValueError("unbalanced ')' in expression")
        if depth != 0:
            raise ValueError("unbalanced '(' in expression")
        return v


class ModelAssumption(BaseModel):
    """One explicit assumption; simulation may later falsify it."""

    model_config = ConfigDict(frozen=True)

    statement: str = Field(min_length=10, max_length=600)
    critical: bool = False


class ModelConstraint(BaseModel):
    """An invariant or constraint the mechanism must respect."""

    model_config = ConfigDict(frozen=True)

    statement: str = Field(min_length=5, max_length=600)
    kind: str = Field(default="invariant", pattern="^(invariant|constraint|failure_condition)$")


class MathModel(BaseModel):
    """The Mechanism Designer's proposed formal model (§13).

    §13 discipline: never assume the first equation is correct — the model
    must list open design questions (alpha, smoothing, lag, caps, floors,
    uncertainty, oracle frequency, statistical confidence) it did NOT settle.
    """

    model_config = ConfigDict(validate_assignment=True)

    candidate_id: str = Field(min_length=1, max_length=64)
    version: int = Field(default=1, ge=1)
    variables: list[ModelVariable] = Field(min_length=1)
    parameters: list[ModelParameter] = Field(default_factory=list)
    equations: list[ModelEquation] = Field(min_length=1)
    assumptions: list[ModelAssumption] = Field(default_factory=list)
    constraints: list[ModelConstraint] = Field(default_factory=list)
    open_questions: list[str] = Field(min_length=1, max_length=30)
    rationale: str = Field(min_length=10, max_length=4000)

    # -- deterministic integrity checks (§2) --------------------------------

    def referenced_symbols(self) -> set[str]:
        """All bare identifier tokens used across equations (both sides)."""
        import re

        tokens: set[str] = set()
        for eq in self.equations:
            lhs, rhs = eq.expression.split("=", 1)
            for side in (lhs, rhs):
                for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", side):
                    if tok in _MATH_FUNCTION_WHITELIST or tok in _MATH_CONSTANTS:
                        continue
                    tokens.add(tok)
        return tokens

    def declared_symbols(self) -> set[str]:
        out = {v.symbol for v in self.variables}
        out |= {p.symbol for p in self.parameters}
        return out

    def undeclared_symbols(self) -> set[str]:
        """Symbols used in equations but never declared (code smells: typos)."""
        return self.referenced_symbols() - self.declared_symbols()

    def unused_symbols(self) -> set[str]:
        return self.declared_symbols() - self.referenced_symbols()

    @model_validator(mode="after")
    def _integrity(self) -> MathModel:
        undeclared = self.undeclared_symbols()
        if undeclared:
            raise ValueError(
                "equations reference undeclared symbols: " + ", ".join(sorted(undeclared))
            )
        if not self.open_questions:
            raise ValueError("§13: the model must list open design questions")
        return self


_MATH_FUNCTION_WHITELIST = frozenset(
    {"log", "ln", "exp", "sqrt", "abs", "max", "min", "sum", "mean", "std", "clip"}
)
_MATH_CONSTANTS = frozenset({"e", "pi"})


class FormalizationResult(BaseModel):
    """Outcome of formalizing one candidate."""

    model_config = ConfigDict(validate_assignment=True)

    candidate_id: str
    model: MathModel | None = None
    error: str = ""
    formalized: bool = False


class FormalizationSummary(BaseModel):
    """Aggregated outcome of a formalization run."""

    model_config = ConfigDict(validate_assignment=True)

    attempted: int = 0
    formalized: int = 0
    failed: int = 0
    model_versions: dict[str, int] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


def model_to_dict(model: MathModel) -> dict[str, Any]:
    """Canonical JSON-serializable form for storage."""
    return model.model_dump(mode="json")


def model_from_dict(data: dict[str, Any]) -> MathModel:
    return MathModel.model_validate(data)
