# Research Dossier: Vol-Weighted Fee Smoothing Escrow

- **Candidate ID:** cand-7f4c2dee85e7
- **Category:** transaction fee markets
- **Overall score:** 6.1250
- **Rank:** 1 (recommended)
- **Status:** finalist

## Executive Summary

**Vol-Weighted Fee Smoothing Escrow** (transaction fee markets) currently holds status **finalist** with an overall deterministic score of **6.1250**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Fee-relay vouchers ration exactly during fee spikes (acceptance falls with fee level, the round-2 red-team finding); the congestion-indexed premium that fixes it is a parameter without a balance sheet — nobody funds the counter-cyclical margin top-ups, they are just assumed.

## Mechanism

Fee-voucher buyers pay vol-weighted premiums into a smoothing escrow; when congestion spikes would collapse relayer acceptance margins, the escrow's inventory subsidizes those margins so vouchers stay accepted — the vol payments the market itself made during volatility become the capital that keeps the hedge functioning through the volatility. Calm periods rebate the surplus to holders.

## Mathematical Model

- `X_t` (input, dimensionless): Exogenous fee-volatility shock: positive = spike pressure.
- `W_t` (state, dimensionless): Voucher-attributable fee flow this batch (netted out of the vol measurement).
- `G_t` (state, dimensionless): Realized fee level.
- `v_t` (state, dimensionless): Measured NATIVE vol (voucher-attributable netted out).
- `dv_t` (state, dimensionless): Vol change this batch (the derivative pi_t prices).
- `B_t` (state, dimensionless): Operating escrow inventory.
- `R_t` (state, dimensionless): Season reserve tranche (v2).
- `A_t` (state, dimensionless): Relayer acceptance rate.
- `m_t` (state, dimensionless): Relayer margin health.
- `pi_t` (output, dimensionless): Vol-weighted premium (derivative-priced in v2).
- `reb_t` (output, dimensionless): Calm rebate rate (vol-fall-gated in v2).
- `G_t1` (state, dimensionless): Next fee level.
- `W_t1` (state, dimensionless): Next voucher-attributable flow.
- `v_t1` (state, dimensionless): Next measured native vol.
- `dv_t1` (state, dimensionless): Next vol change.
- `B_t1` (state, dimensionless): Next operating inventory.
- `R_t1` (state, dimensionless): Next reserve tranche.
- `A_t1` (state, dimensionless): Next acceptance.
- `m_t1` (state, dimensionless): Next margin health.

- `G_t1 = clip(G_t * (1 + k_fee * shock_load * X_t), 0, 3)` — Fees follow congestion shocks (unchanged).
- `W_t1 = clip(W_t * 0.7 + 0.3 * voucher_flow, 0, 3)` — Voucher-attributable flow: decaying share of base flow — the netting target (design quantity, not exogenous input: the smoke gate's lesson).
- `v_t1 = clip(v_t + ((abs(G_t1 - G_t) - k_net * abs(W_t1)) - v_t) * (2 / (1 + vol_span)), 0, 3)` — v2 SEPARATION: measured vol nets out voucher-attributable volume — the hedger's own flow cannot pump the input that prices them.
- `dv_t1 = clip(v_t1 - v_t, -1, 1)` — The derivative: vol change this batch.
- `pi_t = min(w_max, pi_base + k_dv * max(0, dv_t1))` — v2 DERIVATIVE PRICING: spikes keep full weight, sustained wash patterns decay to the base — the pattern-amortization attack dies.
- `R_t1 = clip(R_t + r_share * pi_t * voucher_flow - max(0, b_floor - B_t) * 0.5, 0, 3)` — v2 SEASON RESERVE: funded tranche refills the operating escrow when seasons drain it below the floor.
- `B_t1 = clip(B_t + (1 - r_share) * pi_t * voucher_flow - k_sub * max(0, G_t1 - g_target) * B_t / (1 + 0.05 * sub_lag), 0, 3)` — v2 LAGGED SUBSIDY: top-ups amortize across the settlement window — the timing extraction pays carry through the delay.
- `m_t1 = clip(1 - m_load * max(0, G_t1 - g_target) * (1 - k_sub * B_t), 0, 1)` — Margins defended by the amortized subsidy (physics unchanged).
- `A_t1 = clip(A_t + (m_t1 - A_t) * 0.5, 0, 1)` — Acceptance follows margin health (unchanged).
- `reb_t = k_rebate * max(0, B_t - b_floor) * max(0, min(1, 1 - v_t)) * max(0, min(1, 1 - dv_t1))` — v2: rebates require vol LOW and NOT-RISING — manufactured calm plateaus do not qualify; the rebate proves actual calm.

**Parameters:** k_fee ∈ [0.05, 1.5] (default 0.4), vol_span ∈ [2.0, 50.0] (default 12.0), k_net ∈ [0.0, 1.0] (default 0.8), k_dv ∈ [0.0, 1.5] (default 0.6), pi_base ∈ [0.0, 0.05] (default 0.01), w_max ∈ [0.01, 0.5] (default 0.12), voucher_flow ∈ [0.1, 10.0] (default 1.0), k_sub ∈ [0.0, 1.0] (default 0.3), g_target ∈ [0.1, 3.0] (default 1.0), sub_lag ∈ [1.0, 20.0] (default 5.0), k_rebate ∈ [0.0, 0.5] (default 0.1), b_floor ∈ [0.1, 2.0] (default 0.5), r_share ∈ [0.0, 0.5] (default 0.25), m_load ∈ [0.0, 1.0] (default 0.5), shock_load ∈ [0.0, 1.0] (default 0.5)

**Open questions (§13):** k_net=0.8 netting: how much attribution error before the reflexive channel meaningfully reopens?; Does derivative pricing underprice sustained TRUE vol regimes (multi-batch storms)? The plateau-vs-storm frontier needs the battery.; sub_lag=5 amortization: does the per-batch share defend margins fast enough, or does the lag re-create the acceptance trough?; Reserve sizing: r_share=0.25 routes a quarter of income to dead capital — the season-survival/carry frontier for LP economics.; Statistical confidence: k_net, k_dv, sub_lag, r_share are priors; the sweep maps the defended-acceptance region.

**Critical assumptions:** Voucher-attributable flow is trackable at the measurement layer (per-address accounting; k_net<1 covers attribution error honestly).; Derivative pricing keeps true-spike protection: one-span decay removes wash impact while real shocks move dv_t for the full span.

## Economic Analysis

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.00 (INFERENCE; confidence 0.80)
- **market_demand**: 5.50 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 7.50 (FACT; confidence 0.70)
- **security**: 7.00 (INFERENCE; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: The reflexive vol pump: the vol measurement reads the fee footprint of the voucher market's own participants — a whale buying vouchers lifts fees, v_t rises, pi_t taxes every buyer at up to w_max, and…)
- **game_theory:** 3 attack vector(s) recorded; evidence level INFERENCE
- **security:** 3 attack vector(s) recorded; evidence level INFERENCE
- **oracle:** 3 attack vector(s) recorded; evidence level FACT

## Oracle Design

No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: The reflexive vol pump: the vol measurement reads the fee footprint of the voucher market's own participants — a whale buying vouchers lifts fees, v_t rises, pi_t taxes every buyer at up to w_max, and…)
- **game_theory:** 3 attack vector(s) recorded; evidence level INFERENCE
- **security:** 3 attack vector(s) recorded; evidence level INFERENCE
- **oracle:** 3 attack vector(s) recorded; evidence level FACT

## Simulation

- **cand-7f4c2dee85e7-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-7f4c2dee85e7-montecarlo** (seed 7, sim-0.1.0): mean_final=1000.0, p5_final=1000.0, p95_final=1000.0, failures=0
- **cand-7f4c2dee85e7-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-7f4c2dee85e7-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-7f4c2dee85e7-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1000.0, p5_final=1000.0, p95_final=1000.0, failures=0
- **cand-7f4c2dee85e7-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: volatility weighted premium funding; fee smoothing escrow; counter-cyclical liquidity subsidy; funded insurance margin defi; dynamic premium capitalization
  Class: adjacent_mechanism
- Queries: volatility weighted premium funding; fee smoothing escrow; counter-cyclical liquidity subsidy; funded insurance margin defi; dynamic premium capitalization
  Class: adjacent_mechanism
- Queries: volatility weighted premium funding; fee smoothing escrow; counter-cyclical liquidity subsidy; funded insurance margin defi; dynamic premium capitalization
  Class: adjacent_mechanism

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.00 (INFERENCE; confidence 0.80)
- **market_demand**: 5.50 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.55)
- **oracle_feasibility**: 7.50 (FACT; confidence 0.70)
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

**Recommended candidate (§7).** Rank 1 among finalists; selected deterministically from the ranking.
