# Release Package: Vol-Weighted Fee Smoothing Escrow

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-06T16:37:44+00:00
Candidate: `cand-cd39d95ea572` (§7 recommended, rank 1)

## 1. Publication Readiness

- Deterministic overall score: **5.7** (§19, 11 dimensions)
- Model versions stored: [1, 1, 2] (append-only, §21)
- §15 battery: ✅ 13/13 scenarios clean
- Monte Carlo: 0 failures / 20 trials

## 2. The Mechanism (as recorded)

**Problem.** Volatile transaction fees make gas costs unpredictable and complicate batch settlement budgets

**Core causal chain.** An escrow contract collects fees into a smoothed pool whose release rate responds to realized volatility: when measured volatility rises, more of each fee is retained to back settlement; when volatility decays, retained buffer releases to proposers, so per-transaction effective cost stays smooth

## 3. Evidence Trail

- Prior-art searches recorded: 0 (queries + sources stored, §12)
- Adversarial reports: 8 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: 2 patched version(s) stored; the final version v2 was re-attacked with the patched model in the adversarial prompt (§34 retest)

## 4. Residual Attacks Disclosure (§12 honesty)

No profitable attack remains unaddressed by the final model version. This is a statement about the searched attack space, not an absolute claim of security (§12: no absolute claims).

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
