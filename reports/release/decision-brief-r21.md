# §27 Publication-Decision Brief: Recommended Candidate

Assembled by code from stored evidence only (§2 — no report-writer LLM). Publication is the HUMAN decision (§27); this brief compares the two candidates that decision currently spans. It recommends NOTHING — it measures.

Generated: 2026-09-15T01:04:29

## 1. The Decision Context

The §7 publication decision currently spans two candidates. Where each sits in today's deterministic ranking of 26 stored scored candidate(s) (score descending, name ascending — §19/§7):

- **Separation-Keyed Fee Smoothing Escrow** (`cand-9200b07691c3`) — 6.45, rank 1 of 26, current §7 recommended (rank 1)
- **Demand-Index Escalation Ladder for FX Batches** (`cand-e74d830a9479`) — 6.4, rank 2 of 26, the comparison candidate

The gap is 0.05 on an 11-dimension weighted score — within the noise of bridge-authored research inputs (every candidate's novelty/economist/market dimensions derive from agent-authored reports, §2). The brief's job is to show what the number does NOT: stability of evidence, measured attack surface, and each model's lineage depth.

## 2. Where the 0.05 Comes From (§19 decomposition)

Deterministic scoring, 11 weighted dimensions; missing dimensions imputed at the 5.0 floor (§19).

| Dimension | Weight | Separation-Keyed | Demand-Index | Gap |
|---|---|---|---|---|
| novelty | 10% | 6.00 | 6.00 | +0.00 |
| economic_coherence | 15% | 7.50 | 7.50 | +0.00 |
| game_theory | 10% | 7.50 | 7.50 | +0.00 |
| technical_feasibility | 10% | 5.00\* | 5.00\* | +0.00 |
| oracle_feasibility | 10% | 8.00 | 7.50 | +0.50 |
| security | 10% | 7.00 | 7.00 | +0.00 |
| market_demand | 15% | 6.50 | 6.50 | +0.00 |
| capital_efficiency | 5% | 5.00\* | 5.00\* | +0.00 |
| network_effects | 5% | 5.00\* | 5.00\* | +0.00 |
| communication | 5% | 5.00\* | 5.00\* | +0.00 |
| viral_potential | 5% | 5.00\* | 5.00\* | +0.00 |

\* imputed at the 5.0 floor — no agent-authored evidence stored for that dimension (offline mode). The corpus-wide §2 caveat applies to BOTH candidates' research-derived dimensions equally.

## 3. Measured Attack Surface (§20 battery history)

Every stored census record per candidate, across battery generations (the §21 experiment trail). A flat worst-edge across generations is stability: the same construction measuring clean under every classifier revision the lab shipped. The r22 PARAMETER-CALIBRATION sweep extended the record: every pattern re-run at off-default attacker calibrations (deeper/shallower strikes, more/fewer resonance cycles, faster/slower creep, ± amplitude — 38 runs per candidate) — a bound that holds only at the default calibration is a calibration artifact, not a bound.

**Separation-Keyed Fee Smoothing Escrow** — 3 census record(s):

| Round | Battery | Worst measured edge |
|---|---|---|
| 20 | `attack_patterns_v7_resonance` | 5.1737 |
| 22 | `attack_parameter_sweep` | 32.6375 |
| 33 | `attack_patterns_v8_pin_counterfactual` | 32.6375 |

**Demand-Index Escalation Ladder for FX Batches** — 8 census record(s):

| Round | Battery | Worst measured edge |
|---|---|---|
| 14 | `attack_patterns_v2_crash_park` | 0.3182 |
| 17 | `attack_patterns_v4_drift_creep` | 0.3182 |
| 18 | `attack_patterns_v5_grind_harvest` | 0.3182 |
| 19 | `attack_patterns_v6_window_confirmation` | 0.3182 |
| 20 | `attack_patterns_v7_resonance` | 0.3182 |
| 22 | `attack_parameter_sweep` | 33.2546 |
| 33 | `attack_patterns_v8_pin_counterfactual` | 33.2546 |
| pre | `attack_patterns` | 0.3182 |

All edges are far under the 400 supersede threshold (both candidates classify healthy at every calibration the sweep tried; 0 edges >150 in the whole 76-run sweep). The difference is evidence DEPTH in generations, not measured exposure.

## 4. Residual Attacks on the Final Model Versions (§12)

Attack surfaces the red team NAMED against the final model version, every one of them (r36: the attacking agent's profitability assertion is rendered metadata on each line, never a filter — the reader weighs it, never the code). The §33 claim-matched disclosure: OPEN = never addressed; STILL-PROFITABLE = fix claims it, the final re-attack re-found it anyway.

**Separation-Keyed Fee Smoothing Escrow** (final v3):

- **[OPEN; unprofitable-asserted] long-period alternation partial ride — Period >> 1/lam_c saw-tooth: partial discount on each leg's first fraction; bounded by the band half-width, second-order (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] counter handoff window after a genuine lead — ~1/lam_c-step window after a real lead ends where alternation rides at full key strength before the counter catches up; requires paying the lead's cost first (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] counter handoff window — After a genuine lead (C_t ~0) ends, an immediate saw-tooth rides the separation key at full strength for ~1/lam_c steps before the counter catches up — a first-cycle transient the discount misses; bounded by the symmetric band half-width 0.25 and requires paying the genuine lead's move cost first (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] genuine-lead deadness — Magnitude keying discounts genuine pressure with crafted: retention flat 0.300 through a 3%/step sustained grind (measured) — the buffer never builds under real stress (unspecified, FACT)
- **[OPEN; unprofitable-asserted] genuine-stress buffer failure — Under real sustained stress (the scenario a fee escrow exists for) the counter discounts the retention response: the buffer target stays at base through the stress window — a solvency risk for the escrow's smoothing promise, disclosed as a functionality failure rather than an extraction (unspecified, FACT)
- **[OPEN; unprofitable-asserted] genuine-lead deadness (functionality failure) — The counter pins at 1.0 under any sustained move with fast-EMA movement above 8 (a 3%/step grind measures C_t=1.0 throughout): retention never rises above base on REAL pressure — the escrow never builds its buffer when genuine stress arrives. Not directly attacker P&L, but the mechanism fails its core function under the conditions it exists for (unspecified, FACT)
- **[OPEN; unprofitable-asserted] saw-tooth retention bias — Craft dX with slow negative legs (separation deeply negative, retention pinned at the 0.1 floor) and fast positive legs (separation positive, retention rises to the 0.9 ceiling): the clip band 0.1..0.9 is not symmetric around delta_r=0.3, so the time-average of retention exceeds the base 0.3 — the escrow target inflates on a ZERO-MEAN path (attacker, INFERENCE)
- **[OPEN; unprofitable-asserted] reversion-spread timing — The escrow's lam_e=0.15 convergence makes the target path predictable ~7 steps out; timing fee inflow windows against the convergence spread extracts the spread — bounded by the cap 18 (arbitrageur, HYPOTHESIS)
- **[OPEN; unprofitable-asserted] stale-anchor overcharge window — After genuine breaks the slow anchor trails ~17 steps; retention over-charges through the recovery leg — a disclosed responsiveness gap, no profitable attacker path identified (liquidity_provider, INFERENCE)
- **[OPEN; unprofitable-asserted] observable-path front-running — All keying states are public EMAs of the level: the escrow's target path is predictable ~7 steps ahead; fee-payers can time around high-retention windows, leaving the escrow holding adverse fees (a adverse-selection vector on fee inflow, not on the escrow stock itself) (arbitrageur, HYPOTHESIS)
- **[OPEN; unprofitable-asserted] anchor-drift stale-band hold — After a genuine one-sided regime break, the slow anchor trails for ~1/kappa_s steps; retention keys the stale separation and over-retains through the break's recovery leg — a transient overcharge window proportional to the anchor lag (liquidity_provider, INFERENCE)
- **[OPEN; unprofitable-asserted] sustained-lead retention farming — A whale grinds the level up at a steady +0.5%/step (sub-spike): the fast EMA leads the slow anchor by a stable ~+4%, retention pins near 0.36-0.9, and the buffer target 1000 + 18*r_t inflates ~6 units above anchor — the escrow holds fees the attacker's own grind priced in. The move cost is real but the buffer delta persists as long as the grind does (whale, INFERENCE)
- **[OPEN; unprofitable-asserted] buffer-reversion front-running — The escrow converges to its target at lam_e=0.15: a predictable ~7-step half-life. An attacker who knows the target path can time fee INFLow windows (when target > current escrow, retained inflow is locked at high retention) and fee USE windows (after the target falls) — extracting the convergence spread itself (arbitrageur, HYPOTHESIS)
- **[OPEN; unprofitable-asserted] separation-key oscillation wash — Zero-mean cycling averages the separation key to ~0 — the design's stated immunity. But the clip floor 0.1 makes retention ASYMMETRIC around zero mean: down-legs release to 0.1 while up-legs retain to 0.9, so a 50/50 saw-tooth (slow down, fast up) could bias the time-average of r_t above delta_r (attacker, HYPOTHESIS)

**Demand-Index Escalation Ladder for FX Batches** (final v2):

- **[OPEN; unprofitable-asserted] capped-cycle grinding — Escalation-proportional capped refunds make stuffing a pure deadweight loss. (arbitrageur, INFERENCE)
- **[OPEN; unprofitable-asserted] reserve-floor pressure — Repeated cycles push the reserve toward its floor but cannot breach it; counter-cyclical function degrades gracefully, not catastrophically. (arbitrageur, HYPOTHESIS)
- **[OPEN; profitable-hypothesis] refund-cap exhaustion — Repeated coordinated stuffing across epochs grinds the reserve toward its floor, degrading counter-cyclical function even if each cycle's profit is capped. (arbitrageur, HYPOTHESIS)

## 5. Lineage Depth (§34 improvement history)

- **Separation-Keyed Fee Smoothing Escrow**: 3 model version(s) ([1, 2, 3]), 12 adversarial reports across 4 agents
- **Demand-Index Escalation Ladder for FX Batches**: 2 model version(s) ([1, 2]), 8 adversarial reports across 4 agents

## 6. The Honest Read (for the human decision)

What the evidence supports, without recommendation:

- The Separation-Keyed scores higher (6.45 vs 6.40). Residual honesty is measured under the r36 disclosure (every NAMED surface publishes): Separation-Keyed carries 14 open named surface(s) against its final version; Demand-Index carries 3 open named surface(s) against its final version. Under the pre-r36 filter the successor's surfaces were invisible (every one asserted unprofitable) — the r21 brief's zero-open-residuals comparative claim was an artifact of that filter, §12.
- The ENTIRE 0.05 gap is one dimension: oracle_feasibility (+0.50 at 10% weight). Every other dimension is equal. The gap dimension is agent-authored (bridge provider): Separation-Keyed's stored report was authored after the final model version (the retest loop); Demand-Index's after the final model version (the retest loop) — the rank change rests on agent judgment, not a corpus-level difference. §12: disclosed, not smoothed.
- The incumbent's evidence is DEEPER in CENSUS generations: 8 census record(s) — 6 default-calibration battery generation(s) at flat worst-edge (0.318); 2 calibration-sweep record(s) — measured under every classifier the lab shipped. The successor's evidence is deeper in LOOP EXERCISE: 3 §15 battery runs and a full v3 improve/retest cycle, vs the incumbent's 1. Different kinds of depth; neither is dominated. The r22 parameter-calibration sweep re-measured the incumbent as control: both constructions hold at every off-default attacker calibration tried (successor sweep max 32.6, incumbent 33.3) — and under recalibration the successor's worst edge is the LOWER of the two.
- The 0.05 score gap is smaller than the imputation floor's influence on either side (5 of the head's 11 dimensions are imputed).
- Options the evidence leaves open (all §27-human): publish the Separation-Keyed; publish the Demand-Index; publish both as a comparative package. (The 'accrue stability evidence first' option is discharged — the r22 sweep measured what it asked for.) The lab measures; the human decides.
