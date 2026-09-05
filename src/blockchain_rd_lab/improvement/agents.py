"""Improvement Agent (§3/§34 loop): propose a patched model v(n+1).

The agent reads the adversarial reports and the current MathModel and
proposes a fix. It does NOT decide anything — deterministic code applies
the same §13 integrity checks to the patched model and the §11 machine
controls the status transitions (§2).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from blockchain_rd_lab.agents.base import (
    BaseAgent,
    LLMMessage,
    ModelTier,
)
from blockchain_rd_lab.improvement import ImprovementProposal
from blockchain_rd_lab.research import CandidateBrief

IMPROVER_SYSTEM_PROMPT = """You are the Improvement Agent of an autonomous
blockchain research lab. Your mission is to fix mechanisms that survived
red-team review but were found VULNERABLE (not fatally broken).

You receive:
- the candidate summary,
- the current mathematical model (latest version),
- the adversarial reports that found profitable attacks or weaknesses.

Propose a PATCHED model as version n+1. Rules:
1. Address at least one attack concretely — name the attack and explain
   the fix strategy (circuit breaker, cap, delay, bond, collateral,
   decay, buffer, rule change).
2. Keep the model executable: every symbol used in equations must be
   declared; keep ASCII equations the simulator can evaluate.
3. Preserve §13 discipline: list the design questions you did NOT settle
   in open_questions.
4. Be honest: if the attack cannot be fixed within the model, say so by
   setting fixes_attack=false for it — do not claim a fake fix.

Return ONLY the JSON object described in the system message."""

FIX_STRATEGIES = (
    "bound the correction term with a hard cap and a smoothing delay so a "
    "transient anchor spike cannot over-expand supply within the attack window",
    "require a step-change rate limiter (max S_t1/S_t = 1 + c) so any single "
    "manipulation has bounded effect",
)


class ImprovementAgent(BaseAgent):
    """Proposes patched MathModel v(n+1) after adversarial review."""

    name = "improver"
    role = "Fix red-team findings with patched mechanism models"
    input_schema = CandidateBrief
    output_schema = ImprovementProposal
    model_tier = ModelTier.STRONG
    temperature = 0.2

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, ImprovementInput):
            got = type(payload).__name__
            raise TypeError(f"ImprovementAgent expects ImprovementInput, got {got}")
        user = (
            f"CANDIDATE: {payload.brief.name}\n"
            f"category: {payload.brief.category}\n"
            f"description: {payload.brief.description}\n"
            f"core mechanism: {payload.brief.core_mechanism}\n\n"
            f"CURRENT MODEL (version {payload.current_model.get('version', 1)}):\n"
            f"{json.dumps(payload.current_model, indent=1)}\n\n"
            "ADVERSARIAL FINDINGS (profitable attacks / weaknesses):\n"
        )
        for finding in payload.attack_findings:
            user += f"- [{finding['agent']}] {finding['vector']}\n"
        user += (
            "\nProduce the improvement proposal as the JSON object described "
            "in the system message."
        )
        return [
            LLMMessage(role="system", content=IMPROVER_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user),
        ]


class ImprovementInput(BaseModel):
    """Everything the improvement agent needs: brief + model + findings."""

    model_config = {"frozen": True}

    brief: CandidateBrief
    current_model: dict[str, Any]
    attack_findings: list[dict[str, str]]


def build_improvement_fixture(
    brief: CandidateBrief,
    current_model: dict[str, Any],
    findings: list[dict[str, str]],
) -> dict[str, object]:
    """Deterministic offline improvement for tests and `--mock-fixtures`.

    Patches the model generically: replaces the raw supply-update rule with
    a rate-limited one reacting to an EMA-smoothed anchor, and adds a hard
    single-step cap c_max — the classic fixes for anchor-manipulation
    attacks. Uses the same validation + storage path as the LLM route (§2);
    only the proposal is deterministic.
    """
    from blockchain_rd_lab.formalization import MathModel

    # Work from the stored model so the patch preserves valid structure.
    model = MathModel.model_validate(current_model)
    patched = current_model.copy()

    # 1) new parameter: hard cap on any single-step correction.
    if not any(p["symbol"] == "c_max" for p in patched.get("parameters", [])):
        patched.setdefault("parameters", []).append(
            {
                "name": "hard_step_cap",
                "symbol": "c_max",
                "description": "Maximum allowed single-step supply correction.",
                "min_value": 0.001,
                "max_value": 0.5,
                "default": 0.05,
            }
        )
    # 2) new state variables: smoothed anchor (+ next-step binding).
    symbols = {v["symbol"] for v in patched.get("variables", [])}
    if "X_smooth_t" not in symbols:
        patched.setdefault("variables", []).append(
            {
                "name": "smoothed_anchor",
                "symbol": "X_smooth_t",
                "role": "state",
                "units": "units_of_anchor",
                "description": "EMA-smoothed anchor the rule reacts to.",
            }
        )
    if "X_smooth_t1" not in symbols:
        patched.setdefault("variables", []).append(
            {
                "name": "smoothed_anchor_next",
                "symbol": "X_smooth_t1",
                "role": "output",
                "units": "units_of_anchor",
                "description": "EMA-smoothed anchor after incorporating X_t.",
            }
        )
    # 3) REPLACE the supply-update rule (patch, not append): react only to
    #    the smoothed anchor deviation, bounded by the hard cap.
    patched["equations"] = [
        eq
        for eq in patched.get("equations", [])
        if not eq["expression"].strip().startswith("S_t1")
    ]
    patched["equations"].append(
        {
            "name": "rate_limited_supply_update",
            "expression": "S_t1 = S_t * (1 + clip(alpha * (X_smooth_t - X_t) "
            "/ X_t, -1 * c_max, c_max))",
            "description": "Hardened supply rule: correction is bounded by the "
            "hard cap c_max and reacts to the EMA-smoothed anchor, so a "
            "transient anchor spike cannot over-expand supply within the "
            "attack window.",
        }
    )
    # 4) smoothing equation.
    patched["equations"].append(
        {
            "name": "anchor_smoothing",
            "expression": "X_smooth_t1 = 0.8 * X_smooth_t + 0.2 * X_t",
            "description": "EMA smoothing so transient anchor spikes decay "
            "before affecting the rule.",
        }
    )
    # 5) initial state assumption for the smoother (it needs X_smooth_0).
    #    The simulator seeds unknown state symbols from the anchor series.
    # Bump version + keep §13 honesty.
    patched["version"] = int(model.version) + 1
    oq = list(patched.get("open_questions", []))
    oq.append(
        "Is c_max tight enough against collusive anchor manipulation across "
        "multiple steps (multi-block attack windows)?"
    )
    patched["open_questions"] = oq

    addressed = [
        {
            "agent_name": findings[0]["agent"] if findings else "red_team",
            "vector_description": findings[0]["vector"] if findings else "unspecified",
            "fix_strategy": FIX_STRATEGIES[0],
            "fixes_attack": True,
        }
    ]
    return {
        "summary": "Harden the supply rule with a hard single-step cap c_max "
        "and EMA anchor smoothing so transient anchor manipulation cannot "
        "over-expand supply within the attack window.",
        "addressed_attacks": addressed,
        "model": patched,
    }
