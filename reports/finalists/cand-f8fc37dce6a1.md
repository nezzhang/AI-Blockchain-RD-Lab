# Research Dossier: Drawdown-Underwritten Liquidity Corridor

- **Candidate ID:** cand-f8fc37dce6a1
- **Category:** two-sided market
- **Overall score:** 6.4000
- **Rank:** 6
- **Status:** finalist

## Executive Summary

**Drawdown-Underwritten Liquidity Corridor** (two-sided market) currently holds status **finalist** with an overall deterministic score of **6.4000**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Decentralized FX corridors lose depth exactly when needed; there is no priced mechanism converting passive liquidity into a funded backstop that scales with realized risk.

## Mechanism

The market's own realized drawdown series is the insurance price signal: deeper observed tails raise underwriter premiums, which recruits more backstop depth precisely when ordinary liquidity is most fragile. The conversion price caps corridor losses for traders while giving underwriters a bounded, priced position rather than an open-ended one.

## Mathematical Model

- `X_t` (input, unit): anchor price level (~1000)
- `dX_t` (input, unit): anchor change that step
- `D_t` (state, unit): smoothed corridor drawdown
- `D_t1` (state, unit): next drawdown state
- `U_t` (state, unit): underwriter tranche capacity
- `U_t1` (state, unit): next tranche capacity

- `D_t1 = clip(D_t*(1-lambda_) + lambda_*sqrt(abs(dX_t)/X_t)*900.0, 0.0, 900.0)` — negative anchor moves accumulate into drawdown (EWMA)
- `U_t1 = clip(U_t*(1-0.1) + 0.1*(1000.0 + min(600.0, 0.04*(X_t-1000.0)) - 2.0*D_t1) - remark_k*(D_t1 - D_t)*10.0, 200.0, 2500.0)` — conversion capacity shrinks as drawdown ACCELERATES (dynamic barrier vs pump-then-drown)

**Parameters:** lambda_ ∈ [0.05, 0.9] (default 0.3), gamma ∈ [10.0, 600.0] (default 150.0), topup ∈ [1.0, 40.0] (default 8.0), remark_k ∈ [0.1, 2.0] (default 0.8)

**Open questions (§13):** should conversion price re-mark from the drawdown series itself?

**Critical assumptions:** drawdown is proxied by negative anchor deltas; conversion is linear in drawdown increments

## Economic Analysis

- **economic_coherence**: 7.50 (INFERENCE; confidence 0.80)
- **game_theory**: 7.00 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 8.50 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 6.00 (HYPOTHESIS; confidence 0.70)
- **security**: 6.50 (HYPOTHESIS; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: pump-then-drown drawdown conversion: inflate underwriter capacity by pumping the corridor level, then pin drawdown at its cap to force full tranche conversion at the static pre-agreed price — the whal…)
- **game_theory:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Oracle Design

This mechanism requires external data (oracle). See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: pump-then-drown drawdown conversion: inflate underwriter capacity by pumping the corridor level, then pin drawdown at its cap to force full tranche conversion at the static pre-agreed price — the whal…)
- **game_theory:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 1 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Simulation

- **cand-f8fc37dce6a1-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-f8fc37dce6a1-montecarlo** (seed 7, sim-0.1.0): mean_final=78.9928101081336, p5_final=74.63640595390993, p95_final=84.33233548996836, failures=0
- **cand-f8fc37dce6a1-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-f8fc37dce6a1-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-f8fc37dce6a1-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=76.41322494827291, p5_final=71.71375137945122, p95_final=82.07834457243612, failures=0
- **cand-f8fc37dce6a1-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: underwriter tranche liquidity pool drawdown conversion; decentralized FX backstop depth insurance
  Class: appears_substantially_novel

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.50 (INFERENCE; confidence 0.80)
- **game_theory**: 7.00 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **novelty**: 8.50 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 6.00 (HYPOTHESIS; confidence 0.70)
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
