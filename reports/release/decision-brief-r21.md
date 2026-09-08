# §27 Publication-Decision Brief: Recommended Candidate

Assembled by code from stored evidence only (§2 — no report-writer LLM). Publication is the HUMAN decision (§27); this brief compares the two candidates that decision currently spans. It recommends NOTHING — it measures.

Generated: 2026-09-08T12:53:34+00:00

## 1. The Decision Context

The §7 recommended candidate changed in round 20 for the first time since r15. The two candidates the human publication decision spans:

- **Separation-Keyed Fee Smoothing Escrow** (`cand-9200b07691c3`) — 6.45, current §7 recommended (rank 1)
- **Demand-Index Escalation Ladder for FX Batches** (`cand-e74d830a9479`) — 6.4, the comparison candidate

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

Every stored census record per candidate, across battery generations (the §21 experiment trail). A flat worst-edge across generations is stability: the same construction measuring clean under every classifier revision the lab shipped. The r22 PARAMETER-CALIBRATION sweep extended the record: every pattern re-run at off-default attacker calibrations (deeper/shallower strikes, more/fewer resonance cycles, faster/slower creep, ± amplitude — 27 runs per candidate) — a bound that holds only at the default calibration is a calibration artifact, not a bound.

**Separation-Keyed Fee Smoothing Escrow** — 6 census record(s):

| Round | Battery | Worst measured edge |
|---|---|---|
| 20 | `attack_patterns_v7_resonance` | 5.1737 |
| 22 | `attack_parameter_sweep` | 32.6375 |
| 22 | `attack_parameter_sweep` | 32.6375 |
| 22 | `attack_parameter_sweep` | 32.6375 |
| 22 | `attack_parameter_sweep` | 32.6375 |
| 22 | `attack_parameter_sweep` | 32.6375 |

**Demand-Index Escalation Ladder for FX Batches** — 11 census record(s):

| Round | Battery | Worst measured edge |
|---|---|---|
| 14 | `attack_patterns_v2_crash_park` | 0.3182 |
| 17 | `attack_patterns_v4_drift_creep` | 0.3182 |
| 18 | `attack_patterns_v5_grind_harvest` | 0.3182 |
| 19 | `attack_patterns_v6_window_confirmation` | 0.3182 |
| 20 | `attack_patterns_v7_resonance` | 0.3182 |
| 22 | `attack_parameter_sweep` | 63.8580 |
| 22 | `attack_parameter_sweep` | 33.2546 |
| 22 | `attack_parameter_sweep` | 33.2546 |
| 22 | `attack_parameter_sweep` | 33.2546 |
| 22 | `attack_parameter_sweep` | 33.2546 |
| pre | `attack_patterns` | 0.0000 |

All edges are far under the 400 supersede threshold (both candidates classify healthy at every calibration the sweep tried; zero edges >150 in the whole 54-run sweep). The difference is evidence DEPTH in generations, not measured exposure.

## 4. Residual Attacks on the Final Model Versions (§12)

Profitable vectors the final model version does not fully close (the §33 claim-matched disclosure; OPEN = never addressed; STILL-PROFITABLE = fix claims it, the final re-attack re-found it anyway).

**Separation-Keyed Fee Smoothing Escrow** (final v3):

- none open against the final version (the searched attack space, not an absolute claim, §12)

**Demand-Index Escalation Ladder for FX Batches** (final v2):

- **[OPEN]** refund-cap exhaustion — Repeated coordinated stuffing across epochs grinds the reserve toward its floor, degrading counter-cyclical function even if each cycle's profit is capped. (arbitrageur, HYPOTHESIS)

## 5. Lineage Depth (§34 improvement history)

- **Separation-Keyed Fee Smoothing Escrow**: 3 model version(s) ([1, 2, 3]), 12 adversarial reports across 4 agents
- **Demand-Index Escalation Ladder for FX Batches**: 2 model version(s) ([1, 2]), 8 adversarial reports across 4 agents

## 6. The Honest Read (for the human decision)

What the evidence supports, without recommendation:

- The successor scores higher (6.45 vs 6.40) and carries zero open residuals against its final version; the incumbent carries one OPEN residual (refund-cap exhaustion).
- The ENTIRE 0.05 gap is one dimension: oracle_feasibility (+0.50 at 10% weight). Every other dimension is equal. That dimension is a bridge-authored OracleReport (the successor's was authored in r20's retest loop, the incumbent's in its original era) — the rank change rests on one agent judgment, not a corpus-level difference. §12: disclosed, not smoothed.
- The incumbent's evidence is DEEPER in CENSUS generations: five battery revisions of flat worst-edge (0.318) — measured stability under every classifier the lab shipped. The successor's evidence is deeper in LOOP EXERCISE: three §15 battery runs and a full v1→v3 improve/retest cycle, vs the incumbent's one run. Different kinds of depth; neither is dominated. The r22 parameter-calibration sweep ADDED the successor's second generation and re-measured the incumbent as control: both constructions hold at every off-default attacker calibration tried (successor sweep max 32.6, incumbent 63.9, zero edges >150 in 54 runs) — and under recalibration the successor's worst edge is the LOWER of the two. The stability question the r21 brief flagged is now measured: closed in the successor's favor.
- The 0.05 score gap is smaller than the imputation floor's influence on either side (5 of the successor's 11 dimensions are imputed).
- Options the evidence leaves open (all §27-human): publish the successor; publish the incumbent; publish both as a comparative package. (The 'accrue stability evidence first' option is now discharged — the r22 sweep measured what it asked for.) The lab measures; the human decides.
