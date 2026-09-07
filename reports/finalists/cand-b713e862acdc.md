# Research Dossier: Bandwidth Bond Market for Relay Peers

- **Candidate ID:** cand-b713e862acdc
- **Category:** network economics
- **Overall score:** 6.5250
- **Rank:** 3
- **Status:** finalist

## Executive Summary

**Bandwidth Bond Market for Relay Peers** (network economics) currently holds status **finalist** with an overall deterministic score of **6.5250**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

P2P relay capacity is volunteered and unverified; paid relay markets exist but price capacity without verifying delivery or accounting operational energy cost.

## Mechanism

Internet relay bandwidth becomes a bonded commodity with probe-verified delivery: capacity is committed forward, verified live, and forfaited on shortfall. The energy metering couples the auction price to the real operational (compute and power) cost of delivering the commitment, so underpriced capacity commitments cannot externalize their energy cost.

## Mathematical Model

- `X_t` (input, unit): anchor price level (~1000)
- `dX_t` (input, unit): anchor change that step
- `C_t` (state, unit): bonded capacity pool
- `C_t1` (state, unit): next capacity pool
- `E_t` (state, unit): energy cost index
- `E_t1` (state, unit): next energy cost
- `A_t` (state, unit): capacity lease price
- `A_t1` (state, unit): next lease price
- `s_t` (auxiliary, unit): delivery shortfall intensity

- `s_t = sqrt(max(0.0, 0.05 - dX_t/max(X_t,1.0)) + 0.3*max(0.0, abs(X_t-C_t)/max(X_t,1.0) - 0.1))` — shortfall now includes randomized-probe corroboration: gap between committed capacity and delivered level slashes regardless of which peers probes sample
- `E_t1 = clip(E_t*(1-delta_e) + delta_e*(1000.0 + 250.0*abs(dX_t)/max(X_t,1.0)), 500.0, 2200.0)` — energy index EWMA tracks realized operating intensity
- `A_t1 = clip(0.5*E_t1 + 0.5*C_t1 + 60.0*s_t*3.0, 400.0, 2000.0)` — auction clears at blended energy/capacity plus shortfall premium
- `C_t1 = clip(C_t - chi*s_t*300.0 + 0.07*(1000.0 - C_t) + 0.03*(X_t-1000.0), 450.0, 2400.0)` — forfait on the corroborated gap; calm top-ups replenish

**Parameters:** sigma_s ∈ [0.02, 0.5] (default 0.15), chi ∈ [0.05, 0.8] (default 0.25), delta_e ∈ [0.05, 0.8] (default 0.2)

**Open questions (§13):** should probes sample adversarially placed relays?

**Critical assumptions:** delivered throughput is proxied by anchor level moves; probe gap (commitment minus delivery) drives forfait

## Economic Analysis

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (INFERENCE; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 8.50 (INFERENCE; confidence 0.60)
- **oracle_feasibility**: 7.00 (INFERENCE; confidence 0.70)
- **security**: 7.00 (INFERENCE; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: Probe-route selection by a relay cartel: lease fees collected on undelivered capacity while probes sample healthy peers; profitable with moderate coordination.…)
- **game_theory:** 1 attack vector(s) recorded; evidence level INFERENCE
- **security:** 1 attack vector(s) recorded; evidence level INFERENCE
- **oracle:** 1 attack vector(s) recorded; evidence level INFERENCE

## Oracle Design

No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: Probe-route selection by a relay cartel: lease fees collected on undelivered capacity while probes sample healthy peers; profitable with moderate coordination.…)
- **game_theory:** 1 attack vector(s) recorded; evidence level INFERENCE
- **security:** 1 attack vector(s) recorded; evidence level INFERENCE
- **oracle:** 1 attack vector(s) recorded; evidence level INFERENCE

## Simulation

- **cand-b713e862acdc-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-b713e862acdc-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=762.6156619347444, p5_final=749.7858520928864, p95_final=775.3836624179261, failures=0
- **cand-b713e862acdc-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: bonded bandwidth relay capacity market; verified bandwidth commitment slashing; energy metered bandwidth auction
  Class: appears_substantially_novel
- Queries: bonded bandwidth relay capacity market; verified bandwidth commitment slashing; energy metered bandwidth auction
  Class: appears_substantially_novel
- Queries: bonded bandwidth relay capacity market; verified bandwidth commitment slashing; energy metered bandwidth auction
  Class: appears_substantially_novel
- Queries: bonded bandwidth relay capacity market; verified bandwidth commitment slashing; energy metered bandwidth auction
  Class: appears_substantially_novel

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (INFERENCE; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 8.50 (INFERENCE; confidence 0.60)
- **oracle_feasibility**: 7.00 (INFERENCE; confidence 0.70)
- **security**: 7.00 (INFERENCE; confidence 0.80)

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
