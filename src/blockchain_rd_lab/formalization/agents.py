"""Mechanism Designer agent (Phase 3, §13).

Turns a researched candidate into a formal mathematical model. The LLM
proposes; deterministic validators (MathModel integrity checks) decide what
gets stored (§2).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from blockchain_rd_lab.agents.base import BaseAgent, LLMMessage, LLMProvider, ModelTier
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.research import CandidateBrief, EconomistReport, PriorArtReport

DESIGNER_SYSTEM_PROMPT = """You are the Mechanism Designer of an independent blockchain
economic-mechanism research laboratory (§13).

MISSION: turn a researched candidate into a formal mathematical model.

RULES:
  - Every serious candidate must eventually have equations.
  - Define every variable with a symbol and units; every parameter with a
    plausible range and a default inside that range.
  - Write equations in ASCII pseudo-math: one '=' per equation, use
    * / ^ for arithmetic, ln() exp() sqrt() abs() max() min() clip() as
    needed. No prose inside expressions.
  - State assumptions explicitly; mark critical ones.
  - State invariants (things that must always hold) and failure conditions.
  - NEVER assume the first equation is correct (§13). In open_questions,
    list what you did NOT settle: the key coefficient (e.g. alpha),
    smoothing, lag, caps, floors, uncertainty handling, oracle frequency,
    and statistical confidence — as applicable.
  - Do not invent variables mid-equation: every symbol in an equation must
    be a declared variable or parameter symbol.

OUTPUT: only a JSON object matching the MathModel schema:
{
  "candidate_id": "...",            // copy from the brief
  "variables":   [{"name": "...", "symbol": "...", "role": "state|input|output|auxiliary",
                    "units": "...", "description": "..."}],
  "parameters":  [{"name": "...", "symbol": "...", "description": "...",
                   "min_value": 0.0, "max_value": 1.0, "default": 0.5}],
  "equations":   [{"name": "...", "expression": "S_t1 = S_t * (1 + alpha * dP_t / P_t)",
                   "description": "..."}],
  "assumptions": [{"statement": "...", "critical": true}],
  "constraints": [{"statement": "...", "kind": "invariant|constraint|failure_condition"}],
  "open_questions": ["..."],
  "rationale": "why this formalization is faithful to the mechanism"
}"""


class MechanismDesignerAgent(BaseAgent):
    """Formalizes a candidate into equations (§13)."""

    name = "quant"
    role = "Convert ideas into mathematical models and simulations"
    input_schema = CandidateBrief
    output_schema = MathModel
    model_tier = ModelTier.STRONG
    temperature = 0.2

    def __init__(self, provider: LLMProvider, database: Any | None = None) -> None:
        super().__init__(provider, database)

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, CandidateBrief):
            got = type(payload).__name__
            raise TypeError(f"MechanismDesignerAgent expects CandidateBrief, got {got}")
        user = (
            f"CANDIDATE: {payload.name}\n"
            f"category: {payload.category}\n"
            f"description: {payload.description}\n"
            f"core mechanism: {payload.core_mechanism}\n"
        )
        if payload.problem:
            user += f"problem: {payload.problem}\n"
        if payload.oracle_required:
            user += (
                "requires external data (oracle): yes — define the oracle input "
                "variables, their reporting frequency, and revision policy.\n"
            )
        user += (
            "\nBATTERY INPUT CONTRACT (the §15 simulation feeds your model):\n"
            "- Inputs each step are exactly: X_t = anchor LEVEL (~1000, "
            "drifts per scenario) and dX_t = anchor DELTA that step.\n"
            "- State variables seed at 1000.0; equations must tolerate "
            "that scale.\n"
            "- Any other input symbol you declare gets NO battery feed — "
            "it must derive itself from X_t/dX_t or be a parameter/state.\n"
            "- clip() bounds must bracket the values your equations "
            "actually produce at these scales, or the run saturates "
            "(pinned states = degenerate = vacuous §15 evidence; the "
            "battery flags and rejects such models).\n"
            "\nProduce the formal mathematical model as the JSON object described "
            "in the system message. Every symbol used in equations must be declared."
        )
        return [
            LLMMessage(role="system", content=DESIGNER_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user),
        ]


def build_math_model_fixture(
    brief: CandidateBrief,
    beta: float = 0.5,
) -> dict[str, object]:
    """Deterministic offline model for tests and `lab formalize --mock-fixtures`.

    A generic supply-rule formalization parameterized by the brief, so the
    offline path exercises the exact same validation + storage code.
    """
    return {
        "candidate_id": brief.candidate_id,
        "version": 1,
        "variables": [
            {
                "name": "supply",
                "symbol": "S_t",
                "role": "state",
                "units": "tokens",
                "description": "Mechanism-controlled supply at step t.",
            },
            {
                "name": "anchor",
                "symbol": "X_t",
                "role": "input",
                "units": "units_of_anchor",
                "description": "Exogenous anchor quantity reported to the mechanism.",
            },
            {
                "name": "anchor_delta",
                "symbol": "dX_t",
                "role": "input",
                "units": "units_of_anchor",
                "description": "Change in anchor between reports.",
            },
            {
                "name": "supply_next",
                "symbol": "S_t1",
                "role": "output",
                "units": "tokens",
                "description": "Supply after applying the rule.",
            },
            {
                "name": "raw_growth",
                "symbol": "g_raw_t",
                "role": "auxiliary",
                "units": "fraction",
                "description": "Uncapped per-step growth fraction.",
            },
            {
                "name": "capped_growth",
                "symbol": "g_t",
                "role": "auxiliary",
                "units": "fraction",
                "description": "Capped per-step growth fraction actually applied.",
            },
        ],
        "parameters": [
            {
                "name": "coupling",
                "symbol": "alpha",
                "description": "Coupling strength between anchor change and supply.",
                "min_value": 0.0,
                "max_value": 2.0,
                "default": beta,
            },
            {
                "name": "floor",
                "symbol": "f",
                "description": "Lower cap on per-step supply change fraction.",
                "min_value": -0.1,
                "max_value": 0.0,
                "default": -0.05,
            },
            {
                "name": "cap",
                "symbol": "c",
                "description": "Upper cap on per-step supply change fraction.",
                "min_value": 0.0,
                "max_value": 0.1,
                "default": 0.05,
            },
        ],
        "equations": [
            {
                "name": "raw_growth",
                "expression": "g_raw_t = alpha * dX_t / X_t",
                "description": "Uncapped growth fraction implied by the anchor delta.",
            },
            {
                "name": "capped_growth",
                "expression": "g_t = clip(g_raw_t, f, c)",
                "description": "Growth fraction after applying floor and cap (§13).",
            },
            {
                "name": "supply_update",
                "expression": "S_t1 = S_t * (1 + g_t)",
                "description": "Supply rule: scale supply by the capped growth factor.",
            },
        ],
        "assumptions": [
            {
                "statement": "The anchor quantity X_t is reported truthfully and on schedule.",
                "critical": True,
            },
            {
                "statement": "Anchor deltas are small relative to X_t in normal operation.",
                "critical": False,
            },
        ],
        "constraints": [
            {
                "statement": "Supply never decreases by more than 5% in one step.",
                "kind": "invariant",
            },
            {
                "statement": "If oracle reports stall beyond one period, supply freezes.",
                "kind": "failure_condition",
            },
        ],
        "open_questions": [
            "What value of alpha keeps volatility within the cap band (§13)?",
            "Should the rule smooth over a lag window instead of reacting per report?",
            "How are oracle revisions and restatements handled retroactively?",
            "What oracle frequency balances statistical confidence against cost?",
        ],
        "rationale": (
            "Fixture formalization: supply couples to an exogenous anchor with "
            "explicit caps and floors; constants deliberately left open for "
            "Phase 4 sweeps (§13: never assume the first equation is correct)."
        ),
    }


def attach_research_context(
    prior_art: PriorArtReport | None,
    economist: EconomistReport | None,
) -> str:
    """Optional context block appended to the user message (best-effort)."""
    lines: list[str] = []
    if prior_art is not None:
        lines.append(
            "prior-art context: " + prior_art.conclusion[:400]
        )
    if economist is not None:
        lines.append(
            "economist context: " + economist.summary[:400]
        )
    return "\n".join(lines)
