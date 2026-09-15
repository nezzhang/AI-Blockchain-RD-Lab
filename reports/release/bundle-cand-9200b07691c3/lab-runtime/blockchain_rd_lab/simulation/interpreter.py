"""Safe deterministic interpreter for MathModel equations (§2, §13).

The LLM proposes equations; THIS code executes them. The interpreter is
deliberately restricted:

- Only ASCII arithmetic (+ - * / ** ^), comparison-free assignments,
  whitelisted functions (ln, exp, sqrt, abs, max, min, sum, mean, std,
  clip), and constants (e, pi).
- ^ is normalized to ** (power), never XOR — these are economic models.
- No imports, no names, no attributes, no lambdas, no comprehensions.
- Undeclared symbols are rejected at validation time (MathModel); the
  interpreter double-checks before every run.
- Division by zero and domain errors raise SimulationError — deterministic
  failure, never NaN creep (§15: never only show favorable scenarios).
"""

from __future__ import annotations

import ast
import math
from collections.abc import Callable
from typing import Any

from blockchain_rd_lab.formalization import _MATH_CONSTANTS as _SCHEMA_CONSTANTS

# §13 accepts the named math constants 'e' and 'pi' as bare identifiers
# (formalization._MATH_CONSTANTS) — the interpreter must accept the same
# language or a schema-valid model dies at execution ("symbol 'e' used but
# not declared", the 2026-09-14 audit F3). One source of truth: import
# the canonical set — never redefine it here (r34 pre-audit sweep: the
# r33 fix's comment SAID "import the canonical set" while the code below
# redefined it locally; a schema-side addition would have reopened F3's
# exact drift).
from blockchain_rd_lab.formalization import MathModel

# Values for the canonical set. A module-load parity check guards the
# drift: a schema constant without a value here fails at import, never
# a model at execution. A test pins the parity too.
_CONSTANTS: dict[str, float] = {
    "e": math.e,
    "pi": math.pi,
}

if set(_CONSTANTS) != set(_SCHEMA_CONSTANTS):
    raise ImportError(  # pragma: no cover — guards against silent drift
        "interpreter constant set drifted from the §13 schema set: "
        f"{set(_SCHEMA_CONSTANTS) ^ set(_CONSTANTS)}"
    )


class SimulationError(Exception):
    """Deterministic simulation failure (bad model, bad parameters)."""


def _safe_div(a: Any, b: Any) -> float:
    b = float(b)
    if b == 0.0:
        raise SimulationError("division by zero in equation")
    return float(a) / b


def _safe_pow(a: Any, b: Any) -> float:
    try:
        return float(a) ** float(b)
    except (OverflowError, ValueError) as exc:
        raise SimulationError(f"power overflow/domain: {a}^{b}") from exc


_BIN_OPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: _safe_div,
    ast.Pow: _safe_pow,
}


def _fn_ln(x: float) -> float:
    if x <= 0:
        raise SimulationError("ln of non-positive value")
    return math.log(x)


def _fn_sqrt(x: float) -> float:
    if x < 0:
        raise SimulationError("sqrt of negative value")
    return math.sqrt(x)


def _fn_mean(xs: list[float]) -> float:
    if not xs:
        raise SimulationError("mean of empty sequence")
    return sum(xs) / len(xs)


def _fn_std(xs: list[float]) -> float:
    if not xs:
        raise SimulationError("std of empty sequence")
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "ln": _fn_ln,
    "log": _fn_ln,  # log == natural log in this lab
    "exp": math.exp,
    "sqrt": _fn_sqrt,
    "abs": abs,
    "max": max,
    "min": min,
    "sum": sum,
    "mean": _fn_mean,
    "std": _fn_std,
    "clip": lambda x, lo, hi: min(max(x, lo), hi),
}


class EquationInterpreter:
    """Compiles and evaluates MathModel equations against a symbol table."""

    def __init__(self, model: MathModel) -> None:
        self.model = model
        self.declared = model.declared_symbols()
        # Equations are assignments: "LHS = RHS". Compile the RHS only and
        # bind the result to the LHS symbol.
        self._compiled: dict[str, ast.Expression] = {}
        self.lhs_symbols: dict[str, str] = {}
        for eq in model.equations:
            expr = eq.expression
            if expr.count("=") != 1:
                raise SimulationError(
                    f"equation {eq.name!r}: expected exactly one '=' in {expr!r}"
                )
            lhs, rhs = (part.strip() for part in expr.split("=", 1))
            if not lhs or not rhs:
                raise SimulationError(f"equation {eq.name!r}: empty side in {expr!r}")
            rhs_py = rhs.replace("^", "**")
            try:
                tree = ast.parse(rhs_py, mode="eval")
            except SyntaxError as exc:
                raise SimulationError(
                    f"equation {eq.name!r}: cannot parse {rhs_py!r}: {exc}"
                ) from exc
            self._check_tree(tree)
            self._compiled[eq.name] = tree
            self.lhs_symbols[eq.name] = lhs

        # §14: evaluate in DEPENDENCY order, not declaration order —
        # LLM-authored models may declare equations in any order; the
        # interpreter resolves the dependency graph deterministically
        # (stable: declaration order preserved among independents) and
        # rejects cycles at compile time, not step 0.
        self._order: list[str] = self._topological_order()

    def _equation_dependencies(self, eq_name: str) -> set[str]:
        """Symbols an equation's RHS reads that other equations compute."""
        computed = set(self.lhs_symbols.values())
        deps: set[str] = set()
        for node in ast.walk(self._compiled[eq_name]):
            if isinstance(node, ast.Name) and node.id in computed:
                deps.add(node.id)
        return deps

    def _topological_order(self) -> list[str]:
        """Stable topological sort of equations by data dependency.

        Raises SimulationError on a dependency cycle (deterministic
        compile-time failure, clearer than a step-0 runtime miss).
        """
        names = [eq.name for eq in self.model.equations]
        deps = {n: self._equation_dependencies(n) for n in names}
        # Map LHS -> equation name (multiple writers to one LHS keep
        # declaration order among themselves; the LAST writer wins in
        # evaluate, matching prior declared-order semantics).
        writer: dict[str, list[str]] = {}
        for n in names:
            writer.setdefault(self.lhs_symbols[n], []).append(n)
        emitted: list[str] = []
        done: set[str] = set()
        pending = list(names)
        while pending:
            progressed = False
            for n in list(pending):
                if all(
                    d not in writer or all(w in done for w in writer[d])
                    for d in deps[n]
                ):
                    emitted.append(n)
                    done.add(n)
                    pending.remove(n)
                    progressed = True
            if not progressed:
                stuck = ", ".join(sorted(pending))
                raise SimulationError(
                    f"dependency cycle among equations: {stuck} — equations "
                    "cannot reference each other's outputs circularly"
                )
        return emitted

    def _check_tree(self, tree: ast.AST) -> None:
        """Whitelist AST nodes and operators; reject everything else."""
        allowed = (
            ast.Expression,
            ast.Constant,
            ast.Name,
            ast.BinOp,
            ast.UnaryOp,
            ast.Call,
            ast.Load,
            ast.operator,
            ast.unaryop,
        )
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                raise SimulationError(
                    f"forbidden construct {type(node).__name__} in equation"
                )
            if isinstance(node, ast.BinOp) and type(node.op) not in _BIN_OPS:
                raise SimulationError(
                    f"forbidden binary operator {type(node.op).__name__}"
                )
            if isinstance(node, ast.UnaryOp) and not isinstance(node.op, ast.USub):
                raise SimulationError(
                    f"forbidden unary operator {type(node.op).__name__}"
                )
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    raise SimulationError("non-name function call in equation")
                fname = node.func.id
                if fname not in _FUNCTIONS:
                    raise SimulationError(f"function {fname!r} is not whitelisted")
            if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id not in self.declared
                and node.id not in _FUNCTIONS
                and node.id not in _CONSTANTS
            ):
                raise SimulationError(
                    f"symbol {node.id!r} used but not declared"
                )

    def evaluate(self, symbols: dict[str, float | list[float]]) -> dict[str, float]:
        """Evaluate equations in dependency order; returns computed values.

        Same LHS-multiple-writer semantics as before (later equations in
        the ORIGINAL declaration order overwrite earlier ones), so
        correctly-ordered models behave byte-identically.
        """
        env: dict[str, float | list[float]] = dict(symbols)
        results: dict[str, float] = {}
        for name in self._order:
            tree = self._compiled[name]
            value = self._eval_node(tree.body, env)
            lhs = self.lhs_symbols[name]
            env[lhs] = value
            results[lhs] = value
        return results

    def _eval_node(self, node: ast.AST, env: dict[str, float | list[float]]) -> float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return float(node.value)
            raise SimulationError(f"non-numeric constant {node.value!r}")
        if isinstance(node, ast.Name):
            # Named math constants (audit F3): resolve before env lookup —
            # they are language, not state, so they never shadow and are
            # never shadowed by a step's symbols (a model that DECLARES a
            # variable named 'e' still validates: its own symbol wins in
            # env, per the check order below).
            if node.id in _CONSTANTS and node.id not in env:
                return _CONSTANTS[node.id]
            if node.id not in env:
                raise SimulationError(f"symbol {node.id!r} has no value in this step")
            return float(env[node.id])  # type: ignore[arg-type]
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -self._eval_node(node.operand, env)
            raise SimulationError("unsupported unary operator")
        if isinstance(node, ast.BinOp):
            op = _BIN_OPS.get(type(node.op))
            if op is None:
                raise SimulationError(f"unsupported binary operator {type(node.op).__name__}")
            return float(op(self._eval_node(node.left, env), self._eval_node(node.right, env)))
        if isinstance(node, ast.Call):
            fname = node.func.id  # type: ignore[attr-defined]
            fn = _FUNCTIONS[fname]
            args = [self._eval_node(a, env) for a in node.args]
            try:
                return float(fn(*args))
            except SimulationError:
                raise
            except Exception as exc:
                raise SimulationError(f"function {fname}({args}) failed: {exc}") from exc
        raise SimulationError(f"cannot evaluate node {type(node).__name__}")
