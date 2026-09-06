# Research Dossier: Tranche-Segmented Settlement Guarantee Stack

- **Candidate ID:** cand-5d41cd41f68d
- **Category:** settlement guarantees
- **Overall score:** 5.6000
- **Rank:** 4
- **Status:** finalist

## Executive Summary

**Tranche-Segmented Settlement Guarantee Stack** (settlement guarantees) currently holds status **finalist** with an overall deterministic score of **5.6000**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

Settlement guarantee pools concentrate risk: first-loss tranches absorb all shocks and senior capital earns un-risked yield

## Mechanism

Guarantee capital is segmented into tranches with risk-weighted collateral; a solvency check compares tranche capitalization against queued settlement exposure and dynamically adjusts the guarantee fee each tranche charges, so risk migrates to the tranches priced to hold it

## Mathematical Model

- `X_t` (input, unit): anchor price level (~1000)
- `dX_t` (input, unit): anchor change that step
- `Q_t` (state, unit): queued settlement exposure
- `Q_t1` (state, unit): next queued exposure
- `F_t` (state, unit): per-batch guarantee fee
- `F_t1` (state, unit): next guarantee fee

- `Q_t1 = clip(Q_t * (1 + phi) + 12.0 * dX_t / X_t, 100.0, cap)` — queued exposure drifts up and responds to anchor moves, floored and capped
- `F_t1 = clip(f0 + psi * (Q_t1 - 100.0), 5.0, 80.0)` — guarantee fee scales with exposure LEVEL above the floor — senior free-riding and queue spam both pay proportionally

**Parameters:** phi ∈ [0.001, 0.05] (default 0.006), psi ∈ [0.001, 0.2] (default 0.03), cap ∈ [100.0, 20000.0] (default 2500.0), f0 ∈ [1.0, 60.0] (default 10.0)

**Open questions (§13):** should tranche seniority multiply the level-based fee explicitly?

**Critical assumptions:** queued exposure is measurable each batch; fee pressure is linear in relative exposure growth

## Economic Analysis

- **game_theory**: 7.00 (HYPOTHESIS; confidence 0.80)
- **oracle_feasibility**: 7.50 (HYPOTHESIS; confidence 0.70)
- **security**: 6.50 (HYPOTHESIS; confidence 0.80)

## Game Theory

- **Red Team verdict:** vulnerable (strongest attack: Senior tranche free-riding: guarantee fees price exposure growth, not exposure level or tranche risk, so senior capital harvests fees and exits before slowly accumulated exposure (Q_t toward cap 2500)…)
- **game_theory:** 2 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 2 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Oracle Design

No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **Red Team verdict:** vulnerable (strongest attack: Senior tranche free-riding: guarantee fees price exposure growth, not exposure level or tranche risk, so senior capital harvests fees and exits before slowly accumulated exposure (Q_t toward cap 2500)…)
- **game_theory:** 2 attack vector(s) recorded; evidence level HYPOTHESIS
- **security:** 2 attack vector(s) recorded; evidence level HYPOTHESIS
- **oracle:** 1 attack vector(s) recorded; evidence level HYPOTHESIS

## Simulation

- **cand-5d41cd41f68d-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-5d41cd41f68d-montecarlo** (seed 7, sim-0.1.0): mean_final=1429.3802870523518, p5_final=1428.8629563770494, p95_final=1429.7301953157053, failures=0
- **cand-5d41cd41f68d-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-5d41cd41f68d-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-5d41cd41f68d-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1429.4464606993258, p5_final=1428.9814117072945, p95_final=1429.8674090917502, failures=0
- **cand-5d41cd41f68d-sweep-v2** (seed 7, sim-0.1.0): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

No prior-art research recorded yet (run `lab research`).

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **game_theory**: 7.00 (HYPOTHESIS; confidence 0.80)
- **oracle_feasibility**: 7.50 (HYPOTHESIS; confidence 0.70)
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
