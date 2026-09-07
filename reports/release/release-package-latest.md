# Release Package: Prediction-Fee Fallback Oracle

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-07T03:49:56+00:00
Candidate: `cand-cab81fc40bbf` (§7 recommended, rank 1)

## 1. Publication Readiness

- Deterministic overall score: **6.65** (§19, 11 dimensions)
- Model versions stored: [1, 2] (append-only, §21)
- §15 battery: ✅ 13/13 scenarios clean
- Monte Carlo: 0 failures / 20 trials

## 2. The Mechanism (as recorded)

**Problem.** Payment rails that read oracles either halt on feed failure or silently switch to a single fallback; both behaviors are unpriced and invite stale-quote griefing.

**Core causal chain.** Oracle failure becomes a priced service level instead of a halt: the fee ladder makes degraded data expensive to use, which funds sender insurance and suppresses low-stakes use of the degraded mode. The continuously traded prediction book is the last rung because its open-interest floor makes manipulating the fallback costly in proportion to the damage it could do.

## 3. Evidence Trail

- Prior-art searches recorded: 1 (queries + sources stored, §12)
- Adversarial reports: 8 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: 1 patched version(s) stored; the final version v2 was re-attacked with the patched model in the adversarial prompt (§34 retest)

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
