# Research Dossier: Forecast-Indexed Fee Smoothing Pool

- **Candidate ID:** cand-ce333ff19e9e
- **Category:** monetary policy
- **Overall score:** 6.3000
- **Rank:** 5
- **Status:** finalist

## Executive Summary

**Forecast-Indexed Fee Smoothing Pool** (monetary policy) currently holds status **finalist** with an overall deterministic score of **6.3000**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Fee smoothing mechanisms react to realized congestion, which is late: buffers refill after spikes instead of before them, and the smoothing signal is unfunded opinion rather than priced forecast.

## Mechanism

A prediction market becomes the fee market's forward curve: instead of reacting to realized congestion, the smoothing pool buys its congestion signal in advance from staked forecasts. Forecast accuracy is rewarded by the market itself, and the pool's counter-cyclical buffer is pre-funded by the losing side of the forecast, so smoothing capacity exists before the congestion arrives.

## Mathematical Model

- `X_t` (input, unit): anchor price level (~1000)
- `dX_t` (input, unit): anchor change that step
- `B_t` (state, unit): smoothing buffer level
- `B_t1` (state, unit): next buffer level
- `q_t1` (state, unit): next implied congestion probability

- `q_t1 = clip(0.3 + 0.5*sqrt(abs(dX_t)/X_t), 0.05, 0.95)` — spot implied probability (per-address capped upstream; TWAP applied in buffer rule)
- `B_t1 = clip(B_t*(1-0.1) + 0.1*(1000.0 + 12.0*(q_t1-0.3)), 250.0, 2400.0)` — buffer mean-reverts to belief-scaled target (injection no longer ratchets)

**Parameters:** eta ∈ [20.0, 1600.0] (default 400.0), inject ∈ [2.0, 120.0] (default 30.0), drain ∈ [0.005, 0.3] (default 0.05), pos_cap ∈ [0.01, 0.5] (default 0.2)

**Open questions (§13):** do per-address forecast caps suffice against belief whales?

**Critical assumptions:** implied probability proxies the forecast book midpoint; injection is linear in belief distance from neutral

## Economic Analysis

- **economic_coherence**: 7.50 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 7.00 (HYPOTHESIS; confidence 0.70)
- **security**: 6.50 (HYPOTHESIS; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: belief-whale buffer farming: uncapped forecast positions let one wallet set the implied congestion probability, steering buffer injections toward their own fee-paying transactions…)
- **game_theory:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Oracle Design

No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: belief-whale buffer farming: uncapped forecast positions let one wallet set the implied congestion probability, steering buffer injections toward their own fee-paying transactions…)
- **game_theory:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Simulation

- **cand-ce333ff19e9e-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-ce333ff19e9e-montecarlo** (seed 7, sim-0.1.0): mean_final=1150.2236992470982, p5_final=1143.6792199288905, p95_final=1153.0792546221812, failures=0
- **cand-ce333ff19e9e-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-ce333ff19e9e-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-ce333ff19e9e-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1000.5083180841051, p5_final=1000.4802623182906, p95_final=1000.5413548299864, failures=0
- **cand-ce333ff19e9e-sweep-v2** (seed 7, sim-0.1.0): results recorded
- **exp-3a7ae91132db** (seed None, sim-0.1.0): results recorded
- **exp-94cd2d277999** (seed None, sim-0.1.0): results recorded
- **exp-92383004c71e** (seed None, sim-0.1.0): results recorded
- **exp-f1416fa81e70** (seed None, none): results recorded
- **exp-f8807fc05676** (seed None, none): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: fee smoothing prediction market forward curve; forecast funded congestion buffer
  Class: adjacent_mechanism

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.50 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 7.00 (HYPOTHESIS; confidence 0.70)
- **security**: 6.50 (HYPOTHESIS; confidence 0.80)

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
