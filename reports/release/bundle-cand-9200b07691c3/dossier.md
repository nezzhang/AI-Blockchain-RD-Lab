# Research Dossier: Separation-Keyed Fee Smoothing Escrow

- **Candidate ID:** cand-9200b07691c3
- **Category:** market
- **Overall score:** 6.4500
- **Rank:** 1 (recommended)
- **Status:** finalist

## Executive Summary

**Separation-Keyed Fee Smoothing Escrow** (market) currently holds status **finalist** with an overall deterministic score of **6.4500**. All evidence below is drawn from validated, stored agent and simulation records; nothing in this report is free-form LLM narrative (§2).

## Problem

The superseded predecessor's retention keyed ABSOLUTE realized vol (eta=40 pinned r_t at the 0.9 ceiling through every crafted ramp) while its outflow term was 0.05*sigma weaker — every resonance cycle over-retained inflow monotonically: measured ratchet 285 -> 1321 -> 2143 -> 6479 (linear-unbounded in N, persists under a quiet tail; r20 measured)

## Mechanism

Fast pressure EMA vs slow regime EMA; retention = clip(delta + eta * separation / X, 0.1, 0.9) with the SEPARATION denominated relative; escrow flow symmetric in the same separation key (inflow and outflow caps mirror); clip bounds bracket battery scales.

## Mathematical Model

- `X_t` (input, u): anchor level
- `dX_t` (input, u): level change
- `E_t` (state, u): fee-smoothing escrow level
- `E_t1` (state, u): next escrow level
- `L_f` (state, u): fast pressure EMA
- `L_f1` (state, u): next fast EMA
- `T_s` (state, u): slow regime EMA
- `T_s1` (state, u): next slow EMA
- `r_t` (state, frac): escrow retention fraction
- `r_t1` (state, frac): next retention
- `g_t` (auxiliary, u): signed fast-vs-slow separation
- `C_t` (state, frac): fast-EMA-movement EMA (saw-tooth discount)
- `C_t1` (state, frac): next saw counter
- `G_t` (state, frac): previous separation (lag)
- `G_t1` (state, frac): next lagged separation

- `L_f1 = clip(L_f + kappa_f*(X_t - L_f), 100.0, 10000.0)` — fast pressure EMA of the level — leads on genuine moves; a broad clip so battery extremes never saturate the state
- `T_s1 = clip(T_s + kappa_s*clip(X_t - T_s, -500.0, 500.0), 100.0, 9000.0)` — slow regime EMA with a BOUNDED STEP (±500 — the r19 primitive: battery extremes reach 700k; a value-clipped EMA saturates) — carries sustained moves, washes oscillation
- `g_t = (L_f - T_s) / max(T_s, 1.0)` — SIGNED separation, level-denominated: positive when fast pressure leads the regime (premium inflation), negative on crash legs
- `r_t1 = clip(delta_r + (1.0-C_t)*eta_r*g_t, delta_r - 0.25, delta_r + 0.25)` — retention keys the SIGNED separation with a SYMMETRIC clip band around delta_r (0.3±0.25) and a SAW-TOOTH DISCOUNT: the counter C_t (an EMA of the fast EMA's own movement) fades the separation key on oscillating paths — a zero-mean saw-tooth converges to delta_r at the band CENTER, not the top (the r20 saw-tooth fix; the r12 counter primitive at discount polarity)
- `E_t1 = clip((1.0-lam_e)*E_t + lam_e*(1000.0 + f_c*r_t), 150.0, 20000.0)` — the escrow chases a BOUNDED, REVERTING TARGET (buffer = anchor + cap*retention): size keys CURRENT policy, never the HISTORY of pressure — no free accumulator (the corpus's resonance-healthy designs are all EMAs of bounded targets; the predecessor's integral form E + flows was the ratchet class itself). Converges to the cycle-average of the target under resonance — N-independent by construction; symmetric in both directions (the r18 mirrored-cap discipline, inherited)
- `C_t1 = clip(C_t*(1.0-lam_c) + lam_c*clip(1.0 - 6.0*g_t*G_t, 0.0, 1.0), 0.0, 1.0)` — sign-alternation counter: g_t*G_t < 0 (the separation FLIPPED — saw-tooth) drives the inner term to 1 (counter rises, key discounted); g_t*G_t > 0 (PERSISTED — genuine followed lead) drives it to 0 (counter decays, key rides). SIGN-PERSISTENCE keying, not magnitude: a fast genuine grind also has large fast-EMA movement, so magnitude keying would discount genuine pressure too (caught by the smoke's genuine-lead probe). Keys only the retention discount
- `G_t1 = g_t` — the previous step's separation, carried as a state — lets the counter measure sign PERSISTENCE: g_t*G_t > 0 is a persisting lead/lag (genuine), < 0 is alternation (oscillation/saw-tooth)

**Parameters:** fast_speed ∈ [0.2, 0.9] (default 0.55), slow_speed ∈ [0.02, 0.15] (default 0.06), retention_base ∈ [0.1, 0.5] (default 0.3), retention_gain ∈ [0.05, 0.4] (default 0.15), flow_cap ∈ [5.0, 60.0] (default 18.0), buffer_speed ∈ [0.05, 0.5] (default 0.15), counter_decay ∈ [0.05, 0.5] (default 0.18)

**Open questions (§13):** can sustained genuine pressure (not crafted) hold the separation key high enough to farm retention?

**Critical assumptions:** level observable on-chain; signed separation observable each step

## Economic Analysis

- **novelty**: 6.00 (INFERENCE; confidence 0.80)
- **economic_coherence**: 7.50 (INFERENCE; confidence 0.80)
- **capital_efficiency**: 5.00 (IMPUTED at the 5.0 floor; no authored agent evidence, §19)

## Game Theory

- **Red Team verdict:** survives (strongest attack: Long-period alternation partial ride: a saw-tooth with period well above the counter's time constant spends the first fraction of each leg at partial discount (the EMA discount's own handoff lag) — bu…)
- **game_theory**: 7.50 (INFERENCE; confidence 0.80)
- **game_theory:** 1 attack vector(s) recorded; evidence level INFERENCE
- v3's sign-persistence counter closes both named v2 flaws: there is no magnitude threshold to ride (alternation raises the counter at ANY amplitude — measured slow saw-tooth mean retention 0.300 = base with C_t pinned 1.0), and genuine sustained pressure is no longer discounted (measured 3%/step grin

## Oracle Design

- **oracle_feasibility**: 8.00 (FACT; confidence 0.70)
No external data dependency declared. See Security and adversarial sections for manipulation analysis.

## Security

- **security**: 7.00 (INFERENCE; confidence 0.80)
- **security:** 1 attack vector(s) recorded; evidence level INFERENCE
- The sign-persistence key removes the exploitable boundary entirely: the counter's input g_t*G_t is a sign test, not a magnitude test — no threshold to sit under. Measured: slow saw-tooth 0.300 (= base), duty-cycle saw 0.300, genuine lead 0.428 (response preserved). Residual: the counter is a DISCOUN

## Simulation

- **cand-9200b07691c3-scenarios** (seed 7, sim-0.1.0): results recorded
- **cand-9200b07691c3-montecarlo** (seed 7, sim-0.1.0): mean_final=1005.6810566121621, p5_final=1005.6632140940259, p95_final=1005.6989768920844, failures=0
- **cand-9200b07691c3-sweep** (seed 7, sim-0.1.0): results recorded
- **cand-9200b07691c3-scenarios-v2** (seed 7, sim-0.1.0): results recorded
- **cand-9200b07691c3-montecarlo-v2** (seed 7, sim-0.1.0): mean_final=1005.6207631967238, p5_final=1005.6174266396479, p95_final=1005.6251810227966, failures=0
- **cand-9200b07691c3-sweep-v2** (seed 7, sim-0.1.0): results recorded
- **cand-9200b07691c3-scenarios-v3** (seed 7, sim-0.1.0): results recorded
- **cand-9200b07691c3-montecarlo-v3** (seed 7, sim-0.1.0): mean_final=1005.6340499998557, p5_final=1005.6293537946926, p95_final=1005.6386936934243, failures=0
- **cand-9200b07691c3-sweep-v3** (seed 7, sim-0.1.0): results recorded
- **exp-779ad60c78f9** (seed None, none): results recorded
- **exp-15a351751f2c** (seed None, none): results recorded
- **exp-2240c2647989** (seed None, none): results recorded

All runs are reproducible from the stored seed, parameters, and git commit (§21).

## Historical Analysis

Historical replay ran on synthetic anchor series (Phase 4); real-dataset historical analysis is planned with the data phase.

## Prior Art

- Queries: volatility-indexed retention escrow mechanism; procyclical margin buffer ratchet crypto; countercyclical capital buffer slow anchor keying
  Class: adjacent_mechanism
- Queries: volatility-indexed retention escrow mechanism; procyclical margin buffer ratchet crypto; countercyclical capital buffer slow anchor keying
  Class: adjacent_mechanism

## Competitors

See Prior Art; competitor synthesis pending real research.

## Market

- **market_demand**: 6.50 (INFERENCE; confidence 0.70)
- **network_effects**: 5.00 (IMPUTED at the 5.0 floor; no authored agent evidence, §19)
- **communication**: 5.00 (IMPUTED at the 5.0 floor; no authored agent evidence, §19)
- **viral_potential**: 5.00 (IMPUTED at the 5.0 floor; no authored agent evidence, §19)

## Technical Architecture

- **technical_feasibility**: 5.00 (IMPUTED at the 5.0 floor; no authored agent evidence, §19)
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
