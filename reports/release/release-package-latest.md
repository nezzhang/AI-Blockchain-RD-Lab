# Release Package: Separation-Keyed Fee Smoothing Escrow

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-20T15:02:24
Candidate: `cand-9200b07691c3` (§7 recommended, rank 1)

## 1. Publication Readiness

- Deterministic overall score: **6.725** (§19, 11 dimensions)
- Model versions stored: [3] (append-only, §21)
- §15 battery: ✅ 13/13 scenarios clean
- Monte Carlo: 0 failures / 20 trials

## 2. The Mechanism (as recorded)

**Problem.** The superseded predecessor's retention keyed ABSOLUTE realized vol (eta=40 pinned r_t at the 0.9 ceiling through every crafted ramp) while its outflow term was 0.05*sigma weaker — every resonance cycle over-retained inflow monotonically: measured ratchet 285 -> 1321 -> 2143 -> 6479 (linear-unbounded in N, persists under a quiet tail; r20 measured)

**Core causal chain.** Fast pressure EMA vs slow regime EMA; retention = clip(delta + eta * separation / X, 0.1, 0.9) with the SEPARATION denominated relative; escrow flow symmetric in the same separation key (inflow and outflow caps mirror); clip bounds bracket battery scales.

## 3. Evidence Trail

- Prior-art searches recorded: 1 (2 source rows; identical findings merged, §12)
- Adversarial reports: 12 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: none (single version)

## 4. Residual Attacks Disclosure (§12 honesty)

This list is the searched attack space, not an absolute claim about all attacks (§12).

The red team named **16 attack surface(s)** the final model version does not fully close (independent agents often converge on the same surface with different phrasings — convergence is itself evidence the surface is real). Publication means shipping the mechanism WITH these named residuals — every one is recorded here and in the dossier:

_profitability flag = the attacking agent's own hypothesis about whether the vector pays; it is recorded metadata, never a filter — vectors asserted unprofitable are disclosed here exactly the same way (r36)._

- **sustained-lead retention farming** [open; whale, INFERENCE; unprofitable-asserted] — A whale grinds the level up at a steady +0.5%/step (sub-spike): the fast EMA leads the slow anchor by a stable ~+4%, retention pins near 0.36-0.9, and the buffer target 1000 + 18*r_t inflates ~6 units above anchor — the escrow holds fees the attacker's own grind priced in. The move cost is real but the buffer delta persists as long as the grind does
- **buffer-reversion front-running** [open; arbitrageur, HYPOTHESIS; unprofitable-asserted] — The escrow converges to its target at lam_e=0.15: a predictable ~7-step half-life. An attacker who knows the target path can time fee INFLow windows (when target > current escrow, retained inflow is locked at high retention) and fee USE windows (after the target falls) — extracting the convergence spread itself
- **separation-key oscillation wash** [open; attacker, HYPOTHESIS; unprofitable-asserted] — Zero-mean cycling averages the separation key to ~0 — the design's stated immunity. But the clip floor 0.1 makes retention ASYMMETRIC around zero mean: down-legs release to 0.1 while up-legs retain to 0.9, so a 50/50 saw-tooth (slow down, fast up) could bias the time-average of r_t above delta_r
- **saw-tooth retention bias** [open; attacker, INFERENCE; profitable-hypothesis] — Slow-down/fast-up crafted cycles: down legs pin retention at 0.1, up legs ride toward 0.9; the time-average of retention exceeds 0.3 on a zero-mean path, inflating the buffer target (1000 + 18*r_t) persistently while the cycling continues
- **observable-path front-running** [open; arbitrageur, HYPOTHESIS; unprofitable-asserted] — All keying states are public EMAs of the level: the escrow's target path is predictable ~7 steps ahead; fee-payers can time around high-retention windows, leaving the escrow holding adverse fees (a adverse-selection vector on fee inflow, not on the escrow stock itself)
- **anchor-drift stale-band hold** [open; liquidity_provider, INFERENCE; unprofitable-asserted] — After a genuine one-sided regime break, the slow anchor trails for ~1/kappa_s steps; retention keys the stale separation and over-retains through the break's recovery leg — a transient overcharge window proportional to the anchor lag
- **reversion-spread timing** [open; arbitrageur, HYPOTHESIS; unprofitable-asserted] — The escrow's lam_e=0.15 convergence makes the target path predictable ~7 steps out; timing fee inflow windows against the convergence spread extracts the spread — bounded by the cap 18
- **stale-anchor overcharge window** [open; liquidity_provider, INFERENCE; unprofitable-asserted] — After genuine breaks the slow anchor trails ~17 steps; retention over-charges through the recovery leg — a disclosed responsiveness gap, no profitable attacker path identified
- **slow saw-tooth under the counter threshold** [open; attacker, INFERENCE; profitable-hypothesis] — Craft a zero-mean saw-tooth with small per-step moves (fast-EMA movement < 8, the counter's normalization): C_t stays ~0, the separation key rides every alternation, and the symmetric band still lets up-legs push retention +0.25 while down-legs pull only -0.25 — the average can exceed base whenever the saw-tooth's positive legs are longer-lived than its negative legs (duty-cycle bias within the band)
- **genuine-lead deadness (functionality failure)** [open; unspecified, FACT; unprofitable-asserted] — The counter pins at 1.0 under any sustained move with fast-EMA movement above 8 (a 3%/step grind measures C_t=1.0 throughout): retention never rises above base on REAL pressure — the escrow never builds its buffer when genuine stress arrives. Not directly attacker P&L, but the mechanism fails its core function under the conditions it exists for
- **counter-threshold boundary riding** [open; attacker, INFERENCE; profitable-hypothesis] — Saw-teeth calibrated to keep |kappa_f*(X-L_f)| just under 8: the counter reads ~0 and the separation key rides — the bias the counter was installed to remove returns at a smaller amplitude (bounded by the band half-width 0.25 and the duty-cycle asymmetry a saw-tooth can carry within the threshold)
- **genuine-stress buffer failure** [open; unspecified, FACT; unprofitable-asserted] — Under real sustained stress (the scenario a fee escrow exists for) the counter discounts the retention response: the buffer target stays at base through the stress window — a solvency risk for the escrow's smoothing promise, disclosed as a functionality failure rather than an extraction
- **genuine-lead deadness** [open; unspecified, FACT; unprofitable-asserted] — Magnitude keying discounts genuine pressure with crafted: retention flat 0.300 through a 3%/step sustained grind (measured) — the buffer never builds under real stress
- **counter handoff window** [open; attacker, INFERENCE; unprofitable-asserted] — After a genuine lead (C_t ~0) ends, an immediate saw-tooth rides the separation key at full strength for ~1/lam_c steps before the counter catches up — a first-cycle transient the discount misses; bounded by the symmetric band half-width 0.25 and requires paying the genuine lead's move cost first
- **long-period alternation partial ride** [open; attacker, INFERENCE; unprofitable-asserted] — A saw-tooth with period >> 1/lam_c (~5 steps) lets the counter partially decay during each long leg, so the first portion of every leg rides at partial discount — the average discount is < 1 and part of each leg's separation keys retention; bounded by the symmetric band (±0.25 around base) and second-order
- **counter handoff window after a genuine lead** [open; attacker, INFERENCE; unprofitable-asserted] — ~1/lam_c-step window after a real lead ends where alternation rides at full key strength before the counter catches up; requires paying the lead's cost first

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
- **resonance**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `C_t_ratchet` re-basing (+0.0 in motion at window end), `E_t_ratchet` re-basing (+0.0 in motion at window end), `G_t_ratchet` re-basing (+0.0 in motion at window end), `L_f` re-basing (+0.0 in motion at window end), `L_f_ratchet` re-basing (+0.0 in motion at window end), `T_s` re-basing (+8.4 in motion at window end), `T_s_ratchet` re-basing (+8.4 in motion at window end), `r_t_ratchet` re-basing (+0.0 in motion at window end)
- **vol_oscillation @amplitude=0.02**: attacker edge **+0.1187** on `C_t_drawn` vs a matched base run
- **vol_oscillation @amplitude=0.1**: attacker edge **+0.9999** on `C_t_drawn` vs a matched base run
- **wash_flow @wash_level=0.01**: attacker edge **+0.0023** on `G_t_drawn` vs a matched base run
- **wash_flow @wash_level=0.04**: attacker edge **+32.6375** on `L_f_drawn` vs a matched base run
- **pump_unwind @amplitude=0.02**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `C_t` re-basing (+0.3 in motion at window end)
- **pump_unwind @amplitude=0.1**: attacker edge **+0.9999** on `C_t_drawn` vs a matched base run
- **shock_timing @lag_fraction=0.1**: attacker edge **+0.1862** on `C_t_drawn` vs a matched base run
- **shock_timing @lag_fraction=0.4**: attacker edge **+0.4017** on `C_t_drawn` vs a matched base run
- **crash_park @park_shift=-0.3**: attacker edge **+0.2375** on `G_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +300.0, `T_s` +271.4, `r_t` +0.0); re-basing in transit (arriving or at design offset): `C_t` +0.2
- **crash_park @park_shift=-0.9**: attacker edge **+0.8692** on `G_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +900.0, `T_s` +791.3, `r_t` +0.1); re-basing in transit (arriving or at design offset): `C_t` +1.0
  - heal disclosure: after the one-shot move, protection `E_t` retains 100% of peak while the level stays moved
- **drift_creep @creep_rate=0.002**: attacker edge **+0.0048** on `C_t_drawn` vs a matched base run; drift responsiveness lag: `E_t` +113.2, `L_f` +3.7, `T_s` +32.2 (disclosed design lag, not an extraction)
- **drift_creep @creep_rate=0.01**: attacker edge **+0.1196** on `C_t_drawn` vs a matched base run; drift responsiveness lag: `E_t` +786.8, `L_f` +31.8, `T_s` +250.0 (disclosed design lag, not an extraction)
- **grind_harvest @harvest_shift=-0.3**: attacker edge **+0.1957** on `G_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +187.0, `T_s` +138.3, `r_t` +0.0); re-basing in transit (arriving or at design offset): `C_t` +0.1
- **grind_harvest @harvest_shift=-0.9**: attacker edge **+0.9739** on `C_t_drawn` vs a matched base run (excludes 3 regime-tracking excursion(s): EMA states following the moved level — design property, not extraction: `L_f` +883.9, `T_s` +649.4, `r_t` +0.1)
  - heal disclosure: after the one-shot move, protection `E_t` retains 100% of peak while the level stays moved
- **resonance @strikes=2**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `C_t_ratchet` re-basing (+0.0 in motion at window end), `E_t_ratchet` re-basing (+0.0 in motion at window end), `G_t_ratchet` re-basing (+0.0 in motion at window end), `L_f` re-basing (+0.0 in motion at window end), `T_s` re-basing (+2.6 in motion at window end), `T_s_ratchet` re-basing (+2.6 in motion at window end), `r_t_ratchet` re-basing (+0.0 in motion at window end)
- **resonance @strikes=8**: attacker edge **+0.0002** on `E_t_ratchet` vs a matched base run; re-basing in transit (arriving or at design offset): `C_t` +0.0, `C_t_ratchet` +0.0, `G_t` +0.0, `G_t_ratchet` +0.0, `L_f` +0.0, `L_f_ratchet` +0.0, `T_s` +14.1, `T_s_ratchet` +14.1, `r_t` +0.0, `r_t_ratchet` +0.0
- **resonance @strikes=16**: attacker edge **+0.0010** on `E_t_ratchet` vs a matched base run; re-basing in transit (arriving or at design offset): `C_t` +0.0, `C_t_ratchet` +0.0, `G_t` +0.0, `G_t_ratchet` +0.0, `L_f` +0.0, `L_f_ratchet` +0.0, `T_s` +15.8, `T_s_ratchet` +15.8, `r_t` +0.0, `r_t_ratchet` +0.0
- **resonance @strike_shift=-0.3**: measured, no positive attacker edge (the state(s) drained no further under attack than base); re-basing in transit (confirmed arriving at a doubled window, or resting at its base-run offset from its design target): `C_t_ratchet` re-basing (+0.0 in motion at window end), `E_t_ratchet` re-basing (+0.0 in motion at window end), `G_t_ratchet` re-basing (+0.0 in motion at window end), `L_f` re-basing (+0.0 in motion at window end), `L_f_ratchet` re-basing (+0.0 in motion at window end), `T_s` re-basing (+4.0 in motion at window end), `T_s_ratchet` re-basing (+4.0 in motion at window end), `r_t_ratchet` re-basing (+0.0 in motion at window end)
- **resonance @strike_shift=-0.9**: attacker edge **+0.0377** on `C_t_ratchet` vs a matched base run; re-basing in transit (arriving or at design offset): `E_t_ratchet` +0.0, `G_t_ratchet` +0.0, `L_f` +0.0, `L_f_ratchet` +0.0, `T_s` +14.0, `T_s_ratchet` +14.0, `r_t` +0.0, `r_t_ratchet` +0.0

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
