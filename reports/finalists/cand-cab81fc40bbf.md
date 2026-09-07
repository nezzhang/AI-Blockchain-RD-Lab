# Research Dossier: Prediction-Fee Fallback Oracle

- **Candidate ID:** cand-cab81fc40bbf
- **Category:** oracle design
- **Overall score:** 6.6500
- **Rank:** 1 (recommended)
- **Status:** finalist

## Executive Summary

**Prediction-Fee Fallback Oracle** (oracle design) currently holds status **finalist** with an overall deterministic score of **6.6500**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Payment rails that read oracles either halt on feed failure or silently switch to a single fallback; both behaviors are unpriced and invite stale-quote griefing.

## Mechanism

Oracle failure becomes a priced service level instead of a halt: the fee ladder makes degraded data expensive to use, which funds sender insurance and suppresses low-stakes use of the degraded mode. The continuously traded prediction book is the last rung because its open-interest floor makes manipulating the fallback costly in proportion to the damage it could do.

## Mathematical Model

- `X_t` (input, unit): anchor price level (~1000)
- `dX_t` (input, unit): anchor change that step
- `F_l` (state, unit): conversion fee level (ladder rung)
- `F_l1` (state, unit): next fee level
- `O_p` (state, unit): prediction book open interest
- `O_p1` (state, unit): next open interest

- `O_p1 = clip(O_p*(1-0.15) + 0.15*(oi_floor + 150.0*sqrt(abs(dX_t)/X_t) + min(400.0, 0.01*(X_t-1000.0))), 100.0, 1800.0)` — book open interest mean-reverts to floor, activity-shocked
- `F_l1 = clip(F_l*(1-0.05) + 0.05*(500.0 + rung*max(0.0, 600.0-O_p1)/100.0), 500.0, 1600.0)` — fee ladder unchanged; revenue routing fixed upstream

**Parameters:** rung ∈ [10.0, 300.0] (default 80.0), oi_floor ∈ [10.0, 800.0] (default 150.0), decay ∈ [0.02, 0.8] (default 0.2)

**Open questions (§13):** can a griefing attack cheaply force fallback mode?

**Critical assumptions:** staleness forces fallback rungs proportional to book thinness; last-rung use requires the open-interest floor

## Economic Analysis

- **economic_coherence**: 7.50 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 8.50 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 7.50 (HYPOTHESIS; confidence 0.70)
- **security**: 7.00 (HYPOTHESIS; confidence 0.80)

## Game Theory

- **Red Team verdict:** survives (strongest attack: coordinated book exit attack: LPs thin the book to force fallback fees, then re-enter to capture them — but the OI floor forces the attackers to hold real capital at the thin-book prices, and sender c…)
- **game_theory:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Oracle Design

This mechanism requires external data (oracle). See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** survives (strongest attack: coordinated book exit attack: LPs thin the book to force fallback fees, then re-enter to capture them — but the OI floor forces the attackers to hold real capital at the thin-book prices, and sender c…)
- **game_theory:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Simulation

- **cand-cab81fc40bbf-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-cab81fc40bbf-montecarlo** (seed 7, sim-0.1.0): mean_final=841.8758240133304, p5_final=841.208802521114, p95_final=842.7144339712042, failures=0
- **cand-cab81fc40bbf-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-cab81fc40bbf-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-cab81fc40bbf-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=842.0673173944782, p5_final=841.6803565621009, p95_final=842.7505105047659, failures=0
- **cand-cab81fc40bbf-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: oracle staleness fallback payment rail; prediction book oracle fallback open interest floor
  Class: appears_substantially_novel

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.50 (INFERENCE; confidence 0.80)
- **game_theory**: 7.50 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 8.50 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 7.50 (HYPOTHESIS; confidence 0.70)
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

**Recommended candidate (§7).** Rank 1 among finalists; selected deterministically from the ranking.
