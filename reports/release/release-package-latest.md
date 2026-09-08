# Release Package: Bandwidth Bond Market for Relay Peers

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-08T01:40:44+00:00
Candidate: `cand-b713e862acdc` (§7 recommended, rank 1)

## 1. Publication Readiness

- Deterministic overall score: **6.525** (§19, 11 dimensions)
- Model versions stored: [1, 2] (append-only, §21)
- §15 battery: ✅ 13/13 scenarios clean
- Monte Carlo: 0 failures / 20 trials

## 2. The Mechanism (as recorded)

**Problem.** P2P relay capacity is volunteered and unverified; paid relay markets exist but price capacity without verifying delivery or accounting operational energy cost.

**Core causal chain.** Internet relay bandwidth becomes a bonded commodity with probe-verified delivery: capacity is committed forward, verified live, and forfaited on shortfall. The energy metering couples the auction price to the real operational (compute and power) cost of delivering the commitment, so underpriced capacity commitments cannot externalize their energy cost.

## 3. Evidence Trail

- Prior-art searches recorded: 4 (queries + sources stored, §12)
- Adversarial reports: 8 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: 1 patched version(s) stored; the final version v2 was re-attacked with the patched model in the adversarial prompt (§34 retest)

## 4. Residual Attacks Disclosure (§12 honesty)

This list is the searched attack space, not an absolute claim about all attacks (§12).

The red team found **1 profitable attack surface(s)** the final model version does not fully close (independent agents often converge on the same surface with different phrasings — convergence is itself evidence the surface is real). Publication means shipping the mechanism WITH these named residuals — every one is recorded here and in the dossier:

- **probe underfunding** [open; attacker, INFERENCE] — Starving the probe budget degrades verification coverage; forfaits stop firing and under-delivery becomes free.

### 4b. Measured Attack-Pattern Bounds (§20)

Deterministic bounds from the §20 attack-pattern battery (60-step window, matched base runs).
- **vol_oscillation**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **wash_flow**: attacker edge **+2.4958** on `A_t_drawn` vs a matched base run
- **pump_unwind**: measured, no positive attacker edge (the state(s) drained no further under attack than base)
- **shock_timing**: measured, no positive attacker edge (the state(s) drained no further under attack than base)

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
