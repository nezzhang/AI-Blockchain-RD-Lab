# Research Dossier: AI-Compute Denominated Debt

- **Candidate ID:** cand-1acbaa9de0b0
- **Category:** financial markets
- **Overall score:** 5.0500
- **Rank:** 11
- **Status:** finalist

## Executive Summary

**AI-Compute Denominated Debt** (financial markets) currently holds status **finalist** with an overall deterministic score of **5.0500**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Monetary units ignore productivity deflation

## Mechanism

Debt quoted in compute-hours; settlement converts via compute price oracles.

## Mathematical Model

- `S_t` (state, tokens): Mechanism-controlled supply at step t.
- `X_t` (input, units_of_anchor): Exogenous anchor quantity reported to the mechanism.
- `dX_t` (input, units_of_anchor): Change in anchor between reports.
- `S_t1` (output, tokens): Supply after applying the rule.
- `g_raw_t` (auxiliary, fraction): Uncapped per-step growth fraction.
- `g_t` (auxiliary, fraction): Capped per-step growth fraction actually applied.

- `g_raw_t = alpha * dX_t / X_t` — Uncapped growth fraction implied by the anchor delta.
- `g_t = clip(g_raw_t, f, c)` — Growth fraction after applying floor and cap (§13).
- `S_t1 = S_t * (1 + g_t)` — Supply rule: scale supply by the capped growth factor.

**Parameters:** coupling ∈ [0.0, 2.0] (default 0.5), floor ∈ [-0.1, 0.0] (default -0.05), cap ∈ [0.0, 0.1] (default 0.05)

**Open questions (§13):** What value of alpha keeps volatility within the cap band (§13)?; Should the rule smooth over a lag window instead of reacting per report?; How are oracle revisions and restatements handled retroactively?; What oracle frequency balances statistical confidence against cost?

**Critical assumptions:** The anchor quantity X_t is reported truthfully and on schedule.

## Economic Analysis

- **economic_coherence**: 5.00 (HYPOTHESIS; confidence 0.80)
- **game_theory**: 5.50 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 5.00 (HYPOTHESIS; confidence 0.70)
- **novelty**: 5.00 (INFERENCE; confidence 0.40)
- **oracle_feasibility**: 5.00 (HYPOTHESIS; confidence 0.70)
- **security**: 5.00 (HYPOTHESIS; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: Coordinate an anchor spike during a low-liquidity window so the mechanism over-expands exactly when exit is cheapest.…)
- **game_theory:** 2 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 2 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Oracle Design

This mechanism requires external data (oracle). See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: Coordinate an anchor spike during a low-liquidity window so the mechanism over-expands exactly when exit is cheapest.…)
- **game_theory:** 2 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 2 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Simulation

- **cand-1acbaa9de0b0-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-1acbaa9de0b0-montecarlo** (seed 7, sim-0.1.0): mean_final=1240.6944547857192, p5_final=1220.2580406408717, p95_final=1257.8568144250726, failures=0
- **cand-1acbaa9de0b0-sweep** (seed 7, sim-0.1.0): results recorded
- **exp-bb4142aa974f** (seed None, sim-0.1.0): results recorded
- **exp-ccf4f8274666** (seed None, sim-0.1.0): results recorded
- **exp-835ec0410169** (seed None, sim-0.1.0): results recorded
- **exp-424d1da9b5fa** (seed None, none): results recorded
- **exp-4d063f4fe6a7** (seed None, none): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: financial markets supply mechanism; AI-Compute Denominated Debt prior art
  Class: insufficient_evidence

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 5.00 (HYPOTHESIS; confidence 0.80)
- **game_theory**: 5.50 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 5.00 (HYPOTHESIS; confidence 0.70)
- **novelty**: 5.00 (INFERENCE; confidence 0.40)
- **oracle_feasibility**: 5.00 (HYPOTHESIS; confidence 0.70)
- **security**: 5.00 (HYPOTHESIS; confidence 0.80)

## Technical Architecture

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
