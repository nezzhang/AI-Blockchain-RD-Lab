# §27 Publication-Decision Brief: Recommended Candidate

Assembled by code from stored evidence only (§2 — no report-writer LLM). Publication is the HUMAN decision (§27); this brief compares the two candidates that decision currently spans. It recommends NOTHING — it measures.

Generated: 2026-09-20T15:02:24

## 1. The Decision Context

The §7 publication decision currently spans two candidates. Where each sits in today's deterministic ranking of 10 stored scored candidate(s) (score descending, name ascending — §19/§7):

- **Separation-Keyed Fee Smoothing Escrow** (`cand-9200b07691c3`) — 6.725, rank 1 of 10, current §7 recommended (rank 1)
- **Demand-Index Escalation Ladder for FX Batches** (`cand-e74d830a9479`) — 6.35, rank 2 of 10, the comparison candidate

The gap is 0.38 on an 11-dimension weighted score — within the noise of bridge-authored research inputs (every candidate's novelty/economist/market dimensions derive from agent-authored reports, §2). The brief's job is to show what the number does NOT: stability of evidence, measured attack surface, and each model's lineage depth.

## 2. Where the 0.38 Comes From (§19 decomposition)

Deterministic scoring, 11 weighted dimensions; missing dimensions imputed at the 5.0 floor (§19).

| Dimension | Weight | Separation-Keyed | Demand-Index | Gap |
|---|---|---|---|---|
| novelty | 10% | 6.00 | 6.00 | +0.00 |
| economic_coherence | 15% | 7.50 | 7.50 | +0.00 |
| game_theory | 10% | 7.50 | 7.50 | +0.00 |
| technical_feasibility | 10% | 7.00 | 7.00 | +0.00 |
| oracle_feasibility | 10% | 8.00 | 5.00\* | +3.00 |
| security | 10% | 7.00 | 5.00\* | +2.00 |
| market_demand | 15% | 6.50 | 6.50 | +0.00 |
| capital_efficiency | 5% | 5.50 | 6.00 | -0.50 |
| network_effects | 5% | 6.00 | 6.00 | +0.00 |
| communication | 5% | 5.50 | 6.50 | -1.00 |
| viral_potential | 5% | 4.50 | 5.50 | -1.00 |

\* imputed at the 5.0 floor — no agent-authored evidence stored for that dimension (offline mode). The corpus-wide §2 caveat applies to BOTH candidates' research-derived dimensions equally.

## 3. Measured Attack Surface (§20 battery history)

Every stored census record per candidate, across battery generations (the §21 experiment trail). A flat worst-edge across generations is stability: the same construction measuring clean under every classifier revision the lab shipped. The r22 PARAMETER-CALIBRATION sweep extended the record: every pattern re-run at off-default attacker calibrations (deeper/shallower strikes, more/fewer resonance cycles, faster/slower creep, ± amplitude — 38 runs per candidate) — a bound that holds only at the default calibration is a calibration artifact, not a bound.

**Separation-Keyed Fee Smoothing Escrow** — 4 census record(s):

| Round | Battery | Worst measured edge |
|---|---|---|
| 20 | `attack_patterns_v7_resonance` | 5.1737 |
| 22 | `attack_parameter_sweep` | 32.6375 |
| 33 | `attack_patterns_v8_pin_counterfactual` | 32.6375 |
| 41 | `supply_attack_patterns_v1` | 60.0000 |

**Demand-Index Escalation Ladder for FX Batches** — 0 census record(s):

| Round | Battery | Worst measured edge |
|---|---|---|

All edges are far under the 400 supersede threshold (both candidates classify healthy at every calibration the sweep tried; 0 edges >150 in the whole 38-run sweep). The difference is evidence DEPTH in generations, not measured exposure.

## 4. Residual Attacks on the Final Model Versions (§12)

Attack surfaces the red team NAMED against the final model version, every one of them (r36: the attacking agent's profitability assertion is rendered metadata on each line, never a filter — the reader weighs it, never the code). The §33 claim-matched disclosure: OPEN = never addressed; STILL-PROFITABLE = fix claims it, the final re-attack re-found it anyway.

**Separation-Keyed Fee Smoothing Escrow** (final v3):

- **[OPEN; unprofitable-asserted] sustained-lead retention farming — A whale grinds the level up at a steady +0.5%/step (sub-spike): the fast EMA leads the slow anchor by a stable ~+4%, retention pins near 0.36-0.9, and the buffer target 1000 + 18*r_t inflates ~6 units above anchor — the escrow holds fees the attacker's own grind priced in. The move cost is real but the buffer delta persists as long as the grind does (whale, INFERENCE)
- **[OPEN; unprofitable-asserted] buffer-reversion front-running — The escrow converges to its target at lam_e=0.15: a predictable ~7-step half-life. An attacker who knows the target path can time fee INFLow windows (when target > current escrow, retained inflow is locked at high retention) and fee USE windows (after the target falls) — extracting the convergence spread itself (arbitrageur, HYPOTHESIS)
- **[OPEN; unprofitable-asserted] separation-key oscillation wash — Zero-mean cycling averages the separation key to ~0 — the design's stated immunity. But the clip floor 0.1 makes retention ASYMMETRIC around zero mean: down-legs release to 0.1 while up-legs retain to 0.9, so a 50/50 saw-tooth (slow down, fast up) could bias the time-average of r_t above delta_r (attacker, HYPOTHESIS)
- **[OPEN; profitable-hypothesis] saw-tooth retention bias — Slow-down/fast-up crafted cycles: down legs pin retention at 0.1, up legs ride toward 0.9; the time-average of retention exceeds 0.3 on a zero-mean path, inflating the buffer target (1000 + 18*r_t) persistently while the cycling continues (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] observable-path front-running — All keying states are public EMAs of the level: the escrow's target path is predictable ~7 steps ahead; fee-payers can time around high-retention windows, leaving the escrow holding adverse fees (a adverse-selection vector on fee inflow, not on the escrow stock itself) (arbitrageur, HYPOTHESIS)
- **[OPEN; unprofitable-asserted] anchor-drift stale-band hold — After a genuine one-sided regime break, the slow anchor trails for ~1/kappa_s steps; retention keys the stale separation and over-retains through the break's recovery leg — a transient overcharge window proportional to the anchor lag (liquidity_provider, INFERENCE)
- **[OPEN; unprofitable-asserted] reversion-spread timing — The escrow's lam_e=0.15 convergence makes the target path predictable ~7 steps out; timing fee inflow windows against the convergence spread extracts the spread — bounded by the cap 18 (arbitrageur, HYPOTHESIS)
- **[OPEN; unprofitable-asserted] stale-anchor overcharge window — After genuine breaks the slow anchor trails ~17 steps; retention over-charges through the recovery leg — a disclosed responsiveness gap, no profitable attacker path identified (liquidity_provider, INFERENCE)
- **[OPEN; profitable-hypothesis] slow saw-tooth under the counter threshold — Craft a zero-mean saw-tooth with small per-step moves (fast-EMA movement < 8, the counter's normalization): C_t stays ~0, the separation key rides every alternation, and the symmetric band still lets up-legs push retention +0.25 while down-legs pull only -0.25 — the average can exceed base whenever the saw-tooth's positive legs are longer-lived than its negative legs (duty-cycle bias within the band) (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] genuine-lead deadness (functionality failure) — The counter pins at 1.0 under any sustained move with fast-EMA movement above 8 (a 3%/step grind measures C_t=1.0 throughout): retention never rises above base on REAL pressure — the escrow never builds its buffer when genuine stress arrives. Not directly attacker P&L, but the mechanism fails its core function under the conditions it exists for (unspecified, FACT)
- **[OPEN; profitable-hypothesis] counter-threshold boundary riding — Saw-teeth calibrated to keep |kappa_f*(X-L_f)| just under 8: the counter reads ~0 and the separation key rides — the bias the counter was installed to remove returns at a smaller amplitude (bounded by the band half-width 0.25 and the duty-cycle asymmetry a saw-tooth can carry within the threshold) (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] genuine-stress buffer failure — Under real sustained stress (the scenario a fee escrow exists for) the counter discounts the retention response: the buffer target stays at base through the stress window — a solvency risk for the escrow's smoothing promise, disclosed as a functionality failure rather than an extraction (unspecified, FACT)
- **[OPEN; unprofitable-asserted] genuine-lead deadness — Magnitude keying discounts genuine pressure with crafted: retention flat 0.300 through a 3%/step sustained grind (measured) — the buffer never builds under real stress (unspecified, FACT)
- **[OPEN; unprofitable-asserted] counter handoff window — After a genuine lead (C_t ~0) ends, an immediate saw-tooth rides the separation key at full strength for ~1/lam_c steps before the counter catches up — a first-cycle transient the discount misses; bounded by the symmetric band half-width 0.25 and requires paying the genuine lead's move cost first (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] long-period alternation partial ride — A saw-tooth with period >> 1/lam_c (~5 steps) lets the counter partially decay during each long leg, so the first portion of every leg rides at partial discount — the average discount is < 1 and part of each leg's separation keys retention; bounded by the symmetric band (±0.25 around base) and second-order (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] counter handoff window after a genuine lead — ~1/lam_c-step window after a real lead ends where alternation rides at full key strength before the counter catches up; requires paying the lead's cost first (attacker, INFERENCE)

**Demand-Index Escalation Ladder for FX Batches** (final v2):

- no named attack surface against the final version (the searched attack space, not an absolute claim, §12)

## 5. Lineage Depth (§34 improvement history)

- **Separation-Keyed Fee Smoothing Escrow**: 1 model version(s) ([3]), 12 adversarial reports across 4 agents
- **Demand-Index Escalation Ladder for FX Batches**: 2 model version(s) ([1, 2]), 0 adversarial reports across 0 agents

## 6. The Honest Read (for the human decision)

What the evidence supports, without recommendation:

- The Separation-Keyed scores higher (6.72 vs 6.35). Residual honesty is measured under the r36 disclosure (every NAMED surface publishes): Separation-Keyed carries 16 open named surface(s) against its final version; Demand-Index carries 0 open named surface(s) against its final version. Under the pre-r36 filter the successor's surfaces were invisible (every one asserted unprofitable) — the r21 brief's zero-open-residuals comparative claim was an artifact of that filter, §12.
- The 0.38 gap spreads over 5 dimensions (oracle_feasibility (+3.00 at 10%), security (+2.00 at 10%), capital_efficiency (-0.50 at 5%), communication (-1.00 at 5%), viral_potential (-1.00 at 5%); the largest carrier oracle_feasibility holds 48% of the weighted delta) — disclosed, not smoothed, §12.
- The incumbent's evidence is DEEPER in CENSUS generations: no census records — measured under every classifier the lab shipped. The successor's evidence is deeper in LOOP EXERCISE: 1 §15 battery runs and a full v3 improve/retest cycle, vs the incumbent's 0. Different kinds of depth; neither is dominated. The r22 parameter-calibration sweep re-measured the incumbent as control: both constructions hold at every off-default attacker calibration tried (successor sweep max 32.6, incumbent no sweep record).
- The 0.38 score gap is smaller than the imputation floor's influence on either side (0 of the head's 11 dimensions are imputed).
- Options the evidence leaves open (all §27-human): publish the Separation-Keyed; publish the Demand-Index; publish both as a comparative package. (The 'accrue stability evidence first' option remains OPEN — no stored calibration sweep for both candidates.) The lab measures; the human decides.
