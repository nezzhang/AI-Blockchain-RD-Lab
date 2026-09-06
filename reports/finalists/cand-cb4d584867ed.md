# Research Dossier: Tranche-Segmented Settlement Guarantee Stack

- **Candidate ID:** cand-cb4d584867ed
- **Category:** institutional settlement
- **Overall score:** 6.1000
- **Rank:** 2
- **Status:** finalist

## Executive Summary

**Tranche-Segmented Settlement Guarantee Stack** (institutional settlement) currently holds status **finalist** with an overall deterministic score of **6.1000**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Settlement guarantees today are flat pools: one capital layer, one price, one trigger. Routine small failures (latency straddles) and rare big ones (solver strikes) draw on the same capital, so the pool must be sized for the tail while charging for the average — participants overpay for routine coverage, and the pool is still undercapitalized for the event it exists for.

## Mechanism

Settlement risk is tranched into a capital stack whose split point is set by a prediction market's implied stress odds: rising odds shift pre-commitment toward the event layer (junior/fallback) before stress arrives; falling odds rebuild the cheap routine layer (senior). Senior tranches are priced as steady fees (routine small failures), junior tranches earn state-dependent fragility premiums (rare big failures), and the fallback solver consumes junior capital when it activates. The market's early warning becomes a capital reallocation — the stack re-prices itself ahead of the event instead of being surprised by it.

## Mathematical Model

- `X_t` (input, dimensionless): Exogenous stress series: positive = implied stress odds rising.
- `dX_t` (input, dimensionless): Anchor change per batch (battery input).
- `M_t` (state, dimensionless): Tracked whale/manipulator flow contribution (netted out of draws); decays each batch unless refreshed by tracked whale flow.
- `Q_t` (state, dimensionless): Fast-window implied odds (pricing clock).
- `Q_slow` (state, dimensionless): Slow-window implied odds (capital clock) — v2's split steering.
- `S_t` (state, dimensionless): Senior tranche balance.
- `J_t` (state, dimensionless): Junior tranche balance.
- `w_t` (state, dimensionless): Tranche split point (junior share).
- `r_t` (state, dimensionless): Routine-failure draw (wash-filtered in v2).
- `e_t` (state, dimensionless): Event-failure draw.
- `pi_s_t` (output, dimensionless): Senior fee rate.
- `pi_j_t` (output, dimensionless): Junior premium rate (carry-floored in v2).
- `Q_t1` (state, dimensionless): Next fast odds.
- `Q_slow1` (state, dimensionless): Next slow odds.
- `S_t1` (state, dimensionless): Next senior balance.
- `J_t1` (state, dimensionless): Next junior balance.
- `w_t1` (state, dimensionless): Next split point.
- `M_t1` (state, dimensionless): Next tracked whale contribution.

- `Q_t1 = clip(Q_t + k_odds * shock_load * X_t * (2 / (1 + ema_span)), 0, 1)` — Fast clock (pricing): short window, responsive — pattern pumps move price here only.
- `Q_slow1 = clip(Q_slow + (Q_t1 - Q_slow) * (2 / (1 + slow_span)), 0, 1)` — v2 SPLIT STEERING: slow clock (capital) — the boundary reads this; a pattern must persist 6x longer to move allocation.
- `w_t1 = clip(w_t + w_step * max(-1, min(1, (w_min + (w_max - w_min) * Q_slow1 - w_t) / w_step)) * max(0, min(1, 1 + (Q_slow1 - Q_t1 - band))) * max(0, min(1, 1 - (Q_t1 - Q_slow1 - band))), w_min, w_max)` — v2 HYSTERESIS + SPLIT: the boundary targets slow-odds mapping but moves only when the slow clock EXCEEDS the fast by the band (stress confirmation) or falls behind by the band (calm confirmation) — short pumps move price, never allocation.
- `S_t1 = clip(S_t * (1 - rebuild) + (1 - w_t) * (pi_s * order_flow) + rebuild * S_t - r_t, 0, 3)` — Senior: steady fees in, wash-filtered routine draws out (rebuild asymmetric as before).
- `J_t1 = clip(J_t + w_t * (pi_j_t * order_flow) - e_t, 0, 3)` — Junior: carry-floored premiums in (v2), event draws out.
- `r_t = r_rate * max(0, order_flow - M_t)` — v2 WASH FILTER: routine draws index NETTED flow (the tracked manipulator contribution is subtracted) — wash volume's draw cost lands on the washer (netting lineage, third reuse).
- `e_t = e_rate * max(0, Q_t1 - 0.5) * 2 * J_t` — Event draws: odds-linked on the FAST clock (events are fast), bounded by junior.
- `pi_s_t = pi_s` — Senior fee: steady (unchanged).
- `pi_j_t = max(pi_j_floor, min(pi_j_max, k_prem_j * Q_t1))` — v2 CARRY FLOOR: junior never idles below pi_j_floor — the event layer's LPs are paid through calm; the honest carry cost of pre-committed capital.
- `M_t1 = clip(M_t * 0.5 + 0.1 * max(0, min(1, 2 * abs(dX_t))) * max(0, min(1, abs(X_t) - 1)), 0, 3)` — Tracked whale contribution: decays by half each batch, refreshed by stress-side flow (the tracker models observable large-flow presence from the anchor series).

**Parameters:** k_odds ∈ [0.05, 1.5] (default 0.4), ema_span ∈ [2.0, 50.0] (default 6.0), slow_span ∈ [10.0, 100.0] (default 36.0), k_split ∈ [0.0, 1.0] (default 0.5), band ∈ [0.0, 0.5] (default 0.15), w_min ∈ [0.1, 0.5] (default 0.2), w_max ∈ [0.5, 0.95] (default 0.8), w_step ∈ [0.005, 0.2] (default 0.05), pi_s ∈ [0.001, 0.1] (default 0.01), k_prem_j ∈ [0.0, 1.0] (default 0.4), pi_j_max ∈ [0.01, 0.5] (default 0.12), pi_j_floor ∈ [0.0, 0.05] (default 0.008), order_flow ∈ [0.1, 10.0] (default 1.0), r_rate ∈ [0.0, 0.2] (default 0.03), e_rate ∈ [0.0, 0.5] (default 0.1), rebuild ∈ [0.05, 0.5] (default 0.15), shock_load ∈ [0.0, 1.0] (default 0.5)

**Open questions (§13):** Is slow_span=36 with band=0.15 fast enough for real stress curves? The battery's fast-shock scenarios measure the boundary lag honestly.; Does the carry floor change junior LP economics enough to matter (pi_j_floor=0.008 vs typical calm premiums)?; Can the fast/slow split be gamed by oscillating patterns (pump the fast clock repeatedly to harvest pricing while the slow clock stays calm)? The attack would collect premium volatility income while never moving capital — is that harmful or just market-making?; M_t tracking: per-address or per-cluster? Split-address wash flow is the shared honest limit — flagged, not solved.; Statistical confidence: slow_span, band, pi_j_floor are priors; the sweep maps the responsive-yet-seizure-resistant region.

**Critical assumptions:** Whale flow contribution M_t is trackable at the measurement layer (per-address flow accounting — the netting lineage's assumption, third reuse; split-address circumvention remains its honest limit).; Split steering trades boundary responsiveness for seizure resistance: reallocation now needs sustained slow-odds shifts, so genuinely fast stress curves find a lagging boundary — declared as the design's honest tradeoff, not hidden.

## Economic Analysis

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.00 (INFERENCE; confidence 0.80)
- **market_demand**: 6.00 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.60)
- **oracle_feasibility**: 6.50 (INFERENCE; confidence 0.70)
- **security**: 7.00 (INFERENCE; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: The odds-venue composite steer: one manipulation target (Q_t) moves both of the stack's capital decisions — premium income (pi_j_t) and the tranche boundary (w_t) — so the attacker doubles their harve…)
- **game_theory:** 3 attack vector(s) recorded; evidence level INFERENCE
- **security:** 3 attack vector(s) recorded; evidence level INFERENCE
- **oracle:** 3 attack vector(s) recorded; evidence level INFERENCE

## Oracle Design

No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: The odds-venue composite steer: one manipulation target (Q_t) moves both of the stack's capital decisions — premium income (pi_j_t) and the tranche boundary (w_t) — so the attacker doubles their harve…)
- **game_theory:** 3 attack vector(s) recorded; evidence level INFERENCE
- **security:** 3 attack vector(s) recorded; evidence level INFERENCE
- **oracle:** 3 attack vector(s) recorded; evidence level INFERENCE

## Simulation

- **cand-cb4d584867ed-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-cb4d584867ed-montecarlo** (seed 7, sim-0.1.0): mean_final=1000.0, p5_final=1000.0, p95_final=1000.0, failures=0
- **cand-cb4d584867ed-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-cb4d584867ed-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-cb4d584867ed-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1000.0, p5_final=1000.0, p95_final=1000.0, failures=0
- **cand-cb4d584867ed-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: tranche capital structure dynamic; prediction market capital allocation; senior junior tranching insurance; dynamic risk boundary defi; capital stack rebalancing signal
  Class: adjacent_mechanism
- Queries: tranche capital structure dynamic; prediction market capital allocation; senior junior tranching insurance; dynamic risk boundary defi; capital stack rebalancing signal
  Class: adjacent_mechanism
- Queries: tranche capital structure dynamic; prediction market capital allocation; senior junior tranching insurance; dynamic risk boundary defi; capital stack rebalancing signal
  Class: adjacent_mechanism
- Queries: tranche capital structure dynamic; prediction market capital allocation; senior junior tranching insurance; dynamic risk boundary defi; capital stack rebalancing signal
  Class: adjacent_mechanism

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 7.00 (INFERENCE; confidence 0.80)
- **market_demand**: 6.00 (INFERENCE; confidence 0.70)
- **novelty**: 6.00 (INFERENCE; confidence 0.60)
- **oracle_feasibility**: 6.50 (INFERENCE; confidence 0.70)
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
