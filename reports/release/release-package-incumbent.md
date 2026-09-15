# Release Package: Demand-Index Escalation Ladder for FX Batches

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-15T01:04:29
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

- Prior-art searches recorded: 1 (4 source rows; identical findings merged, §12)
- Adversarial reports: 8 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: 1 patched version(s) stored; the final version v2 was re-attacked with the patched model in the adversarial prompt (§34 retest)

## 4. Residual Attacks Disclosure (§12 honesty)

This list is the searched attack space, not an absolute claim about all attacks (§12).

The red team named **3 attack surface(s)** the final model version does not fully close (independent agents often converge on the same surface with different phrasings — convergence is itself evidence the surface is real). Publication means shipping the mechanism WITH these named residuals — every one is recorded here and in the dossier:

_profitability flag = the attacking agent's own hypothesis about whether the vector pays; it is recorded metadata, never a filter — vectors asserted unprofitable are disclosed here exactly the same way (r36)._

- **capped-cycle grinding** [open; arbitrageur (requires collusion), INFERENCE; unprofitable-asserted] — Escalation-proportional capped refunds make stuffing a pure deadweight loss.
- **reserve-floor pressure** [open; arbitrageur (requires collusion), HYPOTHESIS; unprofitable-asserted] — Repeated cycles push the reserve toward its floor but cannot breach it; counter-cyclical function degrades gracefully, not catastrophically.
- **refund-cap exhaustion** [open; arbitrageur (requires collusion), HYPOTHESIS; profitable-hypothesis] — Repeated coordinated stuffing across epochs grinds the reserve toward its floor, degrading counter-cyclical function even if each cycle's profit is capped.

The model's own recorded open questions (§13, verbatim):
- OPEN QUESTION: should the ladder rungs be exponential rather than linear in Q?

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
- **pump_unwind @amplitude=0.02**: measured, no positive attacker edge (the state(s) drained no further under attack than base) — 1 state excursion(s) were reclassified as REGIME TRACKING (EMA states following the moved level: the design working, not extraction): `F_t` +0.3
- **pump_unwind @amplitude=0.1**: measured, no positive attacker edge (the state(s) drained no further under attack than base) — 1 state excursion(s) were reclassified as REGIME TRACKING (EMA states following the moved level: the design working, not extraction): `F_t` +0.3
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
