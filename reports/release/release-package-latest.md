# Release Package: Vol-Weighted Fee Smoothing Escrow

§27 build-in-public staging document — assembled by code from stored evidence only (§2). Publication is a HUMAN decision (§27); this package stages the evidence, it does not publish.

Generated: 2026-09-06T11:38:47+00:00
Candidate: `cand-7f4c2dee85e7` (§7 recommended, rank 1)

## 1. Publication Readiness

- Deterministic overall score: **6.125** (§19, 11 dimensions)
- Model versions stored: [1, 2] (append-only, §21)
- §15 battery: ✅ 13/13 scenarios clean
- Monte Carlo: 0 failures / 20 trials

## 2. The Mechanism (as recorded)

**Problem.** Fee-relay vouchers ration exactly during fee spikes (acceptance falls with fee level, the round-2 red-team finding); the congestion-indexed premium that fixes it is a parameter without a balance sheet — nobody funds the counter-cyclical margin top-ups, they are just assumed.

**Core causal chain.** Fee-voucher buyers pay vol-weighted premiums into a smoothing escrow; when congestion spikes would collapse relayer acceptance margins, the escrow's inventory subsidizes those margins so vouchers stay accepted — the vol payments the market itself made during volatility become the capital that keeps the hedge functioning through the volatility. Calm periods rebate the surplus to holders.

## 3. Evidence Trail

- Prior-art searches recorded: 3 (queries + sources stored, §12)
- Adversarial reports: 8 across ['game_theory', 'oracle', 'red_team', 'security']
- Improvement cycle: 1 patched version(s) stored; the final version v2 was re-attacked with the patched model in the adversarial prompt (§34 retest)

## 4. Residual Attacks Disclosure (§12 honesty)

This list is the searched attack space, not an absolute claim about all attacks (§12).

The red team found **8 profitable attack surface(s)** the final model version does not fully close (independent agents often converge on the same surface with different phrasings — convergence is itself evidence the surface is real). Publication means shipping the mechanism WITH these named residuals — every one is recorded here and in the dossier:

- **dv_t upswing cycling** [open; arbitrageur, HYPOTHESIS] — Oscillate vol: harvest max(0, dv_t) each upswing, pay nothing on falls — bounded per swing; the asymmetry is a design choice (symmetric pricing would tax honest mean reversion).
- **Attribution-error reflexive leak** [open; whale, INFERENCE] — k_net=0.8: 20% of manufactured flow reaches the vol input — the channel reduced to a frontier, profitability sweep-mapped.
- **Lag-trough margin timing** [open; liquidity_provider, HYPOTHESIS] — Spike into the amortization trough: residual subsidy edge — shrunken by sub_lag, not zero.
- **Attribution-error leak** [open; whale, INFERENCE] — k_net=0.8: a fifth of manufactured flow reaches the vol input — the reflexive channel at reduced strength; the robustness region is a sweep question, not a wall.
- **Lag-window margin trough** [open; liquidity_provider, HYPOTHESIS] — sub_lag=5 amortization: a spike faster than the amortization finds margins mid-deployment — the timing window shrank but did not close to zero; a spike timed into the trough extracts a residual subsidy edge.
- **Vol oscillation on dv_t** [open; arbitrageur, HYPOTHESIS] — Alternate vol up/down within the window: each rise pays pi_base + k_dv * dv_t while each fall costs nothing (max(0, dv_t)) — the derivative pricing's own mirror: the attacker harvests the upswings, the design absorbs the downswings. Netting struggles: oscillating flow looks like native noise to the attribution layer.
- **Reflexive vol pump-and-unwind** [open; whale, INFERENCE] — Manufacture vol through own voucher flow, harvest the vol-weight spread against real buyers, unwind before the EMA reverts — the design's input is the attacker's output.
- **Margin-peak exit extraction** [open; liquidity_provider, HYPOTHESIS] — Per-batch subsidy deployment (k_sub, deterministic) times relayer exits at the subsidized top — the escrow's own funding pays the extractor's exit.

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
