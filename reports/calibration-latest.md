# Calibration Report — known-answer validation of the lab instruments

Generated: 2026-09-22T12:26:35+00:00 · §15 battery steps=120 · §20 attack steps=60 · seed=7

Known mechanisms with established-consensus properties are run through the SAME deterministic batteries real candidates face (§15 scenario battery, §20 attack-pattern battery). The instruments' output is checked against the known ground truth. A failed check is a finding ABOUT THE INSTRUMENT — reported, never hidden (§29).

**Scope:** this suite calibrates the deterministic instruments only. LLM-judged scoring dimensions require blinded fixtures (the judge must not know it is scoring a famous mechanism) — a separate stage.

**OVERALL: CALIBRATION-PASS** — 4/4 fixtures meet every consensus-grounded expectation.

| Fixture | Referent | Consensus | §15 clean | Degenerate | Strongest §20 edge | Checks |
|---|---|---|---|---|---|---|
| PID anchor controller | Classical PID feedback control (textbook control theory) | known_good | 13/13 | 0 | vol_oscillation = 8.3202 (I_t_drawn) | ✅ all pass |
| Utilization-kink rate curve | Compound/Aave-style kinked utilization-rate rule | known_good | 13/13 | 0 | grind_harvest = 0.043385 (R_t_drawn) | ✅ all pass |
| Vol-keyed retention ratchet | Procyclical VaR-style margin/buffer class (BIS/CCP procyclicality literature; the lab's own rejected r16 predecessor) | known_flawed | 13/13 | 0 | resonance = 2362.47 (E_t_ratchet) | ✅ all pass |
| Reflexive mint-burn seigniorage | Terra/Luna-style algorithmic stablecoin (May 2022 collapse) | known_flawed | 13/13 | 0 | wash_flow = 1000 (L_t_drawn) | ✅ all pass |

## PID anchor controller

- **Referent:** Classical PID feedback control (textbook control theory)
- **Consensus class:** known_good
- **Ground truth:** FACT: a PID loop with anti-windup clipping is BIBO-stable — the standard feedback stabilizer of control theory. INFERENCE: no §20 input choreography extracts a standing edge from a bounded controller output, so the strongest measured attack edge must stay under the canonical flaw threshold.
- **§15 battery:** 13/13 clean
- **§20 strongest edge:** vol_oscillation = 8.3202 (I_t_drawn)

| Check | Result | Measured | Ground truth |
|---|---|---|---|
| §15 battery: no hard failures | ✅ | 13/13 clean | FACT: no divisions or unclipped powers — no §15 scenario can produce a numerical failure |
| §15 battery: no degenerate runs | ✅ | 0/13 degenerate | INFERENCE: both states respond to the anchor through the whole window — a live controller, not a saturated one |
| §20 strongest attack edge ≤ 400 | ✅ | strongest: vol_oscillation = 8.3202 (I_t_drawn) | INFERENCE: a fatal-scale attacker edge (≥ the canonical 400) on a bounded stabilizer would be a battery FALSE POSITIVE — the finding this control exists to catch |

## Utilization-kink rate curve

- **Referent:** Compound/Aave-style kinked utilization-rate rule
- **Consensus class:** known_good
- **Ground truth:** FACT: kinked utilization-rate curves are the most deployed DeFi rate mechanism (Compound 2019; Aave), with no consensus fatal flaw in the rate rule itself — the documented risks are oracle and liquidity externalities outside this encoding. INFERENCE: the rate state tracks utilization regime shifts, which the battery's arrival/regime checks must read as following, not extraction.
- **§15 battery:** 13/13 clean
- **§20 strongest edge:** grind_harvest = 0.043385 (R_t_drawn)

| Check | Result | Measured | Ground truth |
|---|---|---|---|
| §15 battery: no hard failures | ✅ | 13/13 clean | FACT: guarded division and full clipping — no numerical failure mode |
| §15 battery: no degenerate runs | ✅ | 0/13 degenerate | INFERENCE: the rate keeps tracking utilization in every regime |
| §20 strongest attack edge ≤ 400 | ✅ | strongest: grind_harvest = 0.043385 (R_t_drawn) | INFERENCE: a fatal-scale edge on the deployed rate-rule shape would be a battery FALSE POSITIVE |

## Vol-keyed retention ratchet

- **Referent:** Procyclical VaR-style margin/buffer class (BIS/CCP procyclicality literature; the lab's own rejected r16 predecessor)
- **Consensus class:** known_flawed
- **Ground truth:** FACT: margin/buffer rules keyed to absolute realized volatility are the documented procyclicality class — protection demand rises with stress and amplifies it (BIS/CCP margin literature); the lab's r16 predecessor of this exact shape was rejected after a measured resonance ratchet (285 -> 6479, linear-unbounded in N). INFERENCE: the §20 resonance choreography must surface the standing accumulation above the canonical flaw threshold.
- **§15 battery:** 13/13 clean
- **§20 strongest edge:** resonance = 2362.47 (E_t_ratchet)

| Check | Result | Measured | Ground truth |
|---|---|---|---|
| §15 battery: no hard failures | ✅ | 13/13 clean | FACT: the flaw is ECONOMIC, not numerical — the model runs clean while the ratchet accumulates |
| §15 battery: no degenerate runs | ✅ | 0/13 degenerate | INFERENCE: all three states exercise dynamics in every scenario |
| §20 resonance edge ≥ 400 | ✅ | resonance = 2362.47 (E_t_ratchet) | FACT: the lab already rejected this class for a measured resonance ratchet — a battery that cannot re-detect it under a known answer has a blind spot |

## Reflexive mint-burn seigniorage

- **Referent:** Terra/Luna-style algorithmic stablecoin (May 2022 collapse)
- **Consensus class:** known_flawed
- **Ground truth:** FACT: Terra/Luna redemptions minted LUNA inversely to its price; a confidence shock through the peg started a self-fueling spiral — supply ~350M to ~6.5T in days, price ~$80 to ~$0.0001 (May 2022), after ~18 months of holding the peg in calm markets. INFERENCE: in this encoding the §15 bank-run shock knocks the price through the arbitrage band and the same feedback runs away (supply >= 5x, price <= 0.5x) while the base scenario stays quiescent.
- **§15 battery:** 13/13 clean
- **§20 strongest edge:** wash_flow = 1000 (L_t_drawn)

| Check | Result | Measured | Ground truth |
|---|---|---|---|
| §15 battery: no hard failures | ✅ | 13/13 clean | INFERENCE: the flaw is ECONOMIC, not numerical — the interpreter runs clean while the economy dies (a clean run is not a healthy mechanism) |
| §15 base: S_t final/initial ≤ 2 | ✅ | 1000 / 1000 = 1 | FACT: the referent held its peg ~18 months in calm markets — the flaw is regime-dependent, so calm scenarios must NOT spiral (supply < 2x) |
| §15 bank_run: S_t final/initial ≥ 5 | ✅ | 1.49841e+09 / 1000 = 1.49841e+06 | FACT: runaway supply expansion is the documented collapse signature — the §15 battery must show it under a bank-run shock (>= 5x; the referent expanded ~4 orders of magnitude) |
| §15 bank_run: P_t final/initial ≤ 0.5 | ✅ | 0.00100263 / 1000 = 1.00263e-06 | FACT: the referent's price collapsed through every floor — under a bank-run shock the battery must show the price broken (<= 0.5x), not a dip-and-recover |

## What this validates — and what it does not

- PASS means: on these known answers, the interpreter, §15 battery, and §20 battery produce output consistent with established consensus. It does NOT prove the instruments catch every flaw class — only the classes these fixtures exercise.
- The fixtures are *encodings* of the referents' core dynamics in the lab's linear-recurrence DSL, not full implementations. Encoding fidelity is stated per fixture as INFERENCE where applicable.
- A FAIL marks an instrument blind spot or over-fire, with the measurement disclosed — the calibration suite's primary product is exactly these findings.
