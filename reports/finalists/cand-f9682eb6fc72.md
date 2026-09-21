# Research Dossier: Prediction-Settled Hashprice Hedge Board

- **Candidate ID:** cand-f9682eb6fc72
- **Category:** derivatives
- **Overall score:** 6.1750
- **Rank:** 6
- **Status:** finalist

## Executive Summary

**Prediction-Settled Hashprice Hedge Board** (derivatives) currently holds status **finalist** with an overall deterministic score of **6.1750**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

AI compute suppliers have no hedging venue for revenue per unit of work; existing derivative boards settle on single-source indices vulnerable to manipulation.

## Mechanism

A market-priced hedge whose settlement reference is itself a market statistic: supplier-reported realized compute prices aggregate into the very index the hedge settles on. The forecast is a prediction market on the market's own future clearing price, so hedging demand and the reference price come from the same population, and margin scales with realized volatility of that reference.

## Mathematical Model

No formal model stored yet (run `lab formalize`).

## Economic Analysis

- **novelty**: 6.00 (INFERENCE; confidence 0.55)
- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **capital_efficiency**: 5.50 (INFERENCE; confidence 0.60)

## Game Theory

- **game_theory**: 7.50 (HYPOTHESIS; confidence 0.80)

## Oracle Design

- **oracle_feasibility**: 5.00 (IMPUTED at the 5.0 floor; no authored agent evidence, §19)
No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **security**: 5.00 (IMPUTED at the 5.0 floor; no authored agent evidence, §19)
No adversarial review recorded yet (run `lab redteam`).

## Simulation

No simulation runs recorded yet (run `lab simulate`).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

No prior-art research recorded yet (run `lab research`).

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **market_demand**: 7.00 (INFERENCE; confidence 0.70)
- **network_effects**: 6.50 (INFERENCE; confidence 0.60)
- **communication**: 5.50 (INFERENCE; confidence 0.60)
- **viral_potential**: 6.00 (INFERENCE; confidence 0.60)

## Technical Architecture

- **technical_feasibility**: 5.50 (INFERENCE; confidence 0.60)
Blockchain required: yes; token required: no. Detailed architecture arrives with the Blockchain Architect review (future phase).

## Regulatory Risks

Regulatory review is pending. This lab does not provide legal advice; risks are flagged for professional review (§9).

## MVP

MVP scoping pending; see Open Questions.

## Risks

No fatal flaws recorded. Residual risks live in the adversarial sections above.

## Open Questions

See the Mathematical Model section's §13 open questions; unresolved items remain HYPOTHESIS-level (§29).

## Recommendation

Not the recommended candidate this cycle. See the lab report for the current recommendation.
