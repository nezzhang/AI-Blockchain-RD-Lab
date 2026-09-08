# Release Package: Demand-Index Escalation Ladder for FX Batches

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-08T02:24:24+00:00
Candidate: `cand-e74d830a9479` (§7 recommended, rank 1)

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
- **pump_unwind**: attacker edge **+0.3177** on `F_t_drawn` vs a matched base run
- **shock_timing**: attacker edge **+0.3182** on `F_t_drawn` vs a matched base run
- **crash_park**: attacker edge **+0.3182** on `F_t_drawn` vs a matched base run
  - heal disclosure: after the one-shot move, protection `F_t` retains 0% of peak, `W_t` retains 33% of peak while the level stays moved

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
