"""Discovery Agent (§9, Phase 1).

Generates novel blockchain economic *mechanisms* — not token names — across
the §24 source domains. Structured output only: an IdeaBatch validated
against Pydantic schemas before anything downstream sees it.
"""

from __future__ import annotations

import random
from typing import Any

from pydantic import BaseModel, Field

from blockchain_rd_lab.agents.base import (
    BaseAgent,
    LLMMessage,
    LLMProvider,
    ModelTier,
)
from blockchain_rd_lab.config import ResearchConfig, load_research
from blockchain_rd_lab.discovery import IdeaBatch
from blockchain_rd_lab.schemas import FORBIDDEN_NOVELTY_CLAIM, REQUIRED_NOVELTY_CLAIM


class DiscoveryPayload(BaseModel):
    """Input for one discovery call."""

    count: int = 5
    domains: list[str] = Field(default_factory=list)
    avoid_topics: list[str] = Field(default_factory=list)
    combination_hint: str = ""


DISCOVERY_SYSTEM_PROMPT = f"""You are the Discovery Agent of an independent blockchain
economic-mechanism research laboratory.

MISSION: generate genuinely novel blockchain economic MECHANISMS — supply
rules, monetary systems, stablecoin mechanisms, incentive structures, oracle
designs, payment protocols — NOT token names, NOT marketing copy.

RULES:
1. Every idea must be an economically coherent mechanism with a clear
   problem, inputs, outputs, and causal chain.
2. Do not assume a mechanism needs a token or a blockchain. Include the
   required implementation type honestly (token / contract / protocol /
   oracle / payment network / no blockchain at all).
3. Span the requested source domains: draw mechanisms from economics,
   finance, demographics, AI, energy, climate, biology, mathematics,
   game theory, information theory, network economics, insurance,
   prediction markets, commodities, labor, trade, distributed systems.
4. If asked to combine concepts, reason about ECONOMIC COMPATIBILITY and
   semantic bridges — never random mashups.
5. Innovation claims must say: "{REQUIRED_NOVELTY_CLAIM}"
   NEVER say: "{FORBIDDEN_NOVELTY_CLAIM}"
6. Output ONLY a JSON object matching the requested schema. No prose
   outside the JSON.

QUALITY BAR: prefer fewer, sharper mechanisms over many vague ones. Each
description must specify how the mechanism actually operates, step by step.
"""


class DiscoveryAgent(BaseAgent):
    """Generates candidate mechanism ideas (Phase 1)."""

    name = "discovery"
    role = "Generate novel blockchain economic mechanisms across source domains"
    input_schema = DiscoveryPayload
    output_schema = IdeaBatch
    model_tier = ModelTier.MEDIUM
    temperature = 0.9

    def __init__(
        self,
        provider: LLMProvider,
        database: Any | None = None,
        research_config: ResearchConfig | None = None,
    ) -> None:
        super().__init__(provider, database)
        self.research = research_config or load_research()

    def build_prompt(self, payload: BaseModel) -> list[LLMMessage]:
        if not isinstance(payload, DiscoveryPayload):
            got = type(payload).__name__
            raise TypeError(f"DiscoveryAgent expects DiscoveryPayload, got {got}")
        domains = (
            payload.domains
            if payload.domains
            else random.sample(
                self.research.discovery_domains,
                k=min(3, len(self.research.discovery_domains)),
            )
        )
        parts = [
            f"Generate {payload.count} novel blockchain economic mechanism ideas.",
            f"Source domains to draw from: {', '.join(domains)}.",
        ]
        if payload.avoid_topics:
            parts.append(
                "Avoid re-generating ideas similar to these known topics: "
                + "; ".join(payload.avoid_topics[:30])
                + "."
            )
        if self.research.discovery.require_combinatorics and payload.combination_hint:
            parts.append(
                "Mechanism combinatorics (§18): " + payload.combination_hint
            )
        parts.append(
            "For each idea provide: name, category, domain, description "
            "(step-by-step mechanism), core_mechanism (one-paragraph causal chain), "
            "problem, innovation_claim, inputs, outputs, oracle_required, "
            "blockchain_required, token_required."
        )
        return [
            LLMMessage(role="system", content=DISCOVERY_SYSTEM_PROMPT),
            LLMMessage(role="user", content="\n".join(parts)),
        ]
