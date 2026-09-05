# Research Dossier: Homeostatic Reserve Stablecoin

- **Candidate ID:** cand-c17ab7a0f74e
- **Category:** stablecoins
- **Overall score:** 5.2500
- **Rank:** 2
- **Status:** finalist

## Executive Summary

**Homeostatic Reserve Stablecoin** (stablecoins) currently holds status **finalist** with an overall deterministic score of **5.2500**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Existing stablecoins rely on a single correction instrument (redemption arbitrage); under sustained stress that one layer either breaks the peg or drains the reserve, and there is no principled policy for when correction mechanisms themselves should stop consuming collateral.

## Mechanism

Three nested negative-feedback layers with fixed thresholds act like homeostatic loops: small deviations trigger cheap fee nudges; medium deviations trigger yield-funded rebalancing; large deviations throttle supply and deploy the insurance tranche. The reflexive safety (yield redirection pauses when reserve ratio hits its floor) mirrors biological homeostasis — exhausted mechanisms rest — which is precisely the anti-death-spiral property single-layer pegs lack. Causal chain: deviation d → layer activation L(d) → counteracting capital flow → deviation shrinks → layer deactivates → no overshoot from over-correction.

## Mathematical Model

- `P_t` (state, dimensionless (target = 1.0)): Market price of the stable unit relative to its reference basket at time t.
- `X_t` (input, dimensionless): Exogenous stress/anchor series from the simulation harness (e.g., demand shock size); interpreted here as the reference-basket value shock applied at t.
- `D_t` (auxiliary, dimensionless): Signed deviation of price from target: D_t = P_t - 1.
- `A_t` (auxiliary, dimensionless): Layer activation level: 0 = dormant, 1 = first layer (fee nudges), 2 = second layer (yield redirection), 3 = third layer (mint throttle + tranche).
- `F_t` (output, dimensionless fraction): Redemption fee multiplier applied at t; mint fee moves oppositely.
- `Y_t` (state, dimensionless fraction): Share of reserve yield currently redirected to the market side that shrinks deviation.
- `R_t` (state, dimensionless ratio): Reserve ratio (collateral value / outstanding supply); the homeostatic band is [r_min, r_max].
- `M_t` (output, dimensionless fraction): Mint-throttle factor: fraction of requested new supply actually allowed at t.
- `P_t1` (state, dimensionless): Price at the next step after the layered responses act.
- `R_t1` (state, dimensionless ratio): Reserve ratio at the next step after yield redirection and throttle act.
- `B_t` (auxiliary, fraction per step): Reserve burn rate: redemption flow this step as a fraction of the reserve.
- `E_t` (state, dimensionless): Signed oscillation accumulator: cumulative absolute deviation crossings used to deplete fee-farming yield.
- `W_t` (state, dimensionless): Time-weighted (EWMA) deviation; layer-3 and tranche deployment key on W_t so single-candle wicks cannot trigger them.
- `W_t1` (state, dimensionless): Next-step EWMA deviation.
- `E_t1` (state, dimensionless): Next-step oscillation accumulator.

- `D_t = P_t - 1` — Signed price deviation from the unit target.
- `A_t = min(3, (abs(D_t) / theta1) * (abs(D_t) / theta2))` — Graded activation proxy: deviation beyond each threshold contributes activation energy; clipped to layer 3. The product form keeps sub-threshold deviations dormant.
- `F_t = f_cap * clip(k_fee * D_t, -1, 1)` — Layer 1: redemption fee rises when price is above peg (positive D_t) and falls (rebate) when below, bounded by f_cap.
- `Y_t = y_max * clip(k_yield * (-D_t), -1, 1) * max(0, min(1, (R_t - r_min) / 0.05))` — Layer 2: yield share redirected toward the shrinking side (sign opposite the deviation), scaled down smoothly to zero as the reserve ratio approaches the band floor r_min — the homeostatic rest rule.
- `M_t = max(0.05, 1 - k_throttle * max(0, abs(D_t) - theta3))` — Layer 3: new supply creation is throttled proportionally to deviation beyond theta3, floored at 5% so the market never fully loses mint access.
- `R_t1 = clip(R_t + shock_load * X_t - abs(Y_t) * 0.02 + rr_drift, r_min * 0.9, r_max)` — Reserve ratio evolves with exogenous stress, layer-2 yield outflow (only when active), and a slow retained-yield rebuild.
- `P_t1 = clip(P_t + shock_load * X_t - k_recover * (F_t + Y_t + 0.1 * (1 - M_t)), 0.5, 2.0)` — Next price: exogenous shock moves price; the sum of active corrective flows (fee effect, redirected yield, and throttle-induced scarcity) pulls it back, all bounded by clip to a plausible regime.
- `B_t = abs(shock_load * X_t) + 0.01 * abs(D_t)` — Redemption-pressure proxy: exogenous stress flow plus price-deviation-driven redemption demand.
- `W_t1 = W_t * (1 - lambda_w) + lambda_w * D_t` — Time-weighted deviation (EWMA): wicks that evaporate never push W_t past theta3.
- `E_t1 = E_t * e_decay + abs(D_t - D_t)` — Oscillation accumulator: grows with each sign change in deviation (here driven by per-step deviation movement), depleting the farming yield.
- `F_t = f_cap * clip(k_fee * D_t, -1, 1) * max(0.1, 1 - E_t)` — Layer 1 (patched): the fee rebate decays with the oscillation accumulator, so boundary farming has negative expectation.
- `Y_t = y_max * clip(k_yield * (-D_t), -1, 1) * max(0, min(1, (R_t - r_min) / 0.05)) * max(0, min(1, (b_rest - B_t) / b_rest))` — Layer 2 (patched): the taper is now the MAXIMUM of the ratio factor and the burn-rate factor — layer 2 rests only when outflow pressure has ALSO ceased. A whale pushing R_t to the floor with redemptions keeps layer 2 active.
- `M_t = max(0.05, 1 - k_throttle * max(0, abs(W_t) - theta3))` — Layer 3 (patched): the throttle keys on the time-weighted deviation W_t, not the instantaneous D_t.
- `R_t1 = clip(R_t + shock_load * X_t * (1 - rho_cap) - abs(Y_t) * 0.02 + rr_drift, r_min * 0.9, r_max)` — Reserve update (patched): the effective shock contribution of any model-marked component is bounded by rho_cap — depressing one mark cannot push the ratio to the floor alone.

**Parameters:** theta1 ∈ [0.001, 0.05] (default 0.005), theta2 ∈ [0.01, 0.1] (default 0.05), theta3 ∈ [0.05, 0.3] (default 0.2), k_fee ∈ [0.1, 10.0] (default 2.0), f_cap ∈ [0.01, 0.2] (default 0.03), k_yield ∈ [0.1, 10.0] (default 1.5), y_max ∈ [0.05, 1.0] (default 0.5), r_min ∈ [1.0, 1.1] (default 1.05), r_max ∈ [1.1, 2.0] (default 1.3), k_throttle ∈ [0.5, 20.0] (default 4.0), k_recover ∈ [0.1, 2.0] (default 0.6), shock_load ∈ [0.0, 1.0] (default 0.3), rr_drift ∈ [0.0, 0.05] (default 0.005), b_rest ∈ [0.005, 0.1] (default 0.02), lambda_w ∈ [0.05, 1.0] (default 0.08), rho_cap ∈ [0.01, 0.5] (default 0.1), e_decay ∈ [0.9, 1.0] (default 0.98)

**Open questions (§13):** What half-life for lambda_w makes the TWAP long enough to defeat wicks but short enough to react to genuine sustained stress? (This patch guesses 12 steps; untested.); The burn-rate b_rest threshold is set to 2% of reserve per step — what empirically separates whale pressure from organic redemption demand?; Does the oscillation accumulator E_t decay between epochs, and if so, how fast, without re-opening the farm after decay?; rho_cap at 10% assumes liquid-component dominance in the reserve — what happens when the reserve MUST hold >10% model-marked assets?; All four fixes add parameters; the model now has 18 — is the added complexity itself a governance/audit risk (honest concern, unfixed here)?

**Critical assumptions:** Arbitrageurs respond to fee and yield differentials within one step (k_recover captures their effectiveness).; Reserve yield is positive and available at the assumed rate; its absolute magnitude is folded into the rr_drift and Y_t coefficients.; Layer thresholds theta1 < theta2 < theta3 are fixed by rule and never moved under stress (no discretion).

## Economic Analysis

- **economic_coherence**: 6.50 (INFERENCE; confidence 0.80)
- **game_theory**: 5.00 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 5.50 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.65)
- **oracle_feasibility**: 4.50 (HYPOTHESIS; confidence 0.70)
- **security**: 4.00 (HYPOTHESIS; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: The reserve-floor defense switch-off: a whale-scale attacker induces redemption pressure until R_t reaches the floor r_min, at which point the mechanism's own homeostatic rest rule tapers layer-2 yiel…)
- **game_theory:** 3 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 3 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 2 attack vector(s) recorded; evidence level HYPOTHESIS

## Oracle Design

No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: The reserve-floor defense switch-off: a whale-scale attacker induces redemption pressure until R_t reaches the floor r_min, at which point the mechanism's own homeostatic rest rule tapers layer-2 yiel…)
- **game_theory:** 3 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 3 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 2 attack vector(s) recorded; evidence level HYPOTHESIS

## Simulation

- **cand-c17ab7a0f74e-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-c17ab7a0f74e-montecarlo** (seed 7, sim-0.1.0): mean_final=1000.0, p5_final=1000.0, p95_final=1000.0, failures=0
- **cand-c17ab7a0f74e-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-c17ab7a0f74e-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-c17ab7a0f74e-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1000.0, p5_final=1000.0, p95_final=1000.0, failures=0
- **cand-c17ab7a0f74e-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: layered stablecoin peg defense mechanisms survey; homeostatic feedback control stablecoin design; reserve yield redirection stablecoin peg stabilization; mint throttle death spiral stablecoin mechanis
  Class: adjacent_mechanism
- Queries: layered stablecoin peg defense mechanisms survey; homeostatic feedback control stablecoin design; reserve yield redirection stablecoin peg stabilization; mint throttle death spiral stablecoin mechanis
  Class: adjacent_mechanism
- Queries: layered stablecoin peg defense mechanisms survey; homeostatic feedback control stablecoin design; reserve yield redirection stablecoin peg stabilization; mint throttle death spiral stablecoin mechanis
  Class: adjacent_mechanism

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 6.50 (INFERENCE; confidence 0.80)
- **game_theory**: 5.00 (HYPOTHESIS; confidence 0.80)
- **market_demand**: 5.50 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.65)
- **oracle_feasibility**: 4.50 (HYPOTHESIS; confidence 0.70)
- **security**: 4.00 (HYPOTHESIS; confidence 0.80)

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
