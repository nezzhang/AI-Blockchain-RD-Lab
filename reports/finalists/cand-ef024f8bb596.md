# Research Dossier: Escrowed Batch-Clearing Insurance Pool

- **Candidate ID:** cand-ef024f8bb596
- **Category:** decentralized fx
- **Overall score:** 5.7000
- **Rank:** 1 (recommended)
- **Status:** finalist

## Executive Summary

**Escrowed Batch-Clearing Insurance Pool** (decentralized fx) currently holds status **finalist** with an overall deterministic score of **5.7000**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Batch auctions depend on a solver oligopoly: few solvers, each with discretion over which valid solution to submit. If the winning solver withholds (spike-window strike analog) or submits a self-dealing solution, settlement stalls or skews — and concentration makes this worse exactly when it matters.

## Mechanism

Solver concentration (EMA of distinct bonded solvers) drives an insurance premium on every batch order; the pooled premiums capitalize a fallback solver that guarantees batch settlement when the primary solver fails, withholds, or commits optimality fraud. Rising concentration makes insurance dearer — a live fragility price — while the fallback's existence makes withholding unprofitable: a striking solver does not stop settlement, it only donates its bond to the pool that replaces it.

## Mathematical Model

- `X_t` (input, dimensionless): Exogenous stress series: negative = solver concentration rising.
- `n_t` (state, count): Raw count of distinct bonded solvers this batch.
- `N_t` (state, count): EMA-smoothed distinct bonded solvers (the fragility signal).
- `pi_t` (state, dimensionless): Per-order insurance premium rate.
- `P_t` (state, dimensionless): Pool inventory (shared layer).
- `G_t` (state, dimensionless): This corridor's pool partition (corridor-backed guarantee).
- `g_t` (state, dimensionless): Measured solution gouge fraction (spread vs attainable, 0 = honest).
- `f_t` (state, dimensionless): Fallback activation (failure-triggered).
- `n_t1` (state, count): Next-batch raw solver count.
- `N_t1` (state, count): Next-batch EMA solver count.
- `pi_t1` (state, dimensionless): Next-batch premium rate.
- `P_t1` (state, dimensionless): Next-batch shared pool inventory.
- `G_t1` (state, dimensionless): Next-batch corridor partition.
- `g_t1` (state, dimensionless): Next-batch measured gouge fraction.
- `b_t` (state, dimensionless): Incoming solver performance bonds this batch.
- `f_t1` (state, dimensionless): Next-batch fallback activation indicator.

- `n_t1 = max(1, n_t - k_exit * max(0, -shock_load * X_t))` — Solver count floors at 1 (monopoly edge exercised by the battery).
- `N_t1 = N_t + (n_t1 - N_t) * (2 / (1 + ema_span))` — EMA-smoothed solver count (premium lead time).
- `pi_t1 = min(pi_max, k_premium * max(0, 1 - N_t1 / n_healthy))` — Premium rises with fragility; the cap is solvency-tied (see solvency_tie equation).
- `g_t1 = k_gouge * max(0, 1 - (N_t1 - 1) / max(1, n_healthy - 1))` — Measured gouge: under concentration the settling solver degrades spread vs attainable — the quality audit reads it as a fraction (0 at healthy, max at monopoly).
- `P_t1 = P_t + pi_t * order_flow + b_t * bond_rate + forfeit_rate * g_t1 * bond_rate` — Pool income (v2): premiums + bonds + GRADUATED FORFEIT — the measured gouge forfeits bond fractionally as it occurs, so harvesting below the failure line pays the pool continuously (the free-riding band collapses).
- `f_t1 = max(0, min(1, fail_prob * max(0, 1 - (N_t1 - 1) / n_healthy)))` — Fallback activation (failure-triggered, unchanged).
- `G_t1 = max(0, G_t - f_t1 * fallback_cost) + max(0, f_t1 * fallback_cost - G_t) * 0` — Corridor partition (v2): the fallback draws from the corridor's OWN partition first; the remainder (zero here when the partition covers it) escalates to the shared layer.
- `P_t1 = max(0, P_t1 - max(0, f_t1 * fallback_cost - G_t))` — Shared layer (v2): only the UNCOVERED remainder of a fallback draw hits the shared pool — simultaneous failures cannot drain one corridor's guarantee to rescue another (aggregate draw is structurally bounded by partitions).
- `pi_t1 = pi_t1 * min(1, max(0, (G_t + P_t) / (cov_ratio * fallback_cost)))` — Solvency tie (v2): the premium cap holds only while coverage holds — when the pool's coverage ratio falls below cov_ratio, the cap releases and premiums rise honestly (retention is never traded against insolvency silently).
- `G_t1 = G_t1 + 0.5 * pi_t * order_flow` — Corridor partitions receive half the premium income (the corridor backs its own guarantee); the shared layer receives the other half.

**Parameters:** k_exit ∈ [0.05, 1.5] (default 0.4), ema_span ∈ [2.0, 50.0] (default 10.0), k_premium ∈ [0.0, 1.0] (default 0.4), n_healthy ∈ [2.0, 20.0] (default 6.0), pi_max ∈ [0.01, 0.5] (default 0.1), order_flow ∈ [0.1, 10.0] (default 1.0), bond_rate ∈ [0.0, 1.0] (default 0.2), fail_prob ∈ [0.0, 1.0] (default 0.1), fallback_cost ∈ [0.1, 2.0] (default 0.5), k_gouge ∈ [0.0, 1.0] (default 0.5), forfeit_rate ∈ [0.0, 2.0] (default 1.0), cov_ratio ∈ [1.0, 5.0] (default 2.0), shock_load ∈ [0.0, 1.0] (default 0.5)

**Open questions (§13):** Does forfeit_rate = 1.0 actually price out the monopolist at the audit's measurement noise, or only at zero noise? The sweep maps profitability vs noise floor.; The audit boundary (what spread counts as attainable) is itself a straddle surface — graduated forfeit keeps the profitable side small, but how small?; Is cov_ratio = 2.0 the right solvency tie, or does releasing the cap under stress push fragile corridors out (adverse selection) anyway?; Partition sizing: what fraction of premium income backs the corridor vs shares into the common layer?; The waterfall's fixed rules must themselves be attack-audited (rule-bound is not attack-free — a deterministic rule has a profitable side too).; Statistical confidence: k_gouge, forfeit_rate, cov_ratio are priors; the sweep maps the solvent-and-unprofitable-to-attack region.

**Critical assumptions:** The quality audit (spread vs attainable) is computable from batch data by deterministic code — the audit's own boundary is the honest residual gray zone.; The fallback waterfall is fixed in code (no solution choice) and bonded at bond_rate — the relocated discretion surface is removed, verified by rule, not assumption.

## Economic Analysis

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 5.00 (HYPOTHESIS; confidence 0.80)
- **novelty**: 6.00 (INFERENCE; confidence 0.60)
- **oracle_feasibility**: 8.50 (FACT; confidence 0.70)
- **security**: 4.50 (HYPOTHESIS; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: Monopoly gouging below the failure line: the fallback guarantee triggers only on solver FAILURE, so the last solvent solver under concentration (n=1) maximizes extraction while settling valid-but-self…)
- **game_theory:** 3 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 3 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level FACT

## Oracle Design

No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: Monopoly gouging below the failure line: the fallback guarantee triggers only on solver FAILURE, so the last solvent solver under concentration (n=1) maximizes extraction while settling valid-but-self…)
- **game_theory:** 3 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 3 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level FACT

## Simulation

- **cand-ef024f8bb596-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-ef024f8bb596-montecarlo** (seed 7, sim-0.1.0): mean_final=1000.0, p5_final=1000.0, p95_final=1000.0, failures=0
- **cand-ef024f8bb596-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-ef024f8bb596-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-ef024f8bb596-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1000.0, p5_final=1000.0, p95_final=1000.0, failures=0
- **cand-ef024f8bb596-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: batch auction solver insurance; solver of last resort; solver concentration risk pricing; fallback auction mechanism defi; performance bond solver market
  Class: adjacent_mechanism
- Queries: batch auction solver insurance; solver of last resort; solver concentration risk pricing; fallback auction mechanism defi; performance bond solver market
  Class: adjacent_mechanism
- Queries: batch auction solver insurance; solver of last resort; solver concentration risk pricing; fallback auction mechanism defi; performance bond solver market
  Class: adjacent_mechanism
- Queries: batch auction solver insurance; solver of last resort; solver concentration risk pricing; fallback auction mechanism defi; performance bond solver market
  Class: adjacent_mechanism

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **economic_coherence**: 7.00 (INFERENCE; confidence 0.80)
- **game_theory**: 5.00 (HYPOTHESIS; confidence 0.80)
- **novelty**: 6.00 (INFERENCE; confidence 0.60)
- **oracle_feasibility**: 8.50 (FACT; confidence 0.70)
- **security**: 4.50 (HYPOTHESIS; confidence 0.80)

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
