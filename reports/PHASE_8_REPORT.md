# Phase 8 Report — Public Research & Pipeline

**Status:** complete
**Principle:** LLM proposes. Code tests. Evidence decides. (§2)
**Scope:** §38 Phase 8 — automated pipeline (§34), research archive
(§26), public release docs (§26/§27). This closes the §38 phase plan: all
§7 CLI commands are now implemented.

## Implemented

| Component | File(s) | Notes |
|-----------|---------|-------|
| §34 pipeline | `pipeline/__init__.py::PipelineService` | Full loop: discover → research → filter → formalize → simulate → redteam → score/rank → report (+ §26 archive build in the report stage). Each stage reports processed/advanced/errors; empty-input stages skip cleanly. Errors are recorded per candidate, never raised — a dead provider cannot kill a run (§35) |
| §35 resumability | `pipeline/__init__.py` | No in-memory checkpoints: **the database is the checkpoint.** Every stage consumes candidates by their §11 input status, so an interrupted run (`--stop-after <stage>`) resumes exactly where it stopped on the next invocation; already-advanced candidates are naturally skipped by their new status |
| Schema-aware fixture provider | `testing/pipeline_fixtures.py::PipelineFixtureProvider` | The key enabler for offline §34 runs: a MockLLMProvider subclass whose `complete_structured` inspects the requested output schema and synthesizes the correct deterministic fixture (IdeaBatch, PriorArt/Economist/Market reports, MathModel, four adversarial reports), parameterized by the candidate context parsed from the user message. Unknown schemas fail closed (§30). Same validation + storage path as a real provider — only the proposal is deterministic (§2) |
| §26 archive | `archive/__init__.py::ArchiveBuilder` | Rejected-mechanisms index (`ideas/rejected/index.md` + `index.json`): every REJECTED candidate with its rejection evidence — §20 confirmed fatal flaws (with categories) or funnel-cut reasons — sorted by category. Failed experiments are a research asset, not hidden (§26/§29) |
| CLI `lab pipeline` | `cli.py` | `--count/-n`, `--target/-t`, `--finalists/-f`, `--stop-after <stage>` (validated against the stage list), `--mock-fixtures`; Rich stage table with per-stage errors; resume hint on interruption; dry-mock fails closed (§30) |
| Public release docs | `README.md` | New **Methodology** (six-step evidence discipline), **Reproducibility** (§21/§26 guarantees), and **Research Archive** sections; stale "stub commands" note replaced with the pipeline description; phase table 0-8 ✅ |
| §7 completion test | `tests/test_cli.py` | The stub test is now a completeness test: every §7 command must exist as a real command — no stubs remain in the lab |

## Evidence (E2E demo, `database/lab.db`)

- `lab pipeline --count 10 --target 5 --finalists 3 --mock-fixtures`:
  **all 8 stages ran, 0 errors** — 10 ideas processed, 3 stored (7 dedup'd
  against existing ideas — correct §35 isolation, duplicates reported),
  3 researched → filtered → formalized → simulated → red-teamed → scored,
  finalists cut, reports + archive written.
- `--stop-after` interruption tested: run 1 stops after `research`
  leaving candidates at PRIOR_ART_CHECKED; run 2 resumes and completes —
  no candidate lost, no stage re-worked (§35 verified in tests).
- Archive: 5 rejected mechanisms indexed with honest reasons (2 confirmed
  §20 fatal flaws incl. the Phase 5 gate rejection; 3 funnel cuts) at
  `ideas/rejected/index.md`.
- Lab state after: 23 candidates — 5 FINALIST, 13 SCORED, 5 REJECTED;
  recommended candidate unchanged (`cand-1acbaa9de0b0`, §7).

## Tests

- 240 passing (was 233): `tests/test_pipeline.py` adds 8 tests — full
  fresh-lab run (all stages present in §34 order, candidates advanced
  through the machine, report + archive artifacts written), empty-stage
  skip behavior, dead-provider isolation (§35: pipeline completes, all
  errors recorded, no candidate lost), stop-after interruption + resume
  from database state, archive build (rejected entries with §20 evidence,
  Markdown + JSON indexes, empty-lab case), model defaults.
- `tests/test_cli.py`: TestPhaseStubs replaced by TestPhaseStubs
  completeness — the §7 command set (13 commands) verified registered.

## Lint

- `ruff check src tests` — all checks passed.

## Type checking

- `mypy` — no issues in 41 source files.

## Bugs found and fixed

- `ResearchFilter.apply` takes the database, not a candidate pool (wrong
  call signature in the filter stage).
- `FilterOutcome` fields are `considered`/`kept`, not `processed`/`passed`.
- `StageResult` has no `completed` field (stray assignment removed).
- `FIXTURE_BATCHES[0]` is a Pydantic `IdeaBatch`, not a dict —
  `json.dumps` blew up; now `model_dump(mode="json")`.
- Archive tests read the wrong paths (`tmp_path/index.md` vs
  `tmp_path/rejected/index.md`) and imported helpers from the `tests`
  package (not importable) — helpers inlined.
- Archive `_rejection_reason` checked `"very_similar"` but the enum value
  is `"very_similar_existing"` — class-B rejections would have fallen to
  the generic reason; fixed, and the generic reason now honestly points
  at funnel-cut/filter records.
- CLI `stop_after: str = None` (needs `str | None`); `MockLLMProvider`
  used-before-definition; unused imports; SIM102 nesting.

## Deliberate Non-Goals (Phase discipline, §39)

- No scheduled/automated daily-weekly cadence (§23's `reports/daily/`,
  `reports/weekly/`): the pipeline runs on demand; cron/scheduling is
  operational tooling outside the lab.
- No real-data ingestion (the §34 pipeline's historical stage runs on
  synthetic anchors; real datasets remain a data-phase item).
- No public git publication (GitHub push, docs site): the repo *content*
  is release-ready (README methodology/reproducibility/archive sections),
  but publishing is a human decision per §27's progression (open-source
  publication → community criticism → prototype → testnet → only then
  consider token).
- No charts in reports (deterministic Markdown tables carry the data).
- IMPROVEMENT/RETEST loop stages (§11/§34) not automated — the pipeline
  stops at report, which matches §38's phase scope.

## Known Limitations

- The fixture provider derives candidate context from user-message text —
  robust for this lab's prompt format; a real provider needs no such
  parsing (prompts are the same).
- Resume relies on status granularity: a candidate mid-stage (e.g. one
  of three research agents done) restarts its whole stage on resume —
  acceptable per §35 (no progress *lost*, possibly re-worked).
- The §34 "Improve / Re-test" stages of the master plan are future work;
  the state machine already has IMPROVEMENT/RETEST statuses reserved.
- Archive reasons for unresearched (class-E) rejections are coarse — the
  filter-stage details live in run records, not persisted per candidate.

## Conclusion

All §38 phases (0-8) are implemented, tested, and documented. The §7 CLI
surface is complete with no stubs. The lab runs its full deterministic
research loop offline, every phase honors the prime directive (§2), and
the repository carries its research record — including failures — as
the public artifact (§26).
