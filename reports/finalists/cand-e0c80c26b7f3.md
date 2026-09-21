# Research Dossier: Quote-Deviation Slashed FX Reference Feed

- **Candidate ID:** cand-e0c80c26b7f3
- **Category:** oracle design
- **Overall score:** 6.3000
- **Rank:** 4
- **Status:** finalist

## Executive Summary

**Quote-Deviation Slashed FX Reference Feed** (oracle design) currently holds status **finalist** with an overall deterministic score of **6.3000**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

FX reference rates for DeFi settlement are either imported from centralized feeds (trust) or composed from unbonded quotes (manipulable at low cost).

## Mechanism

An oracle design whose integrity check is endogenous: the reference rate is disciplined by the very settlement flow it serves, and bonding makes deviation prepaid rather than post-hoc disputed. Median composition plus deviation-scaled slashing turns quote manipulation into a predictable loss.

## Mathematical Model

No formal model stored yet (run `lab formalize`).

## Economic Analysis

- **novelty**: 6.00 (INFERENCE; confidence 0.60)
- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **capital_efficiency**: 5.00 (INFERENCE; confidence 0.60)

## Game Theory

- **game_theory**: 7.50 (INFERENCE; confidence 0.80)

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

- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **network_effects**: 6.50 (INFERENCE; confidence 0.60)
- **communication**: 7.00 (INFERENCE; confidence 0.70)
- **viral_potential**: 6.00 (INFERENCE; confidence 0.60)

## Technical Architecture

- **technical_feasibility**: 7.00 (INFERENCE; confidence 0.70)
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
