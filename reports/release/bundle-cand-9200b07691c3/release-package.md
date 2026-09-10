# Release Package: Separation-Keyed Fee Smoothing Escrow

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-10T04:27:17+00:00
Candidate: `cand-9200b07691c3` (finalist (explicit §27 subject — the human's selection, not the ranking's))

## 1. Publication Readiness

- Deterministic overall score: **6.45** (§19, 11 dimensions)
- Model versions stored: [1, 2, 3] (append-only, §21)
- §15 battery: ✅ 13/13 scenarios clean
- Monte Carlo: 0 failures / 20 trials

## 2. The Mechanism (as recorded)

**Problem.** The superseded predecessor's retention keyed ABSOLUTE realized vol (eta=40 pinned r_t at the 0.9 ceiling through every crafted ramp) while its outflow term was 0.05*sigma weaker — every resonance cycle over-retained inflow monotonically: measured ratchet 285 -> 1321 -> 2143 -> 6479 (linear-unbounded in N, persists under a quiet tail; r20 measured)

**Core causal chain.** Fast pressure EMA vs slow regime EMA; retention = clip(delta + eta * separation / X, 0.1, 0.9) with the SEPARATION denominated relative; escrow flow symmetric in the same separation key (inflow and outflow caps mirror); clip bounds bracket battery scales.

## 3. Evidence Trail

- Prior-art searches recorded: 1 (2 source rows; identical findings merged, §12)
- Adversarial reports: 12 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: 2 patched version(s) stored; the final version v3 was re-attacked with the patched model in the adversarial prompt (§34 retest)

## 4. Residual Attacks Disclosure (§12 honesty)

No profitable attack remains unaddressed by the final model version. This is a statement about the searched attack space, not an absolute claim of security (§12: no absolute claims).

The model's own recorded open questions (§13, verbatim):
- OPEN QUESTION: can sustained genuine pressure (not crafted) hold the separation key high enough to farm retention?

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
