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
  deterministic code — a fatal verdict rejects only when the battery
  MEASURES a worst headline edge over the canonical FLAW_EDGE_THRESHOLD
  (400); the agent's profitability boolean is recorded metadata, never
  the trigger (r35); `lab redteam --mock-fixtures` runs offline.
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
  disclosure lists EVERY named attack surface the final model version
  carries — r36: the agent's profitability assertion is rendered
  metadata on each line, never a filter; strongest-honest-status per
  surface).
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
- Round 36 self-sweep (the r28/r34 discipline applied to the r35
  principle: after demoting the profitability boolean in the GATE, run
  the hostile pass over everywhere else it still has authority —
  found by grep, each verified by live execution before fixing; +5 →
  466). THE FINDING (the r35 class, ONE LEVEL UP, in the surface the
  world reads): §4 of the release package filtered every attack
  vector on `profitable_for_attacker` — `if not av.profitable_for_
  attacker: continue` — so an agent asserting unprofitable could
  suppress DISCLOSURE, not just evade rejection. Corpus census:
  341 of 742 vectors (46%) assert unprofitable — ALL were invisible
  in published §4. The successor's own published §4 said "No
  profitable attack remains unaddressed" while its final re-attack
  named surfaces including a FACT-level functionality failure
  (genuine-lead deadness: retention flat 0.300 through a 3%/step
  sustained grind, MEASURED) — the pre-r36 filter kept it off the
  honesty page. Two more authority sites found and fixed:
  the §34 improve loop (`_fixable_findings` filtered unprofitable-
  asserted vectors from what the improver ever sees) and the §33
  graph (metadata only — left as-is). FIXES: §4 now discloses EVERY
  vector with the assertion rendered as metadata on each line
  ("profitable-hypothesis" / "unprofitable-asserted") — the reader
  weighs it, never the code; the dedup tie-break keeps the MORE
  honest reading on a status tie (profitable-asserted wins);
  the §4 headline no longer says "no profitable attack remains"
  (it was only ever true of the filtered set) — it says the red
  team named N surfaces; the improver now sees EVERY vector
  (profitable-asserted ordered FIRST — attention allocation, not
  filtering) with the flag stated in the prompt. REGRESSION the
  sweep's own probes caught (fixed at the true root): the offline
  pipeline fixture provider parsed the improver prompt's findings
  lines with a regex that didn't know the new `- [agent; flag]`
  shape — zero findings parsed, the fixture fell back to a single
  generic claim, and the race-regression convergence test broke;
  the parser now reads both fields and carries the flag through
  (legacy pre-r36 prompt shape still parseable). PUBLISHED BUNDLE
  REGENERATED through the builder: the successor's §4 now ships 14
  named surfaces (was 0), every one previously filtered, each with
  its assertion flag; isolated third-party verify (/usr/bin/env
  -i, framework 3.12): exit 0 — 51 REPRODUCED + 2 CONSISTENT + 0
  NOT-REPRODUCIBLE. ALSO THIS ROUND (the r35 store follow-up,
  scripts/r35_audit_response.py): the suppression-vector store
  audit — 577 adversarial reports scanned, exactly ONE fatal
  verdict ever (the r33 case, profitable=true), ZERO candidates
  exposed to the pre-r35 fatal+profitable=false trigger — the
  gate vector never fired on real data (preventive, not
  corrective; no §11 question). §21 record stored (AUDIT-CORPUS,
  round 35, idempotent). Pinned by 5 probes: unprofitable-asserted
  vector publishes in §4 with the flag; the flag renders on every
  line; dedup tie keeps the profitable reading; unprofitable-
  asserted vector reaches the improver; profitable-asserted order
  first.
- Round 35 external-audit round-3 response (2026-09-15-auditor-FIXES.md,
  a second-pass hostile audit of the live public main; §2 applies:
  every finding VERIFIED against the live public raw files and by LIVE
  EXECUTION before anything was changed). ONE finding filed (F1 HIGH):
  "the live §20 gate still trusts strongest_attack_is_profitable; the
  r33 measurement fix is not present in the shipped redteam/service.py."
  VERIFICATION VERDICT — THE EVIDENCE IS REFUTED, THE FINDING'S
  STRONGEST FORM IS CONFIRMED. Refutation, by direct fetch of the live
  public raw file: main's service.py (413 lines) imports
  FLAW_EDGE_THRESHOLD (line 58), defines _measured_flaw_edge (189),
  and rejects only on measured_confirmed (the gate block 283-330);
  byte-identical to local HEAD (whose 461 tests pass). The audit's
  quoted predicate AND its "docstring describes the boolean as
  directly participating" sub-claim match the PRE-r33 blob (daf394f)
  EXACTLY, not the live file — and the audit's own header explains
  it: "The prior audit's fixed file is retained separately" (it
  reused its 2026-09-14 copy of service.py while fetching
  adversarial.py/interpreter.py fresh — internally inconsistent,
  since it CONFIRMS the r34 model_dump_json() cache fix that shipped
  in the same commits as the service.py fix it denies; CDN
  max-age=300 cannot hold a day-old blob). The committed audit file
  is kept verbatim; audits are evidence too, and this one records a
  stale-read — the same §2 lesson as the r27 F1 class: verify the
  audit against the artifact before acting on it. THE FINDING'S
  STRONGEST FORM (its remediation item 3, "treat the LLM boolean as
  hypothesis/metadata only") was then tested on the LIVE gate and
  found REAL, one level up: the boolean no longer DECIDED, but it
  still TRIGGERED — an agent asserting profitable=false suppressed
  the measurement entirely, shielding a model the battery would
  convict at 2266 (the suppression-direction hiding vector, the last
  residue of the trust bit). FIX (r35): every fatal verdict is now
  MEASURED; the boolean is pure recorded metadata; the measurement
  can acquit despite the assertion AND convict despite the denial —
  §20's confirmation instrument is the battery, not the agent's
  economics opinion (§20's own spec: "if a fatal flaw is confirmed:
  REJECTED" — confirmation is measurement's job). The dead
  not-triggered persist branch removed; the retest-path comment and
  Quick Reference updated to the measured-gate description.
  PINNED BY TWO PROBES through the full redteam_candidate ->
  _apply_findings path (the audit's item 6, which the r33 probes
  already covered end-to-end — the contradictory-evidence case
  test_fatal_verdict_high_assertion_low_measurement_not_confirmed):
  test_fatal_verdict_nonprofitable_is_still_measured (fatal +
  profitable=false + no model: measurement RUNS, §21 record shows
  the evaluation, fails closed for rejection) and
  test_fatal_verdict_nonprofitable_but_measured_flaw_rejects (THE
  SUPPRESSION VECTOR CLOSED: fatal + profitable=false + flawed
  model measured at 2266 → REJECTED; the agent's denial cannot
  shield a convicted model). 461 pass (+2); ruff/mypy clean. The
  audit's other sections (imputation floor, battery classification,
  interpreter) were re-checks of known/disclosed items and
  confirmed-fixed — no action needed beyond this round's work.
- Round 34 pre-audit sweep (the human's "let other llm audit
  again?" — the r28/r30 discipline: the lab runs its own hostile
  pass over the PREVIOUS round's new code BEFORE the external
  auditor, so the next audit finds nothing the lab could have
  found itself). Target: r33's own additions — the measured gate,
  the pin counterfactual, the constants fix. THREE defects found,
  all fixed at the generator, all pinned the day they shipped;
  +3 → 460. (1) COUNTERFACTUAL CACHE-KEY COLLISION (the serious
  one): the r33 cache key read (kind, steps, park_at, park_shift,
  sym) — omitting every OTHER calibration field the battery sweeps
  (harvest_shift, strikes, amplitude, wash_level, creep_rate,
  lag_fraction, strike_shift). The r33 sweep used ONE battery for
  all 27 runs per candidate: every calibrated variant INHERITED
  its kind's DEFAULT counterfactual verdict without computing its
  own. Benign this round — the full re-sweep under the fixed key
  reproduced the exact same 4-drift set, byte-stable — but a
  classification that ships because two computations COINCIDE is
  not one that was measured. Fix: the key is spec.model_dump_json()
  (complete deterministic serialization; differing specs cannot
  collide). Side catch: serializing specs surfaced a latent
  pydantic warning (float strikes into an int field) — fixed at
  both the sweep script (int-aware setattr) and the r22 test
  literals; 460 pass with zero warnings. (2) F3's CLASS REBORN
  IN THE F3 FIX: the interpreter comment SAID "one source of
  truth: import the canonical set" while the code REDEFINED the
  dict locally — adding a constant to formalization's
  _MATH_CONSTANTS (schema accepts) without a value in the
  interpreter (execution rejects) would have reopened the exact
  drift. Fix: the interpreter imports the canonical set, a
  module-load parity check raises on drift, and a test pins
  set(_CONSTANTS) == set(_MATH_CONSTANTS). (3) STORE HYGIENE (the
  r25 lesson, re-earned): six identical gate re-eval records had
  accumulated for cand-7f2f07fd4e9a (one per sweep re-run), plus
  duplicate r33 census records on re-run. The sweep script is now
  IDEMPOTENT: each re-run purges its own prior gate record and
  prior same-tag census before storing (re-run proof: exactly one
  of each). Also disclosed: the gate's measurement SCOPE (the
  eight DEFAULT calibrations; off-default robustness is the census
  layer's r22 sweep, published in §4b) is now stated in
  _measured_flaw_edge's docstring and pinned by test. Bundle
  regenerated through the builder; isolated verify (/usr/bin/
  env -i, framework 3.12): exit 0 — 51 REPRODUCED + 2 CONSISTENT
  + 0 NOT-REPRODUCIBLE, 8/8 + 19/19 headlines from the published
  files alone. The corpus is now staged for the next external
  audit at the same standard the last one validated.
- Round 33 external-audit response (the human delivered
  2026-09-14-auditor-FIXES.md: "they might be correct but might be
  wrong" — §2 applies to audits: every finding VERIFIED against the
  store and by LIVE EXECUTION before fixing; three findings, three
  confirmed, all fixed at the generator, each pinned by tests the
  day it shipped; +8 → 457). F1 (HIGH, the real one): the §20 gate's
  decisive economic predicate — rt.strongest_attack_is_profitable —
  was an LLM-SUPPLIED FREE FIELD: deterministic code whose fatal
  verdict rejected a candidate on an agent's unverified assertion
  ("deterministic gate" trusted a trust bit). Store ground truth: 16
  REJECTED candidates, exactly ONE via the §20 gate
  (Population-Linked Supply, 2026-09-04) — and it has NO stored
  MathModel and ZERO battery records: the one historical rejection
  rested entirely on the assertion. FIX: the gate now MEASURES —
  fatal+profitable rejects ONLY when the deterministic battery's
  worst headline edge on the latest stored model exceeds the
  CANONICAL FLAW_EDGE_THRESHOLD (400, now a library constant in
  simulation/adversarial.py, the same number every census since
  r16 used — gate and censuses can no longer drift apart);
  unmeasured (no model/vacuous/all under threshold) fails CLOSED
  for rejection; the LLM boolean is recorded as HYPOTHESIS (audit
  point 4); every gate evaluation persists a §21 record
  (fatal_flaw_v2_measured: verdict, hypothesis, measured evidence,
  decision — the audit trail point 5 asked for). The historical
  rejection got its gate-v2 re-evaluation record (evidence class
  documented; §11 correction stays the operator's decision, §2 —
  REJECTED is terminal by design, no resurrection path exists).
  Pinned by 3 probes incl. the audit's own regression: fatal+
  profitable+healthy-measured-model → NOT rejected; flawed model
  (the r20 multiplicative-ratchet class, worst edge 2266) →
  rejected with the MEASUREMENT in the flaw description.
  F2 (MEDIUM): the r19 long-window transit confirmation rebuilt
  the doubled-window spec from kind/steps/park_at alone — every
  other calibration field silently reset to dataclass defaults, so
  a calibrated variant's transit decision was made by the DEFAULT
  attack. Fix: spec.model_copy(update={steps*2, park_at*2}) — full
  calibration carried. F3 (MEDIUM): e/pi are §13-valid symbols
  (MathModel._MATH_CONSTANTS) but EquationInterpreter rejected them
  ("used but not declared") — a schema-valid model that could not
  execute; confirmed by live execution before fixing. Fix: the
  interpreter evaluates bare e/pi (declared variables still win —
  the schema is the contract). THE F2 FIX'S OWN FINDING (the round's
  real work): re-sweeping the calibrated grid under the fixed
  constructor surfaced a classification ambiguity the r18 pin rule
  cannot resolve by position — crash_park @-0.9 on the successor
  reads L_f_drawn 900.0: L_f (fast EMA) ends at 100.0 = BOTH its
  clip floor AND the crashed level. r18's Cyclic precedent (drained
  pool stopped at a floor that coincides with the level) says PIN =
  disclosed edge; but L_f measured INERT (relax the floor to -1e9,
  re-run the same attack: identical trajectory — the EMA converged
  to its fixed point, the clip never bound; X→50 probe: the only
  case the floor binds). Position cannot tell a stopped drain from
  a converged EMA; the COUNTERFACTUAL can. FIX: _pin_is_load_bearing
  (relax-and-rerun, cached per battery): final value unchanged →
  inert bound → the state ARRIVED (classifies by the layers that
  follow); final value moves below the bound → LOAD-BEARING → the
  r18 pin stands. Wired at all four guard sites (r15b arrival,
  EMA-shape filter, long-window confirmation, resonance
  quiet-tail). ANTI-HIDING caught live in the first draft: the
  draft's unbuildable-counterfactual branch returned INERT (False)
  — Cyclic's parameter-bounded floor (z_floor) would have
  exonerated a genuinely drained pool back into regime_tracking;
  the branch now fails CLOSED (unmeasurable is never exonerated),
  and parameter bounds resolve via their defaults so Cyclic keeps
  its pin. Pinned by 6 probes incl. all three historical pin
  lineages (Cyclic Z_t load-bearing; wage-pool W_t: 60-step
  draining → 120/240 pinned-and-convicted; swap-board B_t
  convicted). RE-SWEEP (both decision candidates, 8 defaults + all
  19 calibrations, r33 §21 records): incumbent — ZERO drift, all
  27 rows reproduce the published numbers exactly (r22's "zero
  edges >150 in 54 runs" claim SURVIVES the fix; worst 33.25);
  successor — 4 honest drifts, every one an honesty improvement:
  crash_park @-0.9 L_f_drawn 900.0 moves in_transit→regime_tracking
  (measured exoneration; honest headline G_t_drawn 0.869 unchanged),
  grind_harvest @-0.9 headline 0.8634→0.9739 (its transit now
  decided by its own attack), pump_unwind @amplitude=0.02 headline
  0.3374→0.0 with C_t honestly in_transit (confirmed by its own
  low-amplitude attack at the doubled window); worst headline
  UNCHANGED at 32.6375 (wash_flow @0.04, unaffected as predicted).
  VERIFIER BUGS the regeneration surfaced (both fixed at the one
  source, scripts/r25_verify_bundle.py, and re-shipped):
  sorted() over tuples containing dicts (TypeError under a fresh
  3.12 — the r30 isolated run's interpreter differs from this
  machine's; lesson: the isolated-environment proof must pin the
  interpreter, not just the PATH) and generation-overlap handling
  (the bundle JSON now carries r20+r22+r33 census records; both the
  calibrated re-run comparison and the §4b completeness check must
  take the NEWEST record per kind+calibration / count DISTINCT
  pairs — the same rule §4b renders by). Bundle regenerated through
  the builder (never hand-patched): isolated verify (/usr/bin/env
  -i, framework 3.12, no lab paths) exit 0 — 51 REPRODUCED + 2
  CONSISTENT + 0 NOT-REPRODUCIBLE, 8/8 defaults + 19/19 calibrated
  headlines reproduce from the published files alone.
- Round 31 §27 PUBLICATION (the human pushed; the ladder's
  publication stage is COMPLETE): the repo is public at
  https://github.com/nezzhang/AI-Blockchain-RD-Lab (56 commits,
  MIT license, main). §41 note: the human created the repo,
  fixed the GitHub email gate + token auth (password auth was
  rejected — the 2021 policy), and executed `git push -u origin
  main` personally; the lab never pushed on its own. POST-PUSH
  ACCEPTANCE, run the way any stranger would: (1) fresh
  ANONYMOUS clone of the public URL; (2) all 15 manifest
  sha256s verify against the copy GitHub serves — byte-identical
  from bundle to public copy; (3) the SHIPPED verify.py executed
  against the fresh clone in an isolated environment (/usr/bin/
  env -i, no lab paths importable): exit 0, 51 REPRODUCED + 2
  CONSISTENT + 0 NOT-REPRODUCIBLE, zero pycache — VERIFY-PASS
  FROM THE PUBLISHED FILES ALONE, the exact claim the README
  makes, now true at a public URL. The criticism stage now has
  its global surface: anyone can download the bundle, re-run
  the battery, and file findings (the r27/round-2 audit
  discipline, now open to the world). Ops notes: pushing the
  docs commit requires the human's authenticated session
  (gh auth / Keychain token) — the lab commits locally, the
  human pushes; and `git push` after email-gate fixes needs
  the USERNAME (nezzhang) not the account email in the
  username prompt.
- Round 30 pre-audit sweep for the approved highest-tier LLM
  auditor (the r28 discipline repeated at the new tier — the lab
  reads CODE now, so the sweep targeted the verifier's own
  coverage): ONE real gap found and closed. THE GAP: the README
  claimed verify.py "re-runs EVERY reproducible claim" while the
  re-run covered only the 8 default-calibration headlines — the
  19 calibrated-sweep variants published in §4b (with full-
  precision values in adversarial-bounds.json) were NEVER
  recomputed by the verifier; the round-2 auditor had verified
  them by MANUAL execution, which no third party would repeat.
  Same claim-vs-reality class as round-1 F3. FIXED IN THE
  VERIFIER (the shipped copy + scripts/r25_verify_bundle.py, one
  source): _compare_one() factors the run-and-compare (default or
  calibrated — the calibration tag IS a PatternSpec field
  assignment, 'amplitude=0.02' -> spec.amplitude = 0.02, the
  same mechanical construction the r22 sweep used to author
  it), and _rerun_attack_battery() now re-runs BOTH sets. Real
  bundle: 8/8 defaults + 19/19 calibrated = 27/27 headlines
  reproduce at machine precision. SECOND NEW CHECK (round-2
  audit F1 made structural): _verify_release_package() now
  counts calibration-tagged records per kind in the JSON vs
  @-tagged lines per kind in §4b — the exact 17-vs-19 bug is now
  IMPOSSIBLE to ship undetected (a dropped §4b line fails the
  verifier's NOT-REPRODUCIBLE class). PINNED BY TWO TAMPER
  PROBES (tests/test_verify_bundle.py, +2 -> 449): a drifted
  calibrated headline (self-manifested by a honest publisher)
  fails the sweep re-run AND its summary; a dropped §4b
  calibration line fails the completeness check. Verifier now:
  53 checks (was 33), 51 reproduced + 2 consistent + 0 not-
  reproducible, isolated third-party run exit 0, zero pycache,
  report beside the bundle. Also swept and found CLEAN: all 27
  §4b prose edges tie to JSON at 4-decimal precision (0
  unbacked); '13/13 scenarios clean' backed by the shipped
  record (13 scenarios, 0 failures, 0 degenerate flags, 13/13
  distinct final signatures); README sha256sum command executes
  verbatim 14/14 match (README.md correctly self-excluded);
  manifest 15 files, builder-regenerated (a hand-rolled re-
  manifest in the sweep hashed MANIFEST.json into itself and
  broke its own self-exclusion — the lesson re-earned: regenerate
  through the builder, never hand-patch the manifest); two
  Finder .DS_Store strays removed from lab-runtime/.
- Round 29 external-audit round-2 response (cand-9200b07691c3-
  FIXES-ROUND2.md — the auditor EXECUTED the bundle's own code:
  interpreter, scenario battery, Monte Carlo, and the full attack
  battery incl. all 27 default+calibrated variants; EVERYTHING
  REPRODUCED — round-1 fixes #1-#4 confirmed resolved under real
  execution, the strongest possible validation of the r27 work).
  TWO new findings, both confirmed. F1 (SHOULD FIX, the real bug):
  §4b rendered 17 of 19 calibration-tagged lines — the two
  pump_unwind sweep variants (@amplitude=0.02 edge +0.3374,
  @amplitude=0.1 edge +0.9999) existed in adversarial-bounds.json
  but never reached the disclosure document. MY FIRST FIX WAS A
  MISDIAGNOSIS (kept as the round's lesson): I patched "render
  from the FULLEST census record, not the newest" — wrong: the
  renderer ALREADY used the 27-bound record; the in-memory build
  still produced 17. The auditor's own 19-vs-17 numbers re-checked
  against the store localized the REAL cause: the §4b dedupe key
  was the CALIBRATION TAG ALONE — vol_oscillation and pump_unwind
  BOTH sweep amplitude=0.02/0.1, so whichever pattern rendered
  first added the tag and the other pattern's variants were
  silently skipped. Fix: the dedupe key is now kind+calibration
  (the same calibration under two patterns is two different
  measurements); §4b now renders 19/19 and the checklist
  "count per kind: JSON == markdown" passes for every kind.
  THE FULLEST-RECORD CHANGE IS KEPT anyway (it is more honest:
  "newest wins" would render 8 defaults if a newer default-only
  census landed; more measured bounds = more complete disclosure,
  ties keep newest) — but it was NOT this bug's cause. Pinned by
  TestRound2AuditCalibrationCompleteness (two patterns sharing a
  calibration name both render — 4/4 lines, the exact collision
  case). F2 (minor): verify.py's module docstring still said
  '.venv/bin/python scripts/r25_verify_bundle.py ...' — predates
  the self-contained runtime; now says 'python verify.py .'
  matching the README. ALSO THIS ROUND (not the auditor's): the
  r27 manifest-coverage probe caught a Finder-dropped .DS_Store
  inside the bundle — coverage now excludes non-content artifacts
  (__pycache__, .DS_Store) by explicit policy; anything else
  unlisted remains a real stray. Tests +1 -> 447; isolated
  third-party verify exit 0 (33 checks, 30 reproduced).
- Round 28 pre-audit sweep (the human's "I will ask other LLM to
  audit" — the lab ran its own hostile pass FIRST so the next
  auditor finds nothing the lab could have found): re-read the
  shipped README as an auditor would and executed its own
  commands verbatim. ONE real defect found and fixed: the README's
  sha256sum command hand-listed 9 files while the manifest ships
  15 — an auditor running the README's integrity step verbatim
  got a PARTIAL check (the six unlisted files included verify.py
  itself and the whole lab-runtime). STRUCTURAL FIX: the command
  is now GENERATED from the manifest keys (computed once, shared
  by README and MANIFEST — one source of truth, drift
  impossible), wrapped at 72 cols; pinned by two probes (command
  lists exactly the manifest's files; command EXECUTES verbatim
  and every hash matches). Also swept and found CLEAN: all 20
  §4b edges trace to adversarial-bounds.json at full precision
  (4-decimal render; the '13/13 scenarios' claim counts 'base'
  — ALL_SCENARIOS in the shipped runtime is 13 incl. base, and
  scenario-results.json keys match exactly); score 6.45 coherent
  across decomp/dossier/README; runtime closure complete on disk;
  isolated-environment verify still exit 0 (33 checks, 30
  reproduced, zero pycache). Tests +2 -> 446.
- Round 27 external-audit response round (the criticism stage
  arrived as a real artifact — cand-9200b07691c3-FIXES.md, an
  independent audit of the published bundle; §2 applies to audits
  too: every finding VERIFIED against the store before fixing,
  every fix pinned by a probe the day it ships). TRIAGE: 2
  blocking, 2 "check it yourself is false", 3 minor — ALL
  CONFIRMED REAL. F1 (BLOCKING, the worst): dossier.md's Game
  Theory and Security sections quoted the SUPERSEDED v1
  'vulnerable' verdict (round 1 of 3, 10:34) as current while
  the release package carried the final 'survives' (11:04) —
  the bundle contradicted itself about the same candidate. Root
  cause in the generator, not the file: _redteam_section's
  by_agent dict comprehension kept the FIRST record per agent
  across 12 rows/3 rounds. Fix: latest-per-agent overwrite
  (sorted by created_at, later rounds win) + a _verdict_line
  that max()es the red_team rows explicitly; the sections now
  lead with 'survives — Long-period alternation partial ride',
  exactly the final-round content the audit quoted from ids
  574-577. F2 (BLOCKING): the same generator dumped one shared
  block under four headings — Game Theory and Security were
  byte-identical, Economic Analysis and Market both dumped the
  full score list. Fix: agent_focus sections render their OWN
  agent's latest content + their OWN §19 dimensions; all 11
  dimensions now map to exactly one section each (regression
  caught by the suite: imputed dimensions initially rendered
  NOWHERE — candidate.scores holds only authored rows — now
  imputed dims render with an 'IMPUTED at the 5.0 floor' flag;
  two Python ternary-precedence traps in the section wiring
  caught before commit: a+b if c else d swallows the prefix).
  F3 (the "check it yourself" claim was FALSE): verify.py
  imports blockchain_rd_lab — a third party with only the
  bundle hit ModuleNotFoundError; the README said pip install
  from "the repo" but linked nothing. Fix: the full dependency
  closure measured (4 files ~100KB, stdlib + pydantic only) and
  SHIPPED as lab-runtime/ inside the bundle (interpreter,
  §15 + §20 batteries, MathModel schema); verify.py prepends
  it to sys.path and sets sys.dont_write_bytecode (bytecode
  inside the bundle would violate its own manifest coverage —
  caught live when the isolated run wrote __pycache__ and the
  coverage check failed on it; also: 'python verify.py .' with
  Path('.') has .name=='' — resolve() first or the report
  lands INSIDE as '-VERIFICATION.md', the stray-file lesson
  twice-earned). ISOLATED-ENVIRONMENT PROOF: /usr/bin/env -i
  with no lab paths importable — exit 0, 33 checks, 30
  REPRODUCED, clean environment, zero pycache. F4: the
  verification report's header printed the LITERAL text
  {__import__('datetime')...} — an f-prefix lost across
  implicit string concatenation (and datetime.UTC.datetime is
  not a thing); fixed, headers now render real ISO timestamps.
  F5: prior-art.json double-counted one multi-source review as
  two searches (identical finding JSON under source_ids 84 and
  85 — one blob that itself names both BIS sources inside
  similar_mechanisms); the bundle now dedupes identical
  findings and RECORDS THE MERGE (merged_source_ids), and the
  release package counts DISTINCT findings ('1 (2 source
  rows; identical findings merged, §12)'). F6: the '13/13
  clean' and Monte Carlo mean_final/failures figures had no raw
  backing file while every attack number had one; the final-
  version §21 records now ship as scenario-results.json
  (-scenarios-v3, -montecarlo-v3, -sweep-v3 excluded as
  adversarial-census duplicates) — same backing standard as
  adversarial-bounds.json. F7: the model's one open question
  ('can sustained genuine pressure hold the separation key high
  enough to farm retention?') lived only in model JSON; §4
  now renders the model's open_questions verbatim right after
  the residual list. THE AUDIT'S OWN VERIFICATION CHECKLIST is
  test-enforced (TestAuditChecklist: latest-round verdict in
  the dossier; sections distinct; score arithmetic; no literal
  template text). Tests +15 -> 444 (all seven findings probed;
  ops lesson: the first test draft patched
  LabDatabase._session as a CLASS attribute and 90 tests in
  the full suite failed from the leak — monkeypatch on the
  INSTANCE, never a bare class-attribute assignment; also
  lab report <id> prints the dossier, only bare lab report
  writes the files). The bundle is 12 files + runtime; every
  number reproducible from the published files ALONE, no
  package install, no repo, no database.
- Round 26 publication-hardening round ("make sure all these can
  publish with heavy study by others" — heavy study made a TESTABLE
  standard): a hostile expert with ONLY the published artifacts
  must be able to (1) reproduce every number, (2) find no absolute
  claim, (3) find no internal contradiction. The lab ran that
  audit on its own bundle BEFORE the critics do. PASS 1 — prose
  scan for §12-forbidden language (first ever / nobody /
  guarantee / provably / unhackable / novel-as-claim): CLEAN; the
  only ABSOLUTE/100% hits are MEASURED facts (the predecessor's
  flaw description, a heal ratio), and the §12 disclaimer ships
  verbatim. PASS 2 — prose↔JSON numeric linkage: every attack
  headline in prose ties to full-precision values in
  adversarial-bounds.json (4-decimal render; a first-grep false
  alarm resolved by precision analysis, not by trusting prose).
  PASS 3 — three REAL gaps found and closed: (a) the external
  verifier (r25) was not IN the bundle — a critic needed the
  repo; verify.py now ships INSIDE (the r24 builder copies it;
  tested by running the SHIPPED copy against the bundle from
  inside the directory — 8/8 headlines + 13 §15 scenarios +
  manifest all reproduce from the bundle alone); (b) the §19
  headline 6.45 had no recomputable provenance in the bundle —
  score-decomposition.json now ships every dimension's
  score/weight/weighted/imputed plus the recomputation rule,
  and the verifier RECOMPUTES sum(score*weight) = 6.4500 ==
  published, checks the README carries the same headline, and
  confirms the 5/11 imputation disclosure per dimension; (c)
  a stray -VERIFICATION.md (from a cwd-relative test write)
  violated manifest complete-coverage — removed; final audit:
  10 files, manifest complete, all hashes verify, weights sum
  1.00. README "How to verify" rewritten for the two-level
  self-service check (integrity: sha256sum vs MANIFEST;
  substance: python verify.py . — needs pip install -e . from
  the repo, stated honestly: the interpreter is code, and code
  is the only evidence that counts). Tests: verifier +score
  recomputation fixture (0-10 scale — the first draft's 0.56
  was a real scale bug the check itself caught); clean-bundle
  probe asserts the score recomputes and the imputation
  discloses; 429 pass. The bundle is now heavy-study ready:
  every number reproducible from the published files, every
  claim scoped, every artifact hashed.
- Round 25 external-verifier round (criticism made actionable —
  the §27 ladder's next stage after publication): a critic who
  downloads the bundle got static JSON and had to TRUST it; §2
  says evidence decides, so the published numbers are now
  CHECKABLE FROM THE PUBLISHED FILES ALONE.
  scripts/r25_verify_bundle.py reads ONLY the bundle (never the
  database), re-runs every reproducible claim with the
  deterministic interpreter, and writes
  bundle-<cid>-VERIFICATION.md NEXT TO the bundle (a post-manifest
  artifact about the bundle — inside it would break the
  manifest's complete-file-coverage invariant, caught by the
  round's own probe). THREE verdict classes, honestly separated:
  REPRODUCED (recomputed and matches — all 8 default-calibration
  attack headlines, the §15 13-scenario non-degenerate run, every
  manifest sha256), CONSISTENT (internally coherent, not
  re-computable from the bundle), NOT-REPRODUCIBLE (the bundle's
  own artifacts disagree). Real-bundle result: VERIFY-PASS, 16
  reproduced + 2 consistent + 0 not-reproducible, exit 0.
  THE ROUND'S OWN FIRST CATCH, BEFORE THE VERIFIER SHIPPED: the
  store audit found the r22/r23 §21 purge pattern NEVER COMMITTED
  — LabDatabase._session() closes without commit (every save_*
  commits explicitly inside the with-block; raw session.execute
  deletes rolled back silently while rowcount still printed).
  Twelve redundant/untagged sweep rows had accumulated
  (one untagged duplicate carried the PRE-wrap-fix incumbent
  worst-edge 63.86 — stale evidence sitting in the store beside
  the corrected 33.25); the r24 bundle had shipped 6 census
  records where its own brief claimed 2. Purged WITH commit,
  re-stored once via the tagged script: successor 2 census rows
  (r20 resonance + one 19-tag sweep), incumbent 7 (five battery
  generations + one sweep) — exactly the published claims.
  Brief, r23 packages, and r24 bundle regenerated from the clean
  store; manifest re-verified. Tests +5 -> 429 (clean bundle
  passes with >=8 reproduced re-runs; TAMPERED file fails the
  manifest; UNLISTED file fails coverage; DRIFTED headline
  self-manifested by the publisher still fails the re-run — the
  tamper case that matters, a publisher who re-hashes wrong
  numbers; the report lands beside the bundle, coverage holds).
  Probes found two verifier-draft gaps on the way (report
  placement breaking coverage; the drift probe's vocabulary too
  narrow — a vacuous-disagreement flag IS the catch, never
  silence). Ops: pyproject has no pythonpath — the verifier is
  imported by path in tests, the same way a third party runs it.
  §2 discipline at the boundary: the criticism stage now has a
  tool — a critic who doubts a number runs the same script and
  shows a verdict, not an opinion.
- Round 24 publication-bundle round (the human's "publish all no.1
  files" — §27/§41 approval IN HAND for the rank-1; the lab's part
  under §28/§41 is still STAGING, and staging is now COMPLETE):
  assembled the complete, self-contained, VERIFIABLE publication
  bundle for the §7 rank-1 (Separation-Keyed Fee Smoothing Escrow,
  cand-9200b07691c3) at reports/release/bundle-cand-9200b07691c3/
  — scripts/r24_publication_bundle.py, BY CODE from stored
  evidence only (§2). EIGHT files: README.md (what it is, how to
  verify, how to cite, scope+honesty: simulation-stage evidence,
  5/11 dimensions imputed at the offline floor, §4 residual list,
  no token/no deployment); dossier.md (§23 19-section research
  dossier, byte-pinned by manifest); release-package.md (rebuilt
  from the store via the r23 parameterized builder — one code
  path); model-v3.json (the final MathModel machine-readable);
  adversarial-bounds.json (every §20 census record, default +
  sweep calibrations, ALL classifications verbatim — the
  calibration-tagged r22 rows included); redteam-history.json
  (every adversarial report ever filed, unfiltered — the full
  v1→v3 break/fix history); prior-art.json (§12 trail);
  MANIFEST.json (SHA-256 + byte size of every file, excludes
  itself — self-reference impossible). VERIFICATION discipline:
  the manifest is verified by PROBE, not trusted from the
  generator — tests/test_publication_bundle.py (+4, the r19
  anti-hiding rule applied to a new artifact class the day it
  ships): manifest sha256s verify against disk; the manifest
  lists exactly the directory (nothing ships unhashed); the
  release package comes from the parameterized r23 builder with
  the honest explicit-subject note; hashes are stable under
  re-read (the human's posted copy stays verifiable). The real
  bundle was independently re-verified against the store after
  generation (score 6.45, model v3, 6 census records, 12
  redteam reports — manifest verifies True). Ops notes: the r24
  script surfaced the raw-JSON returns of get_latest_math_model
  (parsed, not dict-indexed) and ExperimentRecord.timestamp
  (not recorded_at); and writing the test fixture was itself a
  demonstration of §13 — the MathModel integrity check rejected
  three malformed drafts in a row (undeclared symbol X_t1,
  missing open_questions, missing rationale) before the fixture
  passed. NOT DONE by the lab, on purpose (§28/§41: the human
  acts with the repo's identity): git push to a public remote
  (none configured), posting to any blog/forum, minting any
  official-claims language beyond the staged files. The bundle
  IS the verbatim material; the human posts it. 424 pass.
- Round 23 three-option §27 staging round ("run the remaining
  options" — all three publication variants made literally
  buildable; the lab stages, the human posts, §28/§41): the r21
  brief's remaining options were publish-the-successor /
  publish-the-incumbent / publish-both-comparatively. Running
  them within the safety contract = building every option's
  package so the human's §27 call is a file copy, not a research
  project. THREE deliverables in reports/release/: (1)
  release-package-successor.md — the §7 rank-1's §27 package
  (the default path, restaged with the r22 sweep evidence);
  (2) release-package-incumbent.md — the same builder with the
  NEW candidate override (release.py build(candidate_id=...)/
  write(...): §27 is the human's decision, so ANY finalist must
  be a publishable subject, not only the rank-1 — the package
  header says 'finalist (explicit §27 subject — the human's
  selection, not the ranking's)'; (3) comparative-package.md —
  the both-option: Part A the decision brief + Part B the
  successor package + Part C the incumbent package, side by
  side, PRESENTED AND NEVER RANKED (§2: the comparative scores
  are the §19 deterministic output and the §21 measurement
  trail; the lab ranks nothing in prose). REFACTOR: the r21
  brief builder moved from script into the reporting library
  (reporting/decision.py, build_decision_brief(db, pair)) — one
  source of truth, any candidate pair; the r21 script is now a
  thin CLI driver. Robustness caught by its own test: the brief
  crashed on a candidate with NO stored model versions (max()
  over an empty list — candidates pre-formalization); now
  renders '(no stored model versions)' honestly — the brief
  renders whatever the evidence trail holds, never assumes
  depth. 4b CALIBRATION TAGS: the r22 sweep re-stored with
  per-variant 'calibration' tags and the release 4b renderer
  names them (wash_flow @wash_level=0.04, resonance @strikes=16
  ...) — 27 rows now read as 8 defaults + 19 named
  recalibrations, not 27 ambiguous lines; the successor's
  honest max renders as 'wash_flow @wash_level=0.04: attacker
  edge +32.6375' (the r14 regime-tracking design property under
  a non-park pattern, disclosed) and the incumbent's as
  'resonance @strikes=16 ... W_t_ratchet +29.0 re-basing in
  transit' (arriving at the doubled window — the quiet-tail
  layer classifying the arrival, which is why the sweep-max
  33.25 is a transit reading, not a standing ratchet; disclosed
  inline). Tests +3 -> 420 pass (explicit-candidate override
  builds the incumbent package with the honest subject note;
  custom filename+candidate write path; decision-brief library
  accepts any pair and RAISES on missing candidates — never a
  silently one-sided brief). Nothing was posted anywhere;
  publication remains the human's §27 act.
- Round 22 parameter-calibration robustness round (the r21 brief's
  own indicated next step, discharged — AND the round that caught a
  real measurement bug): the honest read of the r21 decision brief
  was that the 0.05 rank change rests on ONE agent judgment
  (oracle_feasibility) and that the evidence most directly
  supported ACCRUE STABILITY EVIDENCE before the human §27 decision.
  But a RE-RUN of the same battery adds nothing — the battery is
  deterministic. What made the incumbent's five-generation record
  was each NEW adversarial lens measuring the same construction
  clean. The r22 lens: PARAMETER-CALIBRATION ROBUSTNESS — the
  battery's defaults (strikes=4, amplitude=0.05, park_shift=-0.6,
  creep_rate=0.005, ...) are PUBLIC; a real attacker does not use
  the default calibration. The sweep (scripts/r22_parameter_sweep.py)
  runs every pattern at its default PLUS off-default variants
  (amplitude 0.02/0.10, wash 0.01/0.04, lag 0.1/0.4, park/harvest
  shift -0.3/-0.9, creep 0.002/0.01, resonance strikes 2/8/16 +
  strike_shift -0.3/-0.9) against BOTH decision candidates — the
  successor (the stability question) and the incumbent (the control).
  §21 records: battery 'attack_parameter_sweep', round 22, 27 runs
  per candidate. THE SWEEP IMMEDIATELY CAUGHT ITS OWN BUG (the
  round's real finding): the r20 RESONANCE craft WRAPPED when
  steps%strikes != 0 — the modulo restarted cycle phase in the
  window tail and crafted MORE strikes than labeled (steps=60:
  labeled strikes=8 measured 9, labeled 16 measured 20): the first
  sweep's bounds were real measurements of mislabeled calibrations.
  No committed r20 number was affected (every r20 run used exact
  divisions 60/2, 60/4, 120/8, 240/16); the mislabeled §21 rows were
  purged and re-stored. Fix in the craft: distribute the remainder
  — the first steps%strikes cycles get one extra ramp step, so
  exactly N strike-cycles tile exactly the window (base block
  recomputes the same tiling so final-cycle phase still cancels;
  int coercion on strikes). Corrected RESULT: BOTH constructions
  hold at every calibration tried — successor sweep max 32.64,
  incumbent 33.25, ZERO edges >150 in 54 runs (both far under the
  400 flaw threshold). The maxes are named and honest: the
  successor's is wash_flow at the elevated 0.04 wash level (L_f
  32.6 — the fast EMA OF the level tracking the elevated regime,
  verified end-gap 25.5 with the base at anchor: the r14
  regime-tracking design property surfacing under wash, a NON-park
  pattern the classifier does not cover; disclosed, not extracted)
  and the incumbent's is resonance at strikes=16 (W_t_ratchet 33.25
  — the r20 ratchet metric working on the incumbent's refund pool,
  catching what the default-calibration census read as 0.318).
  Under recalibration the successor's worst edge is the LOWER of
  the two. The stability question the r21 brief flagged is now
  MEASURED: closed in the successor's favor. The r21 brief was
  regenerated from the same script (census tables now show 2 and 7
  records; the 'accrue stability evidence' option is marked
  DISCHARGED with the finding; remaining options publish successor
  / incumbent / both — §27-human). Lesson (twice-earned): a bound
  measured only at the default calibration is a calibration
  artifact, not a bound — AND the act of sweeping found the bug the
  default never exercised: sweeping a choreography's parameters
  tests the MEASUREMENT CODE as much as the model; sweep the
  calibration the day the bound is claimed. Tests +2 (off-default
  calibration changes the run — exact N strikes crafted at every
  calibration incl. prime windows; sweep variants all non-vacuous
  — never a silent None-as-zero).
- Round 21 §27 decision brief: the recommended candidate changed
  in r20 for the first time since r15 (successor 6.45 over
  incumbent 6.40), and §27 publication is the HUMAN decision — so
  the round's deliverable is a COMPARATIVE DECISION BRIEF assembled
  BY CODE from stored evidence only (scripts/r21_decision_brief.py
  → reports/release/decision-brief-r21.md; §2: no report-writer
  LLM). It measures; it recommends NOTHING. What the assembly
  surfaced (all from §21 records + the deterministic scorer + the
  §33 claim-matched residual disclosure): (1) the ENTIRE 0.05 rank
  gap is ONE dimension — oracle_feasibility (+0.50 at 10% weight),
  a bridge-authored OracleReport judgment (r20-authored for the
  successor vs original-era for the incumbent); every other
  dimension is EQUAL. The rank change rests on one agent judgment,
  not a corpus-level difference — disclosed, not smoothed (§12).
  (2) The incumbent's stability evidence is DEEPER in census
  generations: five battery revisions (r14 crash_park → r20
  resonance) of flat worst-edge 0.318 — the same construction
  measured clean under every classifier the lab shipped. The
  successor's evidence is deeper in LOOP EXERCISE: three §15
  battery runs + the full v1→v3 improve/retest cycle (its v2 was
  honestly re-broken by re-attack and re-fixed). Different kinds
  of depth; neither dominated. (3) Residual honesty runs AGAINST
  the incumbent: the successor's final v3 carries ZERO open
  residuals; the incumbent's final v2 carries one OPEN vector
  (refund-cap exhaustion, arbitrageur, HYPOTHESIS) — in the brief
  verbatim. 5 of 11 dimensions imputed at the 5.0 floor on BOTH
  sides (offline mode; the corpus-wide §2 caveat). The brief's
  final section hands the human the open options WITHOUT ranking
  them: publish the successor / the incumbent / neither (accrue
  stability evidence first) / both as a comparative package. The
  lab measures; the human decides (§27/§28 — no token, no
  deployment, publication only on explicit human approval). Ops
  note: the brief builder reuses ReleasePackageBuilder's private
  residual matcher rather than re-deriving the §33 logic — one
  source of truth for the claim-match.
- Round 20 resonance round (the eighth battery pattern — the
  last claimed-but-never-measured vector class): red teams had
  asserted "transient farming" since r12; r19 proved a SINGLE
  strike's re-basing transient is not an edge — the adversarial
  response is to trigger that transient REPEATEDLY. RESONANCE: N
  strike-cycles at the model's own recovery cadence (strike ->
  deterministic ramp back to the 1000 anchor -> quiet beat), N=4
  default; matched base = ONE cycle placed at the pattern's
  LAST-cycle position — identical final-cycle timing, so
  window-end phase (slow-EMA lag, recovery-in-progress) cancels
  and the bound isolates exactly what the N-1 earlier cycles
  leave standing. MEASUREMENT DESIGN (three honest iterations of
  the metric): depth (_drawn) is structurally BLIND to
  repetition (a bounded per-cycle drain returns to the same
  level each cycle); the honest measures are (1) per-state FLOW
  (_cycled, total movement volume — the attacker's forced
  cycling cost, DISCLOSED, never headlined; the r17 attribution
  discipline: movement is not extraction until a consumer
  response pays it) and (2) the RATCHET (window-END value
  pattern-vs-base, per state — what N strikes leave standing vs
  one; computed at matched final-cycle timing so full-re-basing
  designs read 0 by construction). FINDINGS (census over 27
  ranked, before dispositions): 2 flaws >400, 3 transit, rest
  healthy. FLAW 1 — Vol-Weighted Fee Smoothing Escrow (FINALIST,
  1321): vol-indexed retention ratchet — retention keys ABSOLUTE
  vol (eta=40 pins r_t at the 0.9 ceiling through every crafted
  ramp) while the outflow term is 0.05*sigma weaker, so every
  cycle over-retains monotonic; 285 -> 1321 -> 2143 -> 6479
  LINEAR-unbounded in N, persists under quiet (1321 -> 1081).
  FLAW 2 — AI-Compute Denominated Debt (the r16 duplicate-block
  EXEMPLAR, 3583): the multiplicative-supply r16 class at
  resonance scale — S_t1 = S_t*(1+g_t) compounds every recovery
  ramp (13 consecutive same-sign steps per cycle; no prior
  pattern had them, which is why the r16 census measured only
  the oscillation leg): 3583 -> 24352 -> 666931 EXPONENTIAL in
  N. Both SUPERSEDED with measured lineage. The class's r16
  successor (Reversion-Keyed Demographic Reserve, additive flows)
  is resonance-healthy at 32.6 and carries FLAW 2's fix lineage
  — NO second mint (one exemplar successor per flaw class, the
  r16 discipline). FLAW 1's successor minted fresh:
  Separation-Keyed Fee Smoothing Escrow (cand-9200b07691c3)
  through the full §34 loop — v1 (integral-form escrow) CAUGHT
  BY ITS OWN SMOKE at n=8 (ratchet 238: the draft had copied the
  predecessor's integral structure — the flaw class itself);
  rebuilt as a bounded REVERTING TARGET (buffer = anchor +
  cap*retention, the corpus's resonance-healthy designs are all
  EMAs of bounded targets: cycle-average convergence, N-
  independent by construction); v1 red-teamed VULNERABLE (saw-
  tooth retention bias: the v1 clip band [0.1, 0.9] gave up-legs
  +0.6 but down-legs only -0.2, so zero-mean saw-teeth biased
  the retention time-average above base); v2 symmetric band
  delta_r±0.25 + a magnitude-keyed saw counter — honestly
  RE-BROKEN by the re-attack (the counter's magnitude threshold
  8 has a flat zone under it to ride, and its other side is
  worse: a fast GENUINE grind also has large fast-EMA movement,
  so the counter pinned at 1.0 and retention stayed flat 0.300
  through a 3%/step sustained move — the smoothing function
  dead exactly when genuinely needed; the smoke's genuine-lead
  probe caught the same deadness pre-install); v3 SIGN-
  PERSISTENCE counter (g_t*G_t, G_t the lagged separation:
  alternation raises the counter at ANY amplitude — no
  threshold to ride; persistence decays it — the genuine
  response rides): measured slow-saw 0.300 = base exactly,
  duty-cycle saw 0.300, genuine lead 0.428 -> 0.473, resonance
  heads [0,0,0,0] at N=2/4/8/16. SURVIVES re-attack; 6.45 —
  above its predecessor and above Demand-Index 6.40, the FIRST
  successor to take rank 1 (5 of 11 score dimensions imputed at
  the 5.0 offline floor, like every candidate). TRANSIT (the
  quiet-tail layer, r19's discipline applied to repetition —
  the r19 long-window confirmation doubles the window, which a
  dynamically-crafted pattern cannot do; the resonance analogue
  appends QUIET steps at the anchor to both runs and re-
  measures the pattern-vs-base gap: closes < 25% of window-end
  = recovery-in-progress, in_transit; persists = a true
  ratchet, stays an edge; the r18 pin rule holds): Relay
  Congestion Cover Mesh 362 -> 0.0, Counter-Cyclical Fee Sink
  Insurer 310 -> 0.0, Persistent-Drift Joule Escrow 304 ->
  111.6 (its disclosed U_s lag) — all close; the r18/r19
  successors and the recommended candidate all healthy
  (Symmetric-Cap 156 -> 2.5 disclosure-only U_z; wage pool 127
  -> 69.5 disclosure-only S_w; Demand-Index 22.7 -> 0.0).
  Corpus: 26 ranked, curriculum ok (10 families, dominant 23%);
  census (battery attack_patterns_v7_resonance, 8 patterns, §21
  for all 26): median worst-edge 13.8, ZERO edges >400 —
  convergence holds under the repetition pattern; worst
  survivors are disclosed design properties (299.7 allocation
  pass-through, 256.8 mutual drawdown). Tests +5 (craft shape:
  full recovery each cycle; base = one LATE cycle at the
  pattern's final position; reverting pool transit not
  ratchet; vol ratchet stays visible, never in_transit;
  _cycled/_final disclosed never headlined). 415 pass. Lesson:
  a metric blind to the attack it claims to bound is a false
  "bounded by zero" claim in disguise — depth metrics cannot
  see repetition; measure what the Nth cycle leaves standing
  (ratchet), disclose what it forced (flow), and confirm
  transit with the pattern's own rest probe (quiet tail).
- Round 19 window-robustness audit round (the r18 lesson made
  systematic: "every window-end-only classification is window-length
  sensitive — measure the DIRECTION, not the endpoint"): ran the
  park-style battery at 60/120/240 steps over the whole ranked corpus
  and flagged every candidate whose edge classification FLIPS with
  window length (>100 swing). Three flips found; the diagnosis split
  them honestly: (1) Symmetric-Cap (the r18 successor, 340 -> 394 ->
  0.0) — the reserve is in slow transit toward its demand-EMA target
  at 60/120 steps; convergence verified monotone-stable at 400 steps
  (Z-T gap 103 -> 50, the design's drip steady-state; no
  undershoot): HONEST-NEGATIVE, the audit's control case. (2)
  Level-Recentered (266 -> 230 -> 136) — the longer grind raises
  BOTH pattern and matched creep-only base, so the difference
  shrinks: the r18 matched-base subtraction working as intended. NO
  FLAW either. (3) Productivity-Index (188 -> 400 -> 400):
  CONFIRMED FLAW — the wage pool's clip floor 600 sits ABOVE the
  -60% crash level 400 (the r15 bandwidth class exactly: the flow
  IS symmetrically step-capped ±40 but the floor blocks re-basing,
  so W_t pins at 600 under the moved regime; the 60-step window
  read only 188 because the pool was still DRAINING toward the pin —
  the audit's whole point: short-window-only classification had
  hidden the pin behind a transit reading). Superseded + successor
  Regime-Indexed Compute Wage Pool (cand-412f176470fb): single-
  magnet bounded-step regime EMA (±500/step — battery extremes
  reach X=706k, a value-clipped EMA saturates; three §15 smoke
  iterations to 13/13 distinct), symmetric ±f_c flow cap with
  floor 250 < crash 400, delivery kicker, stress memory S_w
  disclosure-only; red-teamed VULNERABLE (flow-cap boundary
  riding; S_w pre-loading), v2 sqrt-compressed quadratic ramp +
  S_w pinned disclosure-only by constraint, SURVIVES; 6.255, rank
  10 of 27. BATTERY gained TWO classification layers, both
  NUMERIC (no structural inference, the r17 discipline): (a) the
  r19 LONG-WINDOW ARRIVAL CONFIRMATION — a park-style excursion
  still standing at the measured window is re-run at 2x window;
  if the state has arrived by then (within 10% of the level, not
  pinned — the r18 pin rule holds at every window) it is disclosed
  as in_transit re-basing, never an attacker edge (the wage-pool
  successor's own 60-step 468 excursion was transit, 0.0 at 120);
  (b) the r19b TARGET-RELATIVE ARRIVAL — a state whose update
  reads another STATE (a declared target) arrives at its DESIGN
  RELATION to the target, not at the raw level: the Symmetric-Cap
  reserve ends 50 above its demand EMA under crash_park — the
  SAME +50 drip offset the base run carries (50.0 vs 47.4
  measured) — the pool fully re-based to its design equilibrium,
  and the raw Z-vs-X reading (485 "edge") over-attributed a
  structural offset the model has whether attacked or not;
  measured at the long window: pattern-vs-target offset ≈
  base-vs-target offset within 10% of the target = followed the
  regime. TWO ANTI-HIDING CATCHES in the same round, both caught
  by probe before any commit: (i) the first r19b draft compared a
  state to its OWN next-symbol (the §14 feedback puts S_t1 in the
  history; offsets matched trivially) and re-hid the Treasury
  anchor-heal + both floor-pins — the target must be a DIFFERENT
  declared state; (ii) the v5 separation-predicate's self-read leak
  (fixed r18 but its census consequences only surfaced now):
  the Output-Indexed swap board's B_t pinned at its 500 floor at
  ALL windows 60/120/240 (the same floor-above-crash-level class,
  a SECOND instance) — hidden in every census since r16 by the
  leak, exposed by the corrected rules; superseded (the audit's
  post-fix finding; the wage-pool successor carries the family).
  Corpus: 27 ranked, curriculum ok; census (battery
  attack_patterns_v6_window_confirmation, §21 for all 27):
  median worst-edge 4.0, ZERO edges >400 — convergence holds
  under the window-robust classifier; worst survivors are
  disclosed design properties (299.7 allocation pass-through,
  256.8 mutual drawdown — insurance semantics). 4b renders the
  in_transit class in both zero-edge and positive-edge variants
  ("re-basing in transit (confirmed arriving at a doubled window,
  or resting at its base-run offset from its design target)").
  Recommended unchanged: Demand-Index Escalation Ladder 6.40.
  Tests +4 (slow-pool-transit-not-headlined; floor-pin never rides
  arrival back in; anchor-heal never rides arrival back in;
  in-transit 4b render). 410 pass. Lesson: a classification layer
  needs its OWN anti-hiding probe the day it ships — run the
  superseded set through the new rule before trusting it.
- Round 18 compound-choreography round (GRIND_HARVEST + TWO
  classification-bug fixes + 4 supersessions): added the seventh
  battery pattern — creep `grind_fraction` (0.5) of the window at
  +0.5%/step then a one-shot `harvest_shift` (-0.6) strike into the
  loaded system, park; matched base is CREEP-ONLY (isolates what the
  timed strike adds). The compound found TWO candidates whose edges
  the single-pattern battery read as zero — and diagnosing WHY
  exposed two window-sensitive classification bugs, both fixed in
  the measurement layer: (1) PIN-AWARE ARRIVAL — Cyclic's Z_t sat
  EXACTLY at its 400 clip floor, which EQUALS the crashed level 400,
  and the r15b arrival check (|final - X| < 10% of X) read the pin
  as 'tracking the level', hiding a fully-drained pool (its inflow
  cap min(200, 0.10*(X-1000)) has NO mirrored outflow cap — the
  pool bleeds ~60/step under any sub-anchor regime; 509.7 standing
  under crash_park, 579.0 under the compound). A state AT a declared
  clip bound was STOPPED there, it did not arrive; the amendment
  (applied to BOTH the r15b arrival check and the r14 EMA-shape pop)
  keeps pins as disclosed edges. (2) HEAL-CONTRADICTION GUARD —
  Treasury's V_t (a 1000-anchored vote-signal EMA) heals toward its
  anchor while X parks at 400; at the 60-step window end its
  displacement sits under the 25% transient threshold and the r15
  transient check popped the 600 edge as 'recovered' — the r13
  anchor-heal flaw class HIDDEN by the honesty fix itself. The guard
  requires a transient to recover NEAR the moved level (|final - X|
  < 25% of X); anchor-heals stay visible (the honesty fix must not
  become a hiding place — pinned by the r15 standing-drain test,
  which caught a first-draft separation-consumption class that would
  have hidden the same drains a second way). Census under the fixed
  classifier re-exposed TWO more pre-r18 hidden edges (Adverse-
  Selection I_t/A_t heal to 1000 exactly — excursion 750, the r13
  class on clearing cover; Belief-Weighted V_t floor-pin 301.3, the
  uncapped-outflow family) — 4 SCORED candidates superseded with
  measured lineage (2 per flaw class, r16 exemplar discipline: ONE
  successor per class): Three-Speed Adverse-Selection Premium
  (cand-dcde8a9d5b19, the r13 insurance polarity on clearing cover;
  v2: sqrt-compressed quadratic premium ramp — monotone marginal
  cost kills the cap-boundary cliff; kicker gated on separation
  context — pulse farming stops paying; SURVIVES re-attack; 6.265)
  + Symmetric-Cap Fee Recycle Reserve (cand-47db6e78b1ea, the
  mirrored outflow cap f_t = clip(r_f*dX/X*1000, -f_c, f_c); v2:
  quadratic ramp near the boundary kills the flat riding zone; the
  utilization index U_z pinned DISCLOSURE-ONLY by an explicit
  constraint; SURVIVES; 6.255). Separation-consumed anchors
  (EMA-anchors whose consumers key the DIFFERENCE — the class-A
  successor's ultra-slow U_s lags 385.7 by design; its premium keys
  |I-U_s|) excluded from park-style headlines, narrowed after
  review to anchors whose OWN update reads another state (a pool
  keyed to a stress aux is a drainable stock, not an anchor).
  Corpus: 28 ranked, 10 families, dominant 21%, curriculum ok;
  census (battery attack_patterns_v5_grind_harvest, §21 records for
  all 28): median worst-edge 2.2, ZERO edges >400 — convergence
  RESTORED under the corrected classifier; worst survivors are
  disclosed design properties (299.7 allocation pass-through, 96
  corridor U_t standing). Recommended unchanged: Demand-Index
  Escalation Ladder 6.40 (grind_harvest renders in 4b: no positive
  edge + F_t 33%/W_t 79% heal disclosure). Tests +7 (two-phase
  craft, creep-only base, compound edge bound, pin-not-arrival,
  anchor-heal-not-transient, genuine-transient preserved, separation
  anchor excluded). 406 pass. Lesson (re-learned): every
  window-end-only classification is window-length-sensitive —
  measure the DIRECTION (toward anchor vs toward level), not the
  endpoint.
- Round 17 drift-creep choreography round (new pattern → new
  disclosure layer; zero new flaws): added DRIFT_CREEP to the §20
  battery — the boiling-frog family: a constant sub-threshold grind
  (+0.5%/step, +35% cumulative) that never trips any single-step
  spike trigger. The motivation was §2 itself: the r16 v2's central
  claim ("drift-paced farming closed by the separation key") was
  red-team HYPOTHESIS, never measured — the battery had no drift
  pattern. Measurement design took three honest iterations:
  (1) the generic _drawn metric is BLIND to drift (both pattern and
  base runs move their states; the lag-vs-level cancels in the
  subtraction) — first probe showed the r16 v2 at headline 0.0 while
  its states sat 266-337 below the drifted level;
  (2) the per-state WEDGE metric (|state - X| at window end, pattern
  vs base) exposed the lag — but wedge-on-every-state FALSE-POSITIVEd
  (a pressure-keyed fee 40% off the level is not "lagging"; a slow
  anchor whose consumer keys the SEPARATION lags 326 while the
  harvestable quantity stays at 1.04). Fixes: a level-denomination
  gate (wedges only for states at level scale in the base run,
  within 25% of X) and ATTRIBUTION HONESTY — a wedge enters the
  attacker-edge headline ONLY through a measured consumer response,
  never by structural inference: the lag itself is a RESPONSIVENESS
  gap (disclosed per state as drift_wedges on the AttackBound),
  and asserting harvest from keyed-shape alone would over-attribute
  (the r16 v2's slow anchor is keyed, but its consumer keys the
  anchor separation, which correctly stays tiny).
  VERDICT BY MEASUREMENT: the r16 v2 separation-key claim SURVIVES
  (drift headline 0.0; its harvest quantity — separation — stays
  ~1.04 under drift vs 0.04 base). Corpus census under the 6-pattern
  battery: NO new attacker edge above threshold anywhere (max drift
  headline 64.2 = the Joule's quiet credit Q_c paying during a GENUINE
  sustained regime move — insurance semantics, the r13 design doing
  its job; 48.4 = the bandwidth successor's P_a tenure-denial, the
  same small griefing vector r15 measured under oscillation, now seen
  under a second pattern). Drift WEDGES are large across the corpus
  (177-330) — a UNIVERSAL responsiveness lag of level-denominated
  states under grinding regimes, now disclosed per state in §4b
  ("lags the drifted level by +N more than base; design lag, not an
  extraction"). Release 4b renders the drift line (both zero-edge and
  positive-edge variants). §21 r17 battery records stored for all 30
  ranked candidates. Tests +4 (craft shape: constant grind no spike;
  fast tracker small wedge; slow state wedge disclosed not headlined;
  non-level states skipped by the denomination gate). No supersede,
  no successor — the pattern found a DISCLOSURE class, not a flaw
  class: the strongest possible outcome for corpus honesty. 399 pass.
- Round 16 convergence-census round (the r15 queued work + the corpus
  honesty debt): (1) recommended-candidate triage — Demand-Index
  Escalation Ladder's 4b heal signature ('F_t retains 0% of peak')
  classified BY POLARITY: the premium keys PRESSURE (dX-based u_t),
  not LEVEL — parked dX=0 is genuine pressure quiet, the r13 flaw
  class does not apply; its W_t 33% refund retention + F_t edges
  +0.32 stay honestly disclosed. (2) CORPUS-WIDE CENSUS under the
  final battery (r13/r14/r15 classifications) — the convergence
  probe that answers 'is anything profitable left undisclosed?'
  Found TWO pre-r10 debts the era-specific remediation passes missed:
  (a) a 913.5-cluster — 6 candidates with IDENTICAL equation sets
  (an EMA-divergence MULTIPLIER S_t = S_t*(1+clip(alpha*(X_smooth-X)/X))
  whose pool collapses -94% under vol_oscillation, 1000 -> 60 measured)
  + Attestation-Locked 700 (A_b pump_unwind) + Fee-Tier Registry 494.7
  + Vol-Adaptive Rebate 386.2 — all 9 superseded (measured-pool-collapse
  lineage); exemplar successor Reversion-Keyed Demographic Reserve
  (cand-47c62aa507b4) minted with the r11 primitive at additive scale:
  reverting-EMA signal + ADDITIVE bounded flows (no multiplicative
  ratchet to compound down-legs; 913.5 -> 0.00 vol_osc) — red-teamed
  VULNERABLE (drift-paced flow farming — patience turns the flow cap
  into a slow tap; anchor-band standing drain), v2 (flow re-keyed to
  T-vs-slow-anchor SEPARATION, the r13 three-speed pattern; drain
  routed to a disclosed beneficiary sink), SURVIVES; 6.25.
  (b) THE DUPLICATE-CONTENT CENSUS (equation-set signature over the
  ranked corpus): TWENTY candidates share ONE identical equation set —
  the pre-r10 corpus block (Demographic Reserve Rule x5, Carbon-Weighted
  Gas Fees x4, Habitat Bond Curve x4, Labor-Backed Escrow x2,
  Commodity-Volatility x2, Population-Linked Supply, Bandwidth Futures,
  AI-Compute Debt) — ALL scoring the 5.050 imputed-median floor, 41% of
  ranked slots, THREE holding FINALIST positions: the r7 vacuum at 2.5x
  scale and the hidden driver of the curriculum's 'dominant 19-21%'
  readings. 19 superseded as duplicates (rank-order exemplar kept,
  cand-1acbaa9de0b0); the family's honest successor already exists
  (cand-47c62aa507b4). Corpus: 57 -> 30 ranked, 11 families, dominant
  23%. CONVERGENCE REACHED: 0 edges above the 400 supersede threshold,
  median worst-edge 14.3, every top residual a DISCLOSED design
  property (allocation pass-through 299.7, mutual drawdown 256.8 —
  insurance semantics). The lab's research loop has converged; what
  remains is the HUMAN §27 publication decision. §21 census records
  stored for all superseded + the successor. 395 pass.
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
