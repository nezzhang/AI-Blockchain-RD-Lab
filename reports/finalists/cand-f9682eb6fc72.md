# Research Dossier: Prediction-Settled Hashprice Hedge Board

- **Candidate ID:** cand-f9682eb6fc72
- **Category:** derivatives
- **Overall score:** 6.3500
- **Rank:** 2
- **Status:** finalist

## Executive Summary

**Prediction-Settled Hashprice Hedge Board** (derivatives) currently holds status **finalist** with an overall deterministic score of **6.3500**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

AI compute suppliers have no hedging venue for revenue per unit of work; existing derivative boards settle on single-source indices vulnerable to manipulation.

## Mechanism

A market-priced hedge whose settlement reference is itself a market statistic: supplier-reported realized compute prices aggregate into the very index the hedge settles on. The forecast is a prediction market on the market's own future clearing price, so hedging demand and the reference price come from the same population, and margin scales with realized volatility of that reference.

## Mathematical Model

- `X_t` (input, unit): anchor price level (~1000)
- `dX_t` (input, unit): anchor change that step
- `H_t` (state, unit): net hedge exposure
- `H_t1` (state, unit): next hedge exposure
- `G_t` (state, unit): aggregate margin level
- `G_t1` (state, unit): next margin level
- `v_t` (auxiliary, unit): realized reference volatility

- `v_t = sqrt(abs(dX_t)/X_t)` — concave realized reference volatility
- `H_t1 = clip(H_t*(1-0.1) + 0.1*(1000.0 + hedge_drift*100.0*v_t), 300.0, 2200.0)` — exposure scales with concave reference volatility (EWMA)
- `G_t1 = clip(floor + xi*v_t + abs(H_t1-H_t) + report_bond*max(0.0, v_t-0.1)/10.0, floor, 2600.0)` — margin adds a reporter-bond surcharge when reference volatility exceeds tolerance

**Parameters:** xi ∈ [50.0, 4000.0] (default 900.0), hedge_drift ∈ [0.2, 20.0] (default 4.0), floor ∈ [100.0, 1200.0] (default 400.0), report_bond ∈ [50.0, 5000.0] (default 500.0)

**Open questions (§13):** does supplier-median settlement inherit oracle slashing discipline?

**Critical assumptions:** settlement reference is a median of supplier prices (proxied by anchor); margin marking is linear in realized vol

## Economic Analysis

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 7.00 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 7.00 (HYPOTHESIS; confidence 0.70)
- **security**: 7.00 (HYPOTHESIS; confidence 0.80)

## Game Theory

- **Red Team verdict:** survives (strongest attack: supplier-median inflation double dip: a majority cartel over-reports compute prices to collect on short hedges while raising their own market revenue — but the majority requirement in a competitive su…)
- **game_theory:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Oracle Design

This mechanism requires external data (oracle). See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** survives (strongest attack: supplier-median inflation double dip: a majority cartel over-reports compute prices to collect on short hedges while raising their own market revenue — but the majority requirement in a competitive su…)
- **game_theory:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Simulation

- **cand-f9682eb6fc72-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-f9682eb6fc72-montecarlo** (seed 7, sim-0.1.0): mean_final=1033.9039095720932, p5_final=1032.076266512252, p95_final=1035.2068391637388, failures=0
- **cand-f9682eb6fc72-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-f9682eb6fc72-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-f9682eb6fc72-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1033.887872273653, p5_final=1032.0174878860237, p95_final=1036.090321999077, failures=0
- **cand-f9682eb6fc72-sweep-v2** (seed 7, sim-0.1.0): results recorded
- **exp-9eae131b9baf** (seed None, sim-0.1.0): results recorded
- **exp-756d73d9aa27** (seed None, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: AI compute revenue hedge supplier; median settlement reference compute price board
  Class: adjacent_mechanism

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 7.00 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 7.00 (HYPOTHESIS; confidence 0.70)
- **security**: 7.00 (HYPOTHESIS; confidence 0.80)

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
