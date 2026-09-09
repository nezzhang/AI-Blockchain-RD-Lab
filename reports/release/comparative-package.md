# §27 Comparative Publication Package (both options)

The third §27 option: publish BOTH decision candidates. Assembled by code from stored evidence only (§2). This document presents the two mechanisms side by side and the evidence for each; it RANKS NOTHING — the comparative score table is the §19 deterministic output, the census tables are the §21 measurement trail, and the §27 call stays with the human (§28/§41: the lab stages, the human posts).

---

# Part A — The Comparative Decision Brief

# §27 Publication-Decision Brief: Recommended Candidate

Assembled by code from stored evidence only (§2 — no report-writer LLM). Publication is the HUMAN decision (§27); this brief compares the two candidates that decision currently spans. It recommends NOTHING — it measures.

Generated: 2026-09-09T03:04:33+00:00

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

**Separation-Keyed Fee Smoothing Escrow** — 2 census record(s):

| Round | Battery | Worst measured edge |
|---|---|---|
| 20 | `attack_patterns_v7_resonance` | 5.1737 |
| 22 | `attack_parameter_sweep` | 32.6375 |

**Demand-Index Escalation Ladder for FX Batches** — 7 census record(s):

| Round | Battery | Worst measured edge |
|---|---|---|
| 14 | `attack_patterns_v2_crash_park` | 0.3182 |
| 17 | `attack_patterns_v4_drift_creep` | 0.3182 |
| 18 | `attack_patterns_v5_grind_harvest` | 0.3182 |
| 19 | `attack_patterns_v6_window_confirmation` | 0.3182 |
| 20 | `attack_patterns_v7_resonance` | 0.3182 |
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


---

# Part B — §27 Release Package: the successor (§7 rank 1)

# Release Package: Separation-Keyed Fee Smoothing Escrow

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-09T03:04:32+00:00
Candidate: `cand-9200b07691c3` (§7 recommended, rank 1)

## 1. Publication Readiness

- Deterministic overall score: **6.45** (§19, 11 dimensions)
- Model versions stored: [1, 2, 3] (append-only, §21)
- §15 battery: ✅ 13/13 scenarios clean
- Monte Carlo: 0 failures / 20 trials

## 2. The Mechanism (as recorded)

**Problem.** The superseded predecessor's retention keyed ABSOLUTE realized vol (eta=40 pinned r_t at the 0.9 ceiling through every crafted ramp) while its outflow term was 0.05*sigma weaker — every resonance cycle over-retained inflow monotonically: measured ratchet 285 -> 1321 -> 2143 -> 6479 (linear-unbounded in N, persists under a quiet tail; r20 measured)

**Core causal chain.** Fast pressure EMA vs slow regime EMA; retention = clip(delta + eta * separation / X, 0.1, 0.9) with the SEPARATION denominated relative; escrow flow symmetric in the same separation key (inflow and outflow caps mirror); clip bounds bracket battery scales.

## 3. Evidence Trail

- Prior-art searches recorded: 2 (queries + sources stored, §12)
- Adversarial reports: 12 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: 2 patched version(s) stored; the final version v3 was re-attacked with the patched model in the adversarial prompt (§34 retest)

## 4. Residual Attacks Disclosure (§12 honesty)

No profitable attack remains unaddressed by the final model version. This is a statement about the searched attack space, not an absolute claim of security (§12: no absolute claims).

### 4b. Measured Attack-Pattern Bounds (§20)

Deterministic bounds from the §20 attack-pattern battery (60-step window, matched base runs).
- **vol_oscillation**: attacker edge **+0.9940** on `C_t_drawn` vs a matched base run
- **wash_flow**: attacker edge **+5.1737** on `L_f_drawn` vs a matched base run
- **pump_unwind**: attacker edge **+0.9999** on `C_t_drawn` vs a matched base run
- **shock_timing**: attacker edge **+0.4017** on `C_t_drawn` vs a matched base run
- **crash_park**: attacker edge **+0.5175** on `G_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +600.0, `T_s` +541.4, `r_t` +0.1); re-basing in transit (arriving or at design offset): `C_t` +0.9
  - heal disclosure: after the one-shot move, protection `E_t` retains 100% of peak while the level stays moved
- **drift_creep**: attacker edge **+0.0300** on `C_t_drawn` vs a matched base run; drift responsiveness lag: `E_t` +330.3, `L_f` +11.7, `T_s` +98.0 (disclosed design lag, not an extraction)
- **grind_harvest**: attacker edge **+0.4915** on `G_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +535.4, `T_s` +421.2, `r_t` +0.1); re-basing in transit (arriving or at design offset): `C_t` +0.9
  - heal disclosure: after the one-shot move, protection `E_t` retains 100% of peak while the level stays moved
- **resonance**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `L_f` re-basing (+0.0 in motion at window end), `T_s` re-basing (+8.4 in motion at window end), `E_t_ratchet` re-basing (+0.0 in motion at window end), `L_f_ratchet` re-basing (+0.0 in motion at window end), `T_s_ratchet` re-basing (+8.4 in motion at window end), `r_t_ratchet` re-basing (+0.0 in motion at window end), `C_t_ratchet` re-basing (+0.0 in motion at window end), `G_t_ratchet` re-basing (+0.0 in motion at window end)
- **vol_oscillation @amplitude=0.02**: attacker edge **+0.1187** on `C_t_drawn` vs a matched base run
- **vol_oscillation @amplitude=0.1**: attacker edge **+0.9999** on `C_t_drawn` vs a matched base run
- **wash_flow @wash_level=0.01**: attacker edge **+0.0023** on `G_t_drawn` vs a matched base run
- **wash_flow @wash_level=0.04**: attacker edge **+32.6375** on `L_f_drawn` vs a matched base run
- **shock_timing @lag_fraction=0.1**: attacker edge **+0.1862** on `C_t_drawn` vs a matched base run
- **shock_timing @lag_fraction=0.4**: attacker edge **+0.4017** on `C_t_drawn` vs a matched base run
- **crash_park @park_shift=-0.3**: attacker edge **+0.2375** on `G_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +300.0, `T_s` +271.4, `r_t` +0.0); re-basing in transit (arriving or at design offset): `C_t` +0.2
- **crash_park @park_shift=-0.9**: attacker edge **+0.8692** on `G_t_drawn` vs a matched base run (excludes 2 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `T_s` +791.3, `r_t` +0.1); re-basing in transit (arriving or at design offset): `L_f` +900.0, `C_t` +1.0
  - heal disclosure: after the one-shot move, protection `E_t` retains 100% of peak while the level stays moved
- **drift_creep @creep_rate=0.002**: attacker edge **+0.0048** on `C_t_drawn` vs a matched base run; drift responsiveness lag: `E_t` +113.2, `L_f` +3.7, `T_s` +32.2 (disclosed design lag, not an extraction)
- **drift_creep @creep_rate=0.01**: attacker edge **+0.1196** on `C_t_drawn` vs a matched base run; drift responsiveness lag: `E_t` +786.8, `L_f` +31.8, `T_s` +250.0 (disclosed design lag, not an extraction)
- **grind_harvest @harvest_shift=-0.3**: attacker edge **+0.1957** on `G_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +187.0, `T_s` +138.3, `r_t` +0.0); re-basing in transit (arriving or at design offset): `C_t` +0.1
- **grind_harvest @harvest_shift=-0.9**: attacker edge **+0.8634** on `G_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +883.9, `T_s` +649.4, `r_t` +0.1); re-basing in transit (arriving or at design offset): `C_t` +1.0
  - heal disclosure: after the one-shot move, protection `E_t` retains 100% of peak while the level stays moved
- **resonance @strikes=2**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `L_f` re-basing (+0.0 in motion at window end), `T_s` re-basing (+2.6 in motion at window end), `E_t_ratchet` re-basing (+0.0 in motion at window end), `T_s_ratchet` re-basing (+2.6 in motion at window end), `r_t_ratchet` re-basing (+0.0 in motion at window end), `C_t_ratchet` re-basing (+0.0 in motion at window end), `G_t_ratchet` re-basing (+0.0 in motion at window end)
- **resonance @strikes=8**: attacker edge **+0.0002** on `E_t_ratchet` vs a matched base run; re-basing in transit (arriving or at design offset): `L_f` +0.0, `T_s` +14.1, `r_t` +0.0, `C_t` +0.0, `G_t` +0.0, `L_f_ratchet` +0.0, `T_s_ratchet` +14.1, `r_t_ratchet` +0.0, `C_t_ratchet` +0.0, `G_t_ratchet` +0.0
- **resonance @strikes=16**: attacker edge **+0.0010** on `E_t_ratchet` vs a matched base run; re-basing in transit (arriving or at design offset): `L_f` +0.0, `T_s` +15.8, `r_t` +0.0, `C_t` +0.0, `G_t` +0.0, `L_f_ratchet` +0.0, `T_s_ratchet` +15.8, `r_t_ratchet` +0.0, `C_t_ratchet` +0.0, `G_t_ratchet` +0.0
- **resonance @strike_shift=-0.3**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `L_f` re-basing (+0.0 in motion at window end), `T_s` re-basing (+4.0 in motion at window end), `E_t_ratchet` re-basing (+0.0 in motion at window end), `L_f_ratchet` re-basing (+0.0 in motion at window end), `T_s_ratchet` re-basing (+4.0 in motion at window end), `r_t_ratchet` re-basing (+0.0 in motion at window end), `C_t_ratchet` re-basing (+0.0 in motion at window end), `G_t_ratchet` re-basing (+0.0 in motion at window end)
- **resonance @strike_shift=-0.9**: attacker edge **+0.0377** on `C_t_ratchet` vs a matched base run; re-basing in transit (arriving or at design offset): `L_f` +0.0, `T_s` +14.0, `r_t` +0.0, `E_t_ratchet` +0.0, `L_f_ratchet` +0.0, `T_s_ratchet` +14.0, `r_t_ratchet` +0.0, `G_t_ratchet` +0.0

## 5. Build-in-Public Progression (§27)

```text
[x] Idea
[x] Research
[x] Simulation
[← HUMAN DECISION — this package] Open-source publication
[ ] Community criticism
[ ] Prototype
[ ] Testnet
[ ] Developer adoption
[ ] Token/mainnet consideration
```

The lab is a research system (§28): no token, no contract deployment, no funds. The next step — open-source publication of this evidence package — is explicitly a human decision. Community criticism of the residual attacks above is the progression's designed next filter: publication invites the attackers to prove the residual surfaces real or bounded.


---

# Part C — §27 Release Package: the incumbent (r15-r19 recommended)

# Release Package: Demand-Index Escalation Ladder for FX Batches

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-09T03:04:32+00:00
Candidate: `cand-e74d830a9479` (finalist (explicit §27 subject — the human's selection, not the ranking's))

## 1. Publication Readiness

- Deterministic overall score: **6.4** (§19, 11 dimensions)
- Model versions stored: [1, 2] (append-only, §21)
- §15 battery: ✅ 13/13 scenarios clean
- Monte Carlo: 0 failures / 20 trials

## 2. The Mechanism (as recorded)

**Problem.** Cross-border FX corridors price congestion either through negotiated fees (opaque) or flat escalate-by-timeout rules (unresponsive to actual demand).

**Core causal chain.** FX settlement congestion becomes self-measuring: the demand index is derived entirely from on-chain queue state, and the escalation schedule couples price directly to that index, so the corridor prices its own scarcity without oracle trust. The refund reserve closes the loop by returning escalations to the population that paid them.

## 3. Evidence Trail

- Prior-art searches recorded: 4 (queries + sources stored, §12)
- Adversarial reports: 8 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: 1 patched version(s) stored; the final version v2 was re-attacked with the patched model in the adversarial prompt (§34 retest)

## 4. Residual Attacks Disclosure (§12 honesty)

This list is the searched attack space, not an absolute claim about all attacks (§12).

The red team found **1 profitable attack surface(s)** the final model version does not fully close (independent agents often converge on the same surface with different phrasings — convergence is itself evidence the surface is real). Publication means shipping the mechanism WITH these named residuals — every one is recorded here and in the dossier:

- **refund-cap exhaustion** [open; arbitrageur (requires collusion), HYPOTHESIS] — Repeated coordinated stuffing across epochs grinds the reserve toward its floor, degrading counter-cyclical function even if each cycle's profit is capped.

### 4b. Measured Attack-Pattern Bounds (§20)

Deterministic bounds from the §20 attack-pattern battery (60-step window, matched base runs).
- **vol_oscillation**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **wash_flow**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **pump_unwind**: measured, no positive attacker edge (the state(s) drained no further under attack than base) — 1 state excursion(s) were reclassified as REGIME TRACKING (EMA states following the moved level: the design working, not extraction): `F_t` +0.3
- **shock_timing**: attacker edge **+0.3182** on `F_t_drawn` vs a matched base run
- **crash_park**: measured, no positive attacker edge (the state(s) drained no further under attack than base) — 1 state excursion(s) were reclassified as REGIME TRACKING (EMA states following the moved level: the design working, not extraction): `F_t` +0.3
  - heal disclosure: after the one-shot move, protection `F_t` retains 0% of peak, `W_t` retains 33% of peak while the level stays moved
- **drift_creep**: measured, no positive attacker edge (the state(s) drained no further under attack than base); drift responsiveness: `Q_t` lags the drifted level by +313.3 more than base, `W_t` lags the drifted level by +318.4 more than base (design lag under a grinding regime, disclosed; an attacker edge only where a measured consumer response appears above)
- **grind_harvest**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
  - heal disclosure: after the one-shot move, protection `F_t` retains 33% of peak, `W_t` retains 79% of peak while the level stays moved
- **resonance**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `Q_t_ratchet` re-basing (+0.0 in motion at window end), `F_t_ratchet` re-basing (+0.0 in motion at window end), `W_t_ratchet` re-basing (+5.6 in motion at window end)
- **vol_oscillation @amplitude=0.02**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **vol_oscillation @amplitude=0.1**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **wash_flow @wash_level=0.01**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **wash_flow @wash_level=0.04**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **shock_timing @lag_fraction=0.1**: attacker edge **+0.3182** on `F_t_drawn` vs a matched base run
- **shock_timing @lag_fraction=0.4**: attacker edge **+0.3182** on `F_t_drawn` vs a matched base run
- **crash_park @park_shift=-0.3**: measured, no positive attacker edge (the state(s) drained no further under attack than base) — 1 state excursion(s) were reclassified as REGIME TRACKING (EMA states following the moved level: the design working, not extraction): `F_t` +0.3
- **crash_park @park_shift=-0.9**: measured, no positive attacker edge (the state(s) drained no further under attack than base) — 1 state excursion(s) were reclassified as REGIME TRACKING (EMA states following the moved level: the design working, not extraction): `F_t` +0.3
  - heal disclosure: after the one-shot move, protection `F_t` retains 0% of peak, `W_t` retains 33% of peak while the level stays moved
- **drift_creep @creep_rate=0.002**: measured, no positive attacker edge (the state(s) drained no further under attack than base); drift responsiveness: `Q_t` lags the drifted level by +104.1 more than base, `W_t` lags the drifted level by +106.8 more than base (design lag under a grinding regime, disclosed; an attacker edge only where a measured consumer response appears above)
- **drift_creep @creep_rate=0.01**: measured, no positive attacker edge (the state(s) drained no further under attack than base); drift responsiveness: `Q_t` lags the drifted level by +761.1 more than base, `W_t` lags the drifted level by +768.8 more than base (design lag under a grinding regime, disclosed; an attacker edge only where a measured consumer response appears above)
- **grind_harvest @harvest_shift=-0.3**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **grind_harvest @harvest_shift=-0.9**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
  - heal disclosure: after the one-shot move, protection `F_t` retains 27% of peak, `W_t` retains 52% of peak while the level stays moved
- **resonance @strikes=2**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `Q_t_ratchet` re-basing (+0.0 in motion at window end), `F_t_ratchet` re-basing (+0.0 in motion at window end), `W_t_ratchet` re-basing (+1.1 in motion at window end)
- **resonance @strikes=8**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `Q_t_ratchet` re-basing (+0.0 in motion at window end), `F_t_ratchet` re-basing (+0.0 in motion at window end), `W_t_ratchet` re-basing (+15.2 in motion at window end)
- **resonance @strikes=16**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `Q_t_ratchet` re-basing (+0.0 in motion at window end), `F_t_ratchet` re-basing (+0.0 in motion at window end), `W_t_ratchet` re-basing (+29.0 in motion at window end)
- **resonance @strike_shift=-0.3**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `Q_t_ratchet` re-basing (+0.0 in motion at window end), `F_t_ratchet` re-basing (+0.0 in motion at window end), `W_t_ratchet` re-basing (+3.6 in motion at window end)
- **resonance @strike_shift=-0.9**: attacker edge **+33.2546** on `W_t_ratchet` vs a matched base run; re-basing in transit (arriving or at design offset): `Q_t_ratchet` +0.0, `F_t_ratchet` +0.0

## 5. Build-in-Public Progression (§27)

```text
[x] Idea
[x] Research
[x] Simulation
[← HUMAN DECISION — this package] Open-source publication
[ ] Community criticism
[ ] Prototype
[ ] Testnet
[ ] Developer adoption
[ ] Token/mainnet consideration
```

The lab is a research system (§28): no token, no contract deployment, no funds. The next step — open-source publication of this evidence package — is explicitly a human decision. Community criticism of the residual attacks above is the progression's designed next filter: publication invites the attackers to prove the residual surfaces real or bounded.

