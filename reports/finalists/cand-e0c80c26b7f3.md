# Research Dossier: Quote-Deviation Slashed FX Reference Feed

- **Candidate ID:** cand-e0c80c26b7f3
- **Category:** oracle design
- **Overall score:** 6.3250
- **Rank:** 4
- **Status:** finalist

## Executive Summary

**Quote-Deviation Slashed FX Reference Feed** (oracle design) currently holds status **finalist** with an overall deterministic score of **6.3250**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

FX reference rates for DeFi settlement are either imported from centralized feeds (trust) or composed from unbonded quotes (manipulable at low cost).

## Mechanism

An oracle design whose integrity check is endogenous: the reference rate is disciplined by the very settlement flow it serves, and bonding makes deviation prepaid rather than post-hoc disputed. Median composition plus deviation-scaled slashing turns quote manipulation into a predictable loss.

## Mathematical Model

- `X_t` (input, unit): anchor price level (~1000)
- `dX_t` (input, unit): anchor change that step
- `M_t` (state, unit): published median reference
- `M_t1` (state, unit): next reference
- `S_t` (state, unit): reporter bond pool
- `S_t1` (state, unit): next bond pool
- `d_t` (auxiliary, unit): quote deviation vs realized

- `d_t = max(0.0, abs(dX_t)/max(X_t,1.0) - tau)` — tolerance-exceeded deviation of quotes from realized
- `M_t1 = clip(M_t*(1-0.3) + 0.3*(1000.0 + min(500.0, 0.6*(X_t-1000.0))) + 0.25*min(400.0, X_t-M_t), 500.0, 2500.0)` — median chases realized execution with bounded speed
- `S_t1 = clip(S_t + mu_b - 0.05*(S_t-1000.0) - omega*d_t*600.0*min(1.0, X_t/1200.0) - min(150.0, max(0.0, 0.02*(1000.0-X_t))), 500.0, 2400.0)` — slash intensity gated by realized-flow level (min(1, X/1200)): thin windows carry near-zero slash, neutralizing cheap anchor capture

**Parameters:** tau ∈ [0.02, 0.5] (default 0.15), omega ∈ [0.05, 0.9] (default 0.45), mu_b ∈ [2.0, 50.0] (default 12.0)

**Open questions (§13):** should the tolerance band widen in low-flow windows?

**Critical assumptions:** realized execution price is proxied by the anchor level; slash condition only applies above realized-flow floor

## Economic Analysis

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (INFERENCE; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.60)
- **oracle_feasibility**: 7.50 (INFERENCE; confidence 0.70)
- **security**: 7.00 (INFERENCE; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: Thin-window anchor capture: cheap realized-price moves in low-flow windows weaponize deviation slashes against honest reporters; profitable below the flow floor.…)
- **game_theory:** 1 attack vector(s) recorded; evidence level INFERENCE
- **security:** 1 attack vector(s) recorded; evidence level INFERENCE
- **oracle:** 1 attack vector(s) recorded; evidence level INFERENCE

## Oracle Design

This mechanism requires external data (oracle). See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: Thin-window anchor capture: cheap realized-price moves in low-flow windows weaponize deviation slashes against honest reporters; profitable below the flow floor.…)
- **game_theory:** 1 attack vector(s) recorded; evidence level INFERENCE
- **security:** 1 attack vector(s) recorded; evidence level INFERENCE
- **oracle:** 1 attack vector(s) recorded; evidence level INFERENCE

## Simulation

- **cand-e0c80c26b7f3-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-e0c80c26b7f3-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1404.7404704910907, p5_final=1365.5230201519157, p95_final=1437.3051681731536, failures=0
- **cand-e0c80c26b7f3-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: oracle deviation slashing realized price anchor; bonded reporter median FX reference feed; self-anchoring oracle design
  Class: adjacent_mechanism
- Queries: oracle deviation slashing realized price anchor; bonded reporter median FX reference feed; self-anchoring oracle design
  Class: adjacent_mechanism
- Queries: oracle deviation slashing realized price anchor; bonded reporter median FX reference feed; self-anchoring oracle design
  Class: adjacent_mechanism
- Queries: oracle deviation slashing realized price anchor; bonded reporter median FX reference feed; self-anchoring oracle design
  Class: adjacent_mechanism

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (INFERENCE; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.60)
- **oracle_feasibility**: 7.50 (INFERENCE; confidence 0.70)
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
