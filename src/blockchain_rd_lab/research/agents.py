"""Phase 2 research agents: Prior-Art, Economist, Market (§9).

Each agent takes a CandidateBrief and returns a Pydantic-validated
structured report. Prompts encode §12 (novelty language), §29 (evidence
levels, preferred sources), and the specific §9 mission per agent.
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
from blockchain_rd_lab.research import (
    CandidateBrief,
    EconomistReport,
    MarketReport,
    PriorArtReport,
)
from blockchain_rd_lab.schemas import (
    FORBIDDEN_NOVELTY_CLAIM,
    REQUIRED_NOVELTY_CLAIM,
)


def _brief_user_message(brief: CandidateBrief, extra: str = "") -> str:
    parts = [
        f"CANDIDATE: {brief.name}",
        f"category: {brief.category}",
        f"description: {brief.description}",
        f"core mechanism: {brief.core_mechanism}",
    ]
    if brief.problem:
        parts.append(f"problem: {brief.problem}")
    if brief.oracle_required:
        parts.append("requires external data (oracle): yes")
    if extra:
        parts.append(extra)
    return "\n".join(parts)


PRIOR_ART_SYSTEM_PROMPT = f"""You are the Prior-Art Agent of an independent blockchain
economic-mechanism research laboratory (§12).

MISSION: determine whether a candidate mechanism already exists in prior art.

NOVELTY CLASSES (assign exactly one):
  A = clearly existing (the mechanism is already deployed or published as-is)
  B = very similar existing mechanism (minor variations exist)
  C = adjacent mechanism (same family, materially different core rule)
  D = appears substantially novel (no substantially similar implementation identified)
  E = insufficient evidence (cannot decide)

LANGUAGE DISCIPLINE (absolute):
  NEVER write: "{FORBIDDEN_NOVELTY_CLAIM}"
  If class D, the conclusion MUST state: "{REQUIRED_NOVELTY_CLAIM}"
  Novelty is always relative to *the sources you actually consulted*.

METHOD:
  - List the specific search queries that should be run (queries you would run).
  - List concrete similar mechanisms with names and URLs (best-effort; mark
    uncertain items clearly in findings).
  - Prefer: academic papers, official protocol documentation, official
    repositories, government datasets, international organizations,
    established research institutions (§29).
  - Label every finding as one of FACT / INFERENCE / HYPOTHESIS in the
    findings text where applicable.

OUTPUT: only a JSON object matching the PriorArtReport schema. No prose
outside the JSON."""


class PriorArtAgent(BaseAgent):
    """Classifies candidate novelty against prior art (§12)."""

    name = "prior_art"
    role = "Determine whether a candidate mechanism already exists in prior art"
    input_schema = CandidateBrief
    output_schema = PriorArtReport
    model_tier = ModelTier.STRONG
    temperature = 0.3

    def __init__(self, provider: LLMProvider, database: Any | None = None) -> None:
        super().__init__(provider, database)

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, CandidateBrief):
            got = type(payload).__name__
            raise TypeError(f"PriorArtAgent expects CandidateBrief, got {got}")
        return [
            LLMMessage(role="system", content=PRIOR_ART_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_brief_user_message(
                    payload,
                    extra=(
                        "Assign the novelty class, list similar mechanisms, "
                        "queries, sources, findings, and a conclusion."
                    ),
                ),
            ),
        ]


ECONOMIST_SYSTEM_PROMPT = """You are the Economist Agent of an independent blockchain
economic-mechanism research laboratory (§9).

MISSION: analyze the candidate as a skeptical monetary economist.

ANALYZE:
  - monetary policy implications (expansion/contraction rules)
  - inflation and deflation dynamics
  - incentive compatibility of participants
  - liquidity under stress
  - monetary equilibrium and stability
  - reflexivity (price → behavior → price loops)
  - capital flows in and out of the mechanism

RULES:
  - Assume participants are self-interested; incentives beat intentions.
  - Distinguish FACT (cited), INFERENCE (reasoned), HYPOTHESIS (speculative)
    in each concern's evidence_level (§29).
  - Mark a concern fatal=true ONLY if it makes the mechanism economically
    unworkable as specified (e.g., guaranteed death spiral, value collapses
    to zero without external subsidy).
  - Score economic_coherence 0-10: internal consistency of the monetary model.

OUTPUT: only a JSON object matching the EconomistReport schema."""


class EconomistAgent(BaseAgent):
    """Analyzes monetary/incentive properties (§9)."""

    name = "economist"
    role = "Analyze monetary policy, incentives, liquidity, stability, reflexivity"
    input_schema = CandidateBrief
    output_schema = EconomistReport
    model_tier = ModelTier.STRONG
    temperature = 0.4

    def __init__(self, provider: LLMProvider, database: Any | None = None) -> None:
        super().__init__(provider, database)

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, CandidateBrief):
            got = type(payload).__name__
            raise TypeError(f"EconomistAgent expects CandidateBrief, got {got}")
        return [
            LLMMessage(role="system", content=ECONOMIST_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_brief_user_message(
                    payload,
                    extra="Analyze as a skeptical monetary economist and score coherence 0-10.",
                ),
            ),
        ]


MARKET_SYSTEM_PROMPT = """You are the Market Agent of an independent blockchain
economic-mechanism research laboratory (§9).

MISSION: determine whether the candidate solves a real problem for a real
customer — or is a solution in search of a problem.

ANALYZE:
  - the actual customer (who specifically transacts/pays?)
  - the actual problem (what measurable pain does it remove?)
  - existing alternatives (status quo and competitors, including non-crypto)
  - market size in honest, order-of-magnitude terms
  - adoption barriers (technical, regulatory, behavioral, liquidity)
  - network effects (does value compound with adoption?)

RULES:
  - "DeFi users" or "crypto enthusiasts" are NOT a customer unless the
    mechanism serves them specifically.
  - Prefer specific, verifiable claims; label the overall report with a
    single dominant evidence_level (§29).
  - Score market_demand 0-10: only strong, specific, willing-to-pay demand
    scores above 6.

OUTPUT: only a JSON object matching the MarketReport schema."""


class MarketAgent(BaseAgent):
    """Analyzes real-world demand and customers (§9)."""

    name = "market"
    role = "Analyze customer, problem, alternatives, market size, adoption barriers"
    input_schema = CandidateBrief
    output_schema = MarketReport
    model_tier = ModelTier.STRONG
    temperature = 0.4

    def __init__(self, provider: LLMProvider, database: Any | None = None) -> None:
        super().__init__(provider, database)

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, CandidateBrief):
            got = type(payload).__name__
            raise TypeError(f"MarketAgent expects CandidateBrief, got {got}")
        return [
            LLMMessage(role="system", content=MARKET_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_brief_user_message(
                    payload,
                    extra=(
                        "Identify the real customer and problem; list honest "
                        "alternatives and adoption barriers; score demand 0-10."
                    ),
                ),
            ),
        ]


def build_research_report_fixture(
    brief: CandidateBrief,
    novelty_class: str = "E",
    coherence: float = 5.0,
    demand: float = 5.0,
    fatal: bool = False,
) -> dict[str, dict[str, object]]:
    """Deterministic offline report generator (tests + `--mock-fixtures`).

    Returns the raw dict an LLM would have produced, so the mock provider
    path exercises the exact same validation + persistence code.
    """
    from blockchain_rd_lab.schemas import NoveltyClass

    # Accept shorthand ("A".."E") or full value ("insufficient_evidence", ...).
    try:
        cls = NoveltyClass(novelty_class)
    except ValueError:
        cls = NoveltyClass[novelty_class.upper()]
    conclusion = {
        "A": "A clearly existing mechanism was identified in prior art.",
        "B": "A very similar existing mechanism was identified in prior art.",
        "C": "An adjacent mechanism family exists; the core rule differs.",
        "D": REQUIRED_NOVELTY_CLAIM,
        "E": "Insufficient evidence to classify novelty.",
    }[cls.name]
    return {
        "prior_art": {
            "novelty_class": cls.value,
            "similar_mechanisms": [
                {"name": "Reference Mechanism", "url": "", "similarity_note": "fixture"}
            ],
            "search_queries": [
                f"{brief.category} supply mechanism",
                f"{brief.name} prior art",
            ],
            "sources": [
                {
                    "title": "Fixture Source",
                    "url": f"fixture://{brief.candidate_id}",
                    "source_type": "web",
                }
            ],
            "findings": ["Fixture finding: adjacent mechanisms exist."],
            "confidence": 0.4,
            "conclusion": conclusion,
        },
        "economist": {
            "summary": (
                f"Fixture analysis of {brief.name}: monetary dynamics depend "
                "on unverified assumptions; treat as HYPOTHESIS."
            ),
            "concerns": [
                {
                    "topic": "incentive compatibility",
                    "note": (
                        "Participants may exit precisely when the mechanism "
                        "needs them to stay."
                    ),
                    "severity": 6.0,
                    "evidence_level": "HYPOTHESIS",
                    "fatal": fatal,
                }
            ],
            "strengths": ["Mechanism rule is explicit and simulatable."],
            "economic_coherence_score": coherence,
            "evidence_level": "HYPOTHESIS",
        },
        "market": {
            "customer": "fixture customer (unverified)",
            "problem": "Fixture problem statement pending real research.",
            "existing_alternatives": ["status quo"],
            "market_size_note": "unknown (fixture)",
            "adoption_barriers": ["no verified demand"],
            "market_demand_score": demand,
            "evidence_level": "HYPOTHESIS",
        },
    }


def fixture_research_responses(briefs: list[CandidateBrief], **kwargs) -> list[str]:
    """One JSON response per candidate, three reports packed per response.

    The mock provider returns one text per agent call, so each candidate
    needs three queued responses in agent order: prior_art, economist, market.
    """
    out: list[str] = []
    for brief in briefs:
        reports = build_research_report_fixture(brief, **kwargs)
        for agent_name in ("prior_art", "economist", "market"):
            out.append(json.dumps(reports[agent_name]))
    return out
