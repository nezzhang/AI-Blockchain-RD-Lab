# CLAUDE.md

Claude-specific notes for working in this repository.

**Read [`AGENTS.md`](./AGENTS.md) first — it is the binding rulebook for all
AI agents here.** Everything below is a convenience summary, not a
replacement.

## Quick Reference

- Prime directive: *LLM proposes. Code tests. Evidence decides.*
- Build phase by phase (see [`MASTER BUILD PROMPT.md`](./MASTER%20BUILD%20PROMPT.md) §38).
  Phase 0 = foundation. Phase 1 = discovery. Phase 2 = research. Phase 3 =
  formalization. Phase 4 = simulation. Phase 5 = adversarial testing.
  Phase 6 = ranking. Phase 7 = reporting. Phase 8 = pipeline + public
  research (done). All §7 commands implemented.
- All agent output must pass Pydantic validation before storage.
- Candidate status changes only via `Candidate.transition()` (state machine,
  `src/blockchain_rd_lab/schemas.py`).
- Scoring is deterministic (`src/blockchain_rd_lab/scoring/`); confirmed fatal
  flaws cap scores and are never averaged away.
- Discovery: `src/blockchain_rd_lab/discovery/` — agent (LLM) + normalizer and
  deduplicator (pure code) + service; `lab discover --mock-fixtures` runs offline.
- Research: `src/blockchain_rd_lab/research/` — Prior-Art/Economist/Market
  agents + service + deterministic `ResearchFilter` (§7 funnel);
  `lab research --mock-fixtures` and `lab filter` run offline.
- Formalization: `src/blockchain_rd_lab/formalization/` — Mechanism Designer
  agent + `MathModel` schema (variables/parameters/equations/assumptions,
  §13) + deterministic integrity checks; `lab formalize --mock-fixtures`
  runs offline.
- Simulation: `src/blockchain_rd_lab/simulation/` — safe equation
  interpreter + §15 scenario battery (13 scenarios incl. bank run, oracle
  failure, black swan) + Monte Carlo + parameter sweeps + Optuna (optional);
  `lab simulate` runs offline; every run persists §21 experiment records
  (seed, git commit, parameters, results).
- Red team: `src/blockchain_rd_lab/redteam/` — Game-Theory/Security/Oracle/
  Red-Team agents ("DESTROY THE IDEA", §9); the §20 fatal-flaw gate is
  deterministic code — a fatal verdict only rejects when the strongest
  attack is also profitable; `lab redteam --mock-fixtures` runs offline.
- Ranking: `src/blockchain_rd_lab/ranking/` — deterministic §19 scoring
  (11 weighted dimensions, missing dims imputed at 5.0), §20 gate
  exclusion, stable ranking (score desc, name asc), §7 finalist cut;
  `lab rank` and `lab score` advance RED_TEAM -> SCORED -> FINALIST.
- Reporting: `src/blockchain_rd_lab/reporting/` — §23 dossiers (19 fixed
  sections) + lab funnel report + §27 release package, ASSEMBLED BY CODE
  from stored evidence (no report-writer LLM; §2); rank-1 finalist is the
  §7 recommended candidate; `lab report [id]` writes reports/finalists/ +
  lab-latest.md + reports/release/release-package-latest.md (build-in-public
  staging: publication is the HUMAN decision, §27/§28; its §4 residual
  disclosure lists every still-profitable/open attack surface the final
  model version carries, strongest-honest-status per surface).
- Pipeline: `src/blockchain_rd_lab/pipeline/` — §34 full loop (discover →
  research → filter → formalize → simulate → redteam → improve → retest →
  score → report); resumable by status (§35: the database is the
  checkpoint); `lab pipeline --count N --mock-fixtures [--stop-after stage]`.
- Improvement loop: `src/blockchain_rd_lab/improvement/` — §34 improve +
  retest stages: the Improvement Agent (LLM) proposes a patched MathModel
  v(n+1) addressing profitable attacks; deterministic §13 integrity checks
  gate it; RETEST re-simulates (§15 battery) and re-attacks (fresh red
  team, §20 gate re-evaluates). RED_TEAM → IMPROVEMENT → RETEST →
  SIMULATING → RED_TEAM; `lab improve`/`lab retest` (offline fixtures).
- Combinator: `src/blockchain_rd_lab/combinator/` — §18 mechanism
  combination engine, pure deterministic code: mines §17 mechanism
  families from the stored corpus by vocabulary, scores pairs by
  semantic bridge (shared keywords) + economic compatibility (curated
  control-flow map), emits hints that steer `lab discover --combine`;
  `lab combine` inspects families/pairs. Never random mashups.
- Cost control: `src/blockchain_rd_lab/cost/` — §31 enforcement: TokenBudget
  (hard fail-closed ceiling), BudgetGuard provider wrapper (cache + budget
  on every call), ResponseCache (disk-backed, TTL), UsageLedger
  (reports/usage-latest.json). Pipeline halts cleanly on exhaustion and
  resumes with a fresh budget; cache hits are free.
- Knowledge graph: `src/blockchain_rd_lab/graph/` — §33: deterministic
  derived graph over all stored evidence (idea ↔ source ↔ mechanism ↔
  simulation ↔ attack ↔ improvement, typed edges); `lab graph [id]`
  (+ --similar-attack for §32 reuse: how was a similar attack fixed?);
  artifact reports/graph-latest.json.
- Bridge: `src/blockchain_rd_lab/agents/bridge.py` — §30 agent-as-LLM
  (DEFAULT provider; config tests pin 'bridge')
  provider: file-protocol (requests/answers under .bridge/),
  fail-closed pending halt, deterministic request ids, free replay
  of answered requests; `lab bridge list|show|answer|purge`;
  structured-only (no free-text completion, §2).
- Improve-stage simulatability gate: every patched model must
  survive one deterministic base-scenario step (parameters +
  battery inputs + initial state) BEFORE storing — unfed inputs
  and dependency cycles are caught at RED_TEAM (resubmittable),
  never at RETEST's terminal step 0.
- Degenerate-run gate (§15 evidence quality): runs whose states pin
  at clip bounds / freeze (every scenario indistinguishable) are
  flagged `degenerate` — vacuous evidence, NOT clean. The §15
  verdict FAILS such models (SIMULATING → FAILED, resubmittable);
  the formalize prompt now states the battery input contract
  (X_t anchor level ~1000, dX_t delta, states seed at 1000, clip
  bounds must bracket those scales).
- §14 state feedback: models declaring both S_t and S_t1 as states
  (the §13 bridge convention) roll computed S_t1 back into S_t —
  the feedback loop closes (previously such models ran flat at
  their initial state and still "passed" the battery).
- Adversarial pattern battery (§20 residual bounding):
  `simulation/adversarial.py` executes the named attack
  choreographies (vol oscillation, wash flow, pump-unwind, shock
  timing) against the final model and reports the attacker's edge
  vs a matched base run; saturated models report headline=None
  (VACUOUS), never 0.0 — a false "bounded by zero" claim.
- Evidence-quality audit: `lab audit` re-runs every stored
  FINALIST/SCORED model under TODAY'S interpreter + battery and
  reports healthy | vacuous | uninterpretable (legacy cycles) —
  the census that exposes ranking evidence authored under older
  gates; §11 corrections remain the operator's decision.
- Curriculum guard (anti-reward-hacking, SimSkill-inspired):
  `discovery/curriculum.py` + `lab audit`'s coverage profile — one
  deterministic measurement of whether the ranked corpus farms a
  narrow family of trivially-passing candidates (SimSkill's
  system-level reward-hacking analogue; the round-7 vacuum is the
  canonical case). Verdicts: ok | warn (honest concentration) |
  degenerate (dominant family's evidence vacuous) | starving (<3
  families). Measures only (§2); operator decides. §12 prior-art
  record for SimSkill (arXiv 2609.03753) stored via
  scripts/r8_priorart_simskill.py — its 'verification asymmetry'
  foundation is the academic form of the lab's §2.
- Round 15 crash_park lineage round (r14 findings triaged, one real
  flaw, three honest verdicts): diagnostic on the 4 candidates the
  r14 re-measurement flagged. BANDWIDTH BOND MARKET (then the
  RECOMMENDED candidate): CONFIRMED FLAW — the collateral pool is
  caught between TWO MAGNETS (0.07*(1000-C) anchor reversion +
  0.03*(X-1000) level tracking); under a permanent shift it settles at
  the tug-of-war equilibrium 22% from the level, the stress deviation
  NEVER closes, and the pool burns chi*s*300 (~17.7/step) FOREVER
  while A_t holders are relatively enriched (A/C doubles; measured
  C_t drawn 179.24, standing at equilibrium). Superseded (FINALIST ->
  SUPERSEDED — the lab supersedes its own #1 on measured evidence) +
  successor Level-Recentered Bandwidth Bond Market (cand-6fea4a5332ca)
  with a SINGLE-MAGNET pool: slow EMA of the level, stress keyed to
  the closing deviation, slash bounded to the re-basing transient.
  Floor lesson caught by the smoke: pool floor 450 was ABOVE the -60%
  crash level (400) — the clip re-created the eternal burn through
  the back door; floor 250 lets the pool reach the level (late-window
  stress 0.0000 measured). JOULE: CORRECT behavior (alarm persists
  through the re-base window then heals on GENUINE re-base; Q_c spend
  is the credit working) — no supersede. FX MATCHING: M/V crash-step
  excursion fully recovers under park (throughput index, not a pool)
  — battery now classifies RECOVERED excursions (<25% of peak at
  parked window end) as TRANSIENT (headline 96 -> 0.14). CORRIDOR:
  r13 verdict stands; T_t excursion reclassified transient (headline
  108 -> U_t 73, the honest standing edge). Battery classification
  gained the r15b numeric level-arrival check (|final - X_final| <
  10% of level = followed the regime; shape-independent — the r14
  shape filter missed the successor pool because it reads a stress
  aux) + the transient-recovery check; release 4b renders both
  (REGIME TRACKING / TRANSIENT context lines). Successor red-teamed
  VULNERABLE (escrow-kicker pulse farming — the r13 family applied to
  allocation weight; re-basing-window slash dumping), v2-patched
  (kicker re-keyed to fast-vs-pool EMA separation; slash AGE-WEIGHTED
  via a post-age state so window-dumped posts pay their own cost),
  SURVIVES re-attack; scored 6.26 vs predecessor 6.525 (honest
  patching cost on the former #1). New recommended: Demand-Index
  Escalation Ladder 6.40. Successor's own disclosed residuals:
  crash_park A_t 299.7 (allocation contract passing through to
  capacity — the disclosed design choice) + P_a tenure-denial under
  oscillation (a small honest griefing vector, queued for a future
  round). §21 battery records re-stored for all 4 under the final
  r15 battery. Tests +2 (transient-recovery classification, standing
  drain never hidden — the honesty fix must not become a hiding
  place). 395 pass.
- Round 14 4b-disclosure honesty fix: the §20 battery's crash_park
  headline was carried ENTIRELY by EMA-of-level states following the
  moved level (600 = the fix from r12/r13 WORKING), which the §27
  4b section then published as a 'measured attacker edge' — a
  misleading disclosure, exactly what the lab exists to prevent. Fix
  in two layers: (1) the battery now classifies EMA-of-level states
  (equation reads itself + X_t only, ignoring function names and
  parameters) as REGIME-TRACKING: under park-style choreographies
  (crash_park, pump_unwind's parked half) their _drawn excursions are
  excluded from the attacker-edge headline and recorded separately as
  regime_tracking on the AttackBound — measured once where the
  measurement happens; (2) the release 4b renderer discloses BOTH
  layers: the honest attacker edge (if any) AND the regime-tracking
  reclassification AND the r13 heal_flags (per keyed protection state,
  % of crash-time peak retained while parked; next-state symbols
  dropped). Pinned by 4 tests (TestBoundsDisclosureHonesty).
  Re-measured all 17 stored SCORED/FINALIST battery records under the
  r14 code — which surfaced crash_park exposure the OLD battery was
  structurally blind to across the corpus: Bandwidth Bond Market (the
  RECOMMENDED candidate) C_t collateral drains 179 under crash_park
  (its stress slash chi*s_t*300 has no beneficiary — insurance-payout
  semantics, honestly ambiguous: the 4b now shows the raw edge and
  the heal disclosure 'A_t retains 100% of peak' on the release page);
  Corridor T_t 108; FX Matching M_t 96; Joule Q_c credit 66. These are
  now disclosed, not hidden — the r13 battery semantics lesson closed
  with the classification living in the measurement, and the new
  corpus-wide crash_park findings queue the next round's work.
- Round 13 anchor-heal round (r12 finding generalized — and corrected
  by evidence): hypothesis "all 3 r11 anchored-trend siblings heal
  under move-once-then-park" tested with a new §20 battery pattern
  CRASH_PARK (the choreography wash/pump/osc/shock all lack: they move
  repeatedly or revert; nothing parks) + a battery-level heal_flags
  measurement (per keyed protection state, the parked displacement as a
  fraction of crash-time peak, POST-crash window only — an earlier draft
  keyed the init transient and mis-flagged; caught in review). Evidence:
  Oracle F_t heals to 7% of peak while the level stays -60% moved
  (tail cover sold at anchor-normal premium — monetizable); Joule
  drift alarm fires 4 steps then heals under the moved regime
  (healed-window defaults pay no slash premium); Corridor U_t RETAINS
  74% (its level term tracks the move — protection persists, NO flaw;
  the 3/3 hypothesis was wrong, no supersede); r12 meter E_t heals BY
  DESIGN (re-banding semantics). Superseded the 2 confirmed (lineage =
  measured heal ratios), minted 2 successors with the r12 primitive at
  INSURANCE POLARITY: a THREE-SPEED construction (fast kicker + medium
  EMA + ultra-slow regime-anchor EMA; the gate = |medium - anchor|/anchor
  — in smooth growth they track together (no false premium), after
  crash-park the medium EMA stays below the anchor indefinitely
  (persistent displacement), zero-mean oscillation flattens both (no
  wash harvest). First v1 draft keyed the fee to a single level-EMA —
  the §15 battery caught 10/13 scenario collapse (the base scenario's
  inherent growth carried the level to 2400 and pinned the fee/OI
  clips), forcing the 3-speed construction. Both v1 smoke-gated
  (13/13 distinct, wash 1.23, crash-park heal ratios 0.93-1.0), both
  red-teamed VULNERABLE (kicker-pulse cap-boundary farming;
  recovery-leg overpay; tranche-sized ratchet evasion; reconvergence
  overcharge), both v2-patched (kicker re-keyed to fast-vs-medium EMA
  separation — zero-mean pulses average out, the r11/r12 lesson applied
  to the kicker itself; ratchet re-keyed to displacement context + a
  quiet-time delivery credit), both SURVIVE re-attack; scored 6.29 /
  6.23 (oracle slightly below its predecessor's 6.36 — honest patching
  cost; joule above its 6.17). §21 battery records stored for both v2.
  Battery semantics lesson (open): crash_park's _drawn headline (600 =
  the EMAs moving to the new level) is the FIX working, not extraction;
  the heal_flags carry the real signal — a headline-metric nuance to
  fold into 4b disclosure assembly.
- Round 12 lineage-fix round (the r11 open question resolved by
  measurement): the Sustained-Band Forecast Fee Meter's residual
  (+487.45 pump_park / +295.76 vol_oscillation on B_m) was traced to
  the band centering on a 1000-anchored reverting trend EMA — a
  PERMANENT level shift integrates exceedance forever (eternal
  mis-banding). Superseded (SCORED -> SUPERSEDED, measured-design-flaw
  lineage) + successor Divergence-Gated Fee Band Meter (cand-a9f161bde5a8)
  whose v1 re-centers the band on the LEVEL itself via a fast/slow
  EMA divergence gate (a MACD construction): slow EMA T_t tracks X
  (wide 200..3000 clip — the r11 saturation defect), fast EMA L_f leads,
  band excess = sustained |L_f - T_t|/X beyond the band, vol-discounted
  (omega); asymmetric integral + 1.2:0.5 forfeit/comp; bounded
  re-centering-transient kicker preserves 13/13 scenario distinctness.
  Red-teamed VULNERABLE (intra-band free-riding, transient farming),
  patched to v2 with a transient-frequency counter C_t = EMA of the
  SLOW-EMA MOVEMENT (genuine re-centering only: oscillation moves X but
  leaves T flat, so the counter decays — the first draft keyed the
  counter and pool terms to |X-T| and REGRESSED wash to +498, caught by
  the smoke's wash gate before install), escalating drain
  (rho_c*C_t*8) + deflating compensation (rho_c*C_t*4) for repeated
  shift farmers; re-attacked: SURVIVES. Battery: 700 (r10 pred) ->
  487.45 (r11) -> 4.68 wash / 0.0 measured zeros elsewhere (r12 v2,
  §21 exp-c05613c1671c). Score 6.295 vs predecessor 6.245 — the first
  lineage fix to GAIN ranking points (r11's cost the score; r12's
  construction closed the residual without trading it away). Ops
  lesson: pre-storing a model from a mint script then answering the
  formalize request with it double-saves (formalize stores latest+1);
  the r12 flow extracts the stored row's JSON, deletes the pre-§15
  row, and lets the formalize replay be the canonical store — no
  duplicate rows minted at all.
- Round 11 measured-residual improvement round: the 4 finalists carrying
  the largest r10 §20 pattern-battery edges (Fee Oracle +14.75 F_l,
  Joule +351.83 J_t, Fee Meter +700 B_m, Corridor +784.99 U_t) were
  SUPERSEDED with the measured residual recorded as lineage and 4
  successors minted whose v1 models key the adversarially-sensitive
  state to a REVERTING EMA of the signed level path (T_t1 = T_t +
  kappa*((1000 + dX/X*1000) - T_t) — zero-mean oscillation washes out,
  sustained drift carries it; an integrating signed-EMA drifts forever
  and saturates, the 1000-reversion makes it a low-pass filter), plus
  small instantaneous kickers for whale-trace. All 4 smoke-gated
  13/13-distinct + non-degenerate + whale-distinguishable + wash-edge
  <=150 (achieved 1.98-5.81), red-teamed VULNERABLE (honest: EMA lag,
  patience extraction, kicker leakage), patched to v2 (asymmetric-kappa
  fast-EMA fees + kicker shrink; ratcheting drift threshold; vol-
  adaptive band + forfeit:comp 1.2:0.5; sign-independent |dX| crash
  circuit), re-attacked: all 4 SURVIVE. Battery re-measured: 3 of 4
  near-closed (784.99 -> 1.98, 351.83 -> 1.98, 14.75 -> 7.23);
  Sustained-Band Meter wash-flow closed (1.98) but pump_park still
  drains B_m (487) — traced to the band centering on the 1000-anchored
  trend, so PERMANENT level shifts look like eternal mis-banding;
  honest finding: that drain is stale-band forfeiture (the design's
  own consequence, no attacker P&L path), recorded in the r11 docs +
  4b numbers, open question: band should re-center on an EMA OF THE
  LEVEL. Ranking: Trend-Indexed Prediction-Fee Oracle 6.36 FINALIST
  (top-3); successors score below predecessors (6.17-6.36 vs 6.40-6.65)
  — honest §20-residual patching costs ranking points, exactly the §2
  trade. Ops lesson (the r9 double-save, new trigger): r11_models
  --store BEFORE the formalize answer install made the answers carry
  v1 content, and the formalize replay then bumped it to spurious v2
  rows (rationale = v1 rationale exposes it); fixed by deleting the
  spurious v2 rows + purging the stale improve requests minted against
  them (deterministic rids regenerate on re-run). §33 binding lesson:
  addressed_attacks must ALSO name the SECURITY/ORACLE vector
  phrasings (Jaccard >= 0.5 against THEIR text, not the red-team
  phrasing) or those findings stay unbound and the improve stage
  re-mints.
- Round 10 adversarial-residual bounding: the §20 AttackPatternBattery
  (vol_oscillation, wash_flow, pump_unwind, shock_timing) now runs
  against every finalist's FINAL model version and persists as §21
  experiment records (dataset='adversarial_patterns',
  scripts/r10_adversarial_residuals.py); the §27 release package's §4
  disclosure gained section 4b — MEASURED attacker edges vs matched
  base runs, code-assembled from the latest record (§2). Two §20
  honesty fixes pinned by tests: (1) the metric extractor only measured
  B_*/R_* stocks — S_/J_/G_/W_-named states were UNMEASURED and their
  models reported false "bounded by zero" headlines (now EVERY declared
  state is drainable; `test_every_declared_state_is_drainable`);
  (2) models with no measurable metrics at all now flag vacuous
  (headline=None), never headline=0.0
  (`test_unmeasurable_model_is_vacuous_not_zero`). Findings on the
  current finalists: rank-1 Prediction-Fee Fallback Oracle carries
  measured attacker edges +1.94..+14.75 (F_l fallback pool drain,
  O_p open-interest pool) under the four choreographies — disclosed
  in 4b; Joule escrow +288..+352 J_t drain under vol/pump patterns.
- Round 9 corpus-widening round: 10 bridge-authored ideas targeting
  the families ABSENT from the ranked corpus (governance,
  economic-driven, energy-driven, oracle-design) driven through the
  full §34 loop — all 10 modeled (battery-contract MathModels, 13/13
  distinct non-degenerate), all 10 red-teamed VULNERABLE with named
  profitable vectors, all 10 patched to v2 (multi-epoch baselines,
  escalation-proportional refund caps, probe corroboration, flow-gated
  slashing, delivery-keyed releases, provider weight floors,
  corroboration gaps, benchmark gap penalties, net-of-self-dealing
  weight, realized-stabilization vesting), all 10 SURVIVE v2 re-attack;
  3 new finalists (Joule-Bonded Inference Escrow 6.60 at #2, Bandwidth
  Bond Market 6.525 at #3, Demand-Index Escalation Ladder 6.40 at #5).
  Curriculum: ok — 12 families (was 11), all 57 ranked healthy,
  dominant market-driven 21%. Classification honesty: cross-family
  candidates classify by max token hits, so energy/oracle/economic
  PATTERNS landed in market/stablecoin/productivity families — the
  mechanism patterns are in the corpus even where the label straddles.
  Ops lesson pinned: bridge improvement proposals MUST carry the real
  candidate_id (improve rejects `unknown`); `--store` after formalize
  double-saves (auto-version bump, duplicate content) — scripts now
  skip existing v1 rows.
- Round 8 combination round (§18 × §34): the two unexercised §18
  pairs — market×prediction and oracle×prediction — each produced 5
  bridge-authored ideas driven through the full pipeline (15
  generated, 14 modeled/simmed/attacked/improved/retested/scored, 6
  finalists; top-5 of the ranking is now combination candidates,
  rank-1 Prediction-Fee Fallback Oracle at 6.65). The §18 combinator
  gate is SCORE-ONLY (a bridge≥0.05 AND-gate silently vetoed
  compat-only pairs; the CLI table already used score-only —
  `tests/test_combinator.py::test_gate_is_score_only_compat_pairs_
  emit` pins it). Prior-art persistence fix: sourceless
  PriorArtReports now still record their §12 evidence trail (the r8
  gap — `_persist_prior_art` saved rows only inside the
  sources loop; `tests/test_priorart_persistence.py`); all 14
  candidates carry authored prior-art rows. Model-equation
  discipline: relative |dX|/X responses, concave sqrt() compression,
  capped level terms, mean-reverting pools; v2 patches close the
  named attack vectors (rationing, dynamic barriers, probe
  corroboration, directional accuracy, verified-exposure
  compensation, slash-to-challengers). Curriculum: ok — 11 families,
  dominant 19%.
- Round 7 correction (evidence honesty): the 6 vacuous/cycle
  finalists + 2 replay-duplicates were SUPERSEDED with reasons
  recorded (innovation_claim lineage) and §26-archived; the 2
  cycle-evidence SCORED models likewise. Six successors were minted
  with lineage, formalized to battery-contract-compliant v1 models
  (13/13 distinct non-degenerate scenario trajectories), red-teamed,
  improved to v2 (claim-based addressed_attacks, verbatim attack
  names), re-tested (5/6 survives), and scored — the ranking's top 5
  is now ALL successors on real evidence. Improve-stage claim hygiene:
  addressed_attacks must name the stored attack vectors verbatim or
  the §33/§27 matching (name-slug/Jaccard) cannot bind the claim.
- Red teams attack the FORMALIZED model: CandidateBrief.formal_model
  carries the latest MathModel JSON into every adversarial prompt
  ('attack THIS design') — retest's re-attack targets the patched
  parameters, and changed model versions mint fresh bridge requests
  (no stale replays of pre-patch attacks).
- Score-stage honesty gate: RED_TEAM candidates with unresolved
  improvements (fresh profitable findings remain) are HELD, never
  scored on unfixed models; they resolve on the next run (§35).
- Improvement×Graph: the improve stage consults the §33 graph —
  prior fixes (other candidates' resolved attacks + fix
  rationales) render in the improver prompt (§32 reuse), and
  findings already ADDRESSES-ed by the current model version are
  deterministically filtered (Jaccard ≥ 0.5 token match): full
  convergence = honest stop, no re-patching. ADDRESSES edges are
  CLAIM-BASED: they derive from the improver's own addressed_attacks
  list (persisted agent-run output, name-slug or Jaccard ≥ 0.5 match),
  never a blanket claim over every profitable attack — a fix that
  never targeted an attack cannot close it.
- Archive: `src/blockchain_rd_lab/archive/` — §26 rejected-mechanisms
  index (ideas/rejected/index.{md,json}) with rejection reasons and §20
  flaw records; failed experiments are a research asset.
- Success criteria: §42 is TEST-ENFORCED — `tests/test_success_criteria.py`
  runs `pipeline --count 100` offline (corpus generator spans §24's 20
  domains; `src/blockchain_rd_lab/testing/corpus.py`) and asserts the
  whole funnel: 100 generated → 20 after the filter → 20 modeled/simmed/
  attacked/improved/retested → 5 finalists → 1 recommended + reports.
- Never issue tokens, deploy contracts, move funds, or spend significant API
  budget without explicit human approval.

## Commands

```bash
make dev        # lint + typecheck + test (run before every commit)
make lint       # ruff check src tests scripts
make typecheck  # mypy
make test       # pytest
```

## Code Layout

- `src/blockchain_rd_lab/schemas.py` — candidate, status machine, scores, experiments
- `src/blockchain_rd_lab/database/` — SQLAlchemy + SQLite repository (candidates, experiments, agent runs, sources, prior art)
- `src/blockchain_rd_lab/agents/` — agent base + LLM providers (mock, OpenAI-compat, local)
- `src/blockchain_rd_lab/discovery/` — Phase 1: agent, normalizer, deduplicator, service
- `src/blockchain_rd_lab/research/` — Phase 2: prior-art/economist/market agents, service, deterministic filter
- `src/blockchain_rd_lab/formalization/` — Phase 3: Mechanism Designer, MathModel schema + integrity checks, service
- `src/blockchain_rd_lab/simulation/` — Phase 4: equation interpreter, scenario battery, Monte Carlo, sweeps, Optuna
- `src/blockchain_rd_lab/redteam/` — Phase 5: adversarial agents, §20 fatal-flaw gate, redteam_results persistence
- `src/blockchain_rd_lab/ranking/` — Phase 6: deterministic scoring service, ranking, finalist selection
- `src/blockchain_rd_lab/reporting/` — Phase 7: dossier + lab report builders, §7 recommendation
- `src/blockchain_rd_lab/pipeline/` — Phase 8: §34 resumable pipeline orchestration
- `src/blockchain_rd_lab/archive/` — Phase 8: §26 rejected-mechanisms index
- `src/blockchain_rd_lab/improvement/` — §34 improve/retest loop (patched model versions)
- `src/blockchain_rd_lab/combinator/` — §18 mechanism combination engine (families, pair scoring, hints)
- `src/blockchain_rd_lab/cost/` — §31 budgets, response cache, usage ledger
- `src/blockchain_rd_lab/graph/` — §33 research knowledge graph (derived, deterministic)
- `src/blockchain_rd_lab/scoring/` — deterministic scoring engine
- `src/blockchain_rd_lab/cli.py` — Typer CLI (`lab`)
- `src/blockchain_rd_lab/testing/` — offline fixtures + §24 corpus generator (deterministic, 20 domains)
- `config/` — YAML configuration (lab, agents, scoring, research)
