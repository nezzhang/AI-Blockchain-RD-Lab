"""Phase 5 adversarial agents: Game Theory, Security, Oracle, Red Team (§9).

Each agent takes a CandidateBrief (plus the stored math-model context for
the quant-facing review) and returns a Pydantic-validated report. The
prompts encode the §9 missions; the Red Team prompt is explicitly
destructive ("DESTROY THE IDEA") while still requiring evidence labels
(§29). The service — deterministic code — decides confirmations and
rejections, never the prompt (§2, §20).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from blockchain_rd_lab.agents.base import (
    BaseAgent,
    LLMMessage,
    LLMProvider,
    ModelTier,
)
from blockchain_rd_lab.redteam import (
    GameTheoryReport,
    OracleReport,
    RedTeamReport,
    SecurityReport,
)
from blockchain_rd_lab.research import CandidateBrief


def _brief_user_message(brief: CandidateBrief, model_dump: str = "", extra: str = "") -> str:
    parts = [
        f"CANDIDATE: {brief.name}",
        f"category: {brief.category}",
        f"description: {brief.description}",
        f"core mechanism: {brief.core_mechanism}",
    ]
    if brief.oracle_required:
        parts.append("requires external data (oracle): yes")
    if model_dump:
        parts.append(f"formalized model:\n{model_dump}")
    if brief.formal_model:
        # §34 retest: the red team attacks the FORMALIZED design (the
        # latest patched MathModel), not just the prose description.
        parts.append(f"formalized model (attack THIS design):\n{brief.formal_model}")
    if extra:
        parts.append(extra)
    return "\n".join(parts)


GAME_THEORY_SYSTEM_PROMPT = """You are the Game Theory Agent of an independent blockchain
economic-mechanism research laboratory (§9).

MISSION: assume every participant is a rational profit maximizer, and find
where the mechanism breaks.

FIND (at minimum):
  - arbitrage paths
  - manipulation strategies
  - incentive misalignment (who profits from failure?)
  - equilibrium failures (no stable state, or a bad one)
  - bank-run dynamics
  - death-spiral loops (falling anchor -> contraction -> further fall)
  - strategic attacks (commit/reveal games, timing games, holdup)

RULES:
  - Attacks must name the attacker role: whale, validator, oracle_provider,
    governance, arbitrageur, liquidity_provider, attacker.
  - profitable_for_attacker=true ONLY with a reasoned profit path.
  - Label every vector FACT / INFERENCE / HYPOTHESIS (§29) — most attacks
    are HYPOTHESIS unless backed by simulation or precedent.
  - Score game_theory_score 0-10: 10 = robust under rational adversaries;
    low scores mean obvious profitable attacks exist.

OUTPUT: only a JSON object matching the GameTheoryReport schema."""


class GameTheoryAgent(BaseAgent):
    """Finds strategic exploits under rational participants (§9)."""

    name = "game_theory"
    role = "Assume rational profit maximizers; find arbitrage, manipulation, death spirals"
    input_schema = CandidateBrief
    output_schema = GameTheoryReport
    model_tier = ModelTier.STRONG
    temperature = 0.3

    def __init__(self, provider: LLMProvider, database: Any | None = None) -> None:
        super().__init__(provider, database)

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, CandidateBrief):
            got = type(payload).__name__
            raise TypeError(f"GameTheoryAgent expects CandidateBrief, got {got}")
        return [
            LLMMessage(role="system", content=GAME_THEORY_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_brief_user_message(
                    payload,
                    extra="Enumerate concrete attack vectors and score 0-10.",
                ),
            ),
        ]


SECURITY_SYSTEM_PROMPT = """You are the Security Agent of an independent blockchain
economic-mechanism research laboratory (§9).

MISSION: break the mechanism's security assumptions across layers.

INVESTIGATE:
  - smart-contract attack surface (if contracts are implied)
  - economic attacks (fee evasion, mint-path abuse, accounting tricks)
  - oracle attacks (bad data, stale data, selective truth)
  - governance attacks (capture, flash-loan voting, quorum games)
  - validator attacks (censorship, collusion, MEV extraction)
  - censorship and Sybil vectors

RULES:
  - Name the attacker role on every vector.
  - hardest_attack_to_defend must be a single, specific attack.
  - Label evidence FACT / INFERENCE / HYPOTHESIS (§29).
  - Score security_score 0-10: 10 = no plausible unmitigated attack path.

OUTPUT: only a JSON object matching the SecurityReport schema."""


class SecurityAgent(BaseAgent):
    """Investigates cross-layer attack paths (§9)."""

    name = "security"
    role = "Investigate contract, economic, oracle, governance, validator attacks"
    input_schema = CandidateBrief
    output_schema = SecurityReport
    model_tier = ModelTier.STRONG
    temperature = 0.3

    def __init__(self, provider: LLMProvider, database: Any | None = None) -> None:
        super().__init__(provider, database)

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, CandidateBrief):
            got = type(payload).__name__
            raise TypeError(f"SecurityAgent expects CandidateBrief, got {got}")
        return [
            LLMMessage(role="system", content=SECURITY_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_brief_user_message(
                    payload,
                    extra="Enumerate attack vectors across layers; name the hardest one.",
                ),
            ),
        ]


ORACLE_SYSTEM_PROMPT = """You are the Oracle Agent of an independent blockchain
economic-mechanism research laboratory (§9).

MISSION: for mechanisms that depend on real-world data, determine whether
the data pipeline can be trusted.

INVESTIGATE:
  - data sources (who produces the number, under what incentives?)
  - accuracy and error bounds
  - latency and staleness under stress
  - revision policy (do reported values get restated?)
  - manipulation vectors (who can move the reported value, at what cost?)
  - decentralization of reporting
  - oracle provider incentives (do providers profit from lying?)
  - conflicting-data handling

RULES:
  - If the mechanism needs no external data, say so and still assess the
    implicit data dependencies (e.g., "the anchor itself").
  - Label evidence FACT / INFERENCE / HYPOTHESIS (§29).
  - Score oracle_feasibility_score 0-10: 10 = robust, hard-to-manipulate,
    redundant sourcing.

OUTPUT: only a JSON object matching the OracleReport schema."""


class OracleAgent(BaseAgent):
    """Assesses real-world-data feasibility and manipulation (§9)."""

    name = "oracle"
    role = "Investigate data sources, accuracy, latency, revisions, manipulation"
    input_schema = CandidateBrief
    output_schema = OracleReport
    model_tier = ModelTier.STRONG
    temperature = 0.3

    def __init__(self, provider: LLMProvider, database: Any | None = None) -> None:
        super().__init__(provider, database)

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, CandidateBrief):
            got = type(payload).__name__
            raise TypeError(f"OracleAgent expects CandidateBrief, got {got}")
        return [
            LLMMessage(role="system", content=ORACLE_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_brief_user_message(
                    payload,
                    extra="Assess the data pipeline and its manipulation vectors.",
                ),
            ),
        ]


RED_TEAM_SYSTEM_PROMPT = """You are the Red Team Agent of an independent blockchain
economic-mechanism research laboratory (§9).

MISSION: DESTROY THE IDEA. Actively attempt to make this mechanism fail.
Your job is not balance; it is destruction. Balance happens elsewhere.

ASK (all of these, explicitly):
  - How can I manipulate it?
  - How can I arbitrage it?
  - How can a whale exploit it?
  - How can validators exploit it?
  - How can oracle providers exploit it?
  - How can governance exploit it?
  - How can liquidity disappear?
  - How can the system enter a death spiral?
  - Can I create a profitable attack?
  - What happens during a crisis?
  - What happens if the assumptions are wrong?

RULES:
  - verdict is exactly one of: survives | vulnerable | fatal.
    "fatal" means the mechanism cannot work as specified — the attack is
    structural, not incidental.
  - strongest_attack must be the single best destruction attempt, with its
    profit path if profitable_for_attacker.
  - what_would_save_it: the minimal change that would defeat your best
    attack (empty string not allowed; "nothing" is a valid answer).
  - Label evidence FACT / INFERENCE / HYPOTHESIS (§29).
  - You are adversarial, not careless: every attack must still be *possible*.

OUTPUT: only a JSON object matching the RedTeamReport schema."""


class RedTeamAgent(BaseAgent):
    """Attempts to destroy the mechanism (§9)."""

    name = "red_team"
    role = "DESTROY THE IDEA — attempt to make every promising mechanism fail"
    input_schema = CandidateBrief
    output_schema = RedTeamReport
    model_tier = ModelTier.STRONGEST
    temperature = 0.6

    def __init__(self, provider: LLMProvider, database: Any | None = None) -> None:
        super().__init__(provider, database)

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, CandidateBrief):
            got = type(payload).__name__
            raise TypeError(f"RedTeamAgent expects CandidateBrief, got {got}")
        return [
            LLMMessage(role="system", content=RED_TEAM_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_brief_user_message(
                    payload,
                    extra="Attempt destruction. Deliver a verdict.",
                ),
            ),
        ]


# ---------------------------------------------------------------------------
# Offline fixtures (deterministic, same validation path as LLM output)
# ---------------------------------------------------------------------------


def build_redteam_fixture(
    brief: CandidateBrief,
    verdict: str = "vulnerable",
    fatal: bool = False,
) -> dict[str, dict[str, object]]:
    """Deterministic offline adversarial reports for one candidate.

    Returns the raw dicts the four agents would have produced, so the
    mock provider path exercises the exact same validation + storage code.
    """
    v = verdict if verdict in ("survives", "vulnerable", "fatal") else "vulnerable"
    if fatal:
        v = "fatal"

    def vector(name: str, attacker: str, profitable: bool = False) -> dict[str, object]:
        return {
            "vector": name,
            "description": (
                f"Fixture attack for {brief.name}: {attacker} acts when the "
                "mechanism is most dependent on cooperation."
            ),
            "attacker": attacker,
            "profitable_for_attacker": profitable,
            "requires_collusion": False,
            "evidence_level": "HYPOTHESIS",
        }

    return {
        "game_theory": {
            "summary": (
                f"Fixture game-theoretic review of {brief.name}: rational "
                "participants can time exits around anchor revisions."
            ),
            "attack_vectors": [
                vector("exit timing around anchor revisions", "whale"),
                vector("liquidity withdrawal cascade", "liquidity_provider"),
            ],
            "equilibria_notes": (
                "Multiple equilibria exist; the cooperative one is not "
                "dominant under stress."
            ),
            "death_spiral_risk": 4.5,
            "game_theory_score": 5.5,
            "evidence_level": "HYPOTHESIS",
        },
        "security": {
            "summary": (
                f"Fixture security review of {brief.name}: attack surface "
                "spans oracle reporting and parameter updates."
            ),
            "attack_vectors": [
                vector("stale-data exploit", "oracle_provider", profitable=True),
                vector("parameter-capture", "governance"),
            ],
            "hardest_attack_to_defend": (
                "oracle provider reporting selectively during low-liquidity windows"
            ),
            "security_score": 5.0,
            "evidence_level": "HYPOTHESIS",
        },
        "oracle": {
            "summary": (
                f"Fixture oracle review of {brief.name}: the anchor series "
                "must be live, redundant, and manipulation-resistant."
            ),
            "data_source_assessment": (
                "Single-source anchor assumed; redundancy and revision policy "
                "unverified (fixture)."
            ),
            "manipulation_vectors": [
                vector("anchor spike during thin hours", "attacker", profitable=True),
            ],
            "oracle_feasibility_score": 5.0,
            "evidence_level": "HYPOTHESIS",
        },
        "red_team": {
            "verdict": v,
            "strongest_attack": (
                "Coordinate an anchor spike during a low-liquidity window so the "
                "mechanism over-expands exactly when exit is cheapest."
            ),
            "strongest_attack_is_profitable": True,
            "attack_vectors": [
                vector("coordinated anchor manipulation", "attacker", profitable=True),
                vector("bank-run trigger", "whale"),
            ],
            "what_would_save_it": (
                "Time-weighted anchor smoothing plus a circuit breaker on "
                "growth derived from low-confidence reports."
            ),
            "evidence_level": "HYPOTHESIS",
        },
    }


def fixture_redteam_responses(
    briefs: list[CandidateBrief], **kwargs
) -> list[str]:
    """One JSON response per candidate, four reports in agent order."""
    out: list[str] = []
    for brief in briefs:
        reports = build_redteam_fixture(brief, **kwargs)
        for agent_name in ("game_theory", "security", "oracle", "red_team"):
            out.append(json.dumps(reports[agent_name]))
    return out
