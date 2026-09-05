# Phase 7 Report — Reporting

**Status:** complete
**Principle:** LLM proposes. Code tests. Evidence decides. (§2)
**Scope:** §38 Phase 7 — automated research reports, Markdown, experiment
summaries (§23 dossier structure, §7 recommendation tail).

## Implemented

| Component | File(s) | Notes |
|-----------|---------|-------|
| Report schemas | `reporting/__init__.py` | `ReportSection`, `CandidateDossier` (with `to_markdown()`), `LabReport` (with `to_markdown()`), `ReportOutcome`. Missing evidence renders as honest `_(no recorded evidence yet)_` notes — never dropped sections, never fabricated content (§29) |
| §23 dossier structure | `reporting/service.py::SECTIONS` | All 19 fixed sections in spec order: Executive Summary, Problem, Mechanism, Mathematical Model, Economic Analysis, Game Theory, Oracle Design, Security, Simulation, Historical Analysis, Prior Art, Competitors, Market, Technical Architecture, Regulatory Risks, MVP, Risks, Open Questions, Recommendation |
| ReportBuilder | `reporting/service.py` | **Assembled by code, no report-writer LLM** — dossiers draw on stored candidates + dimension scores (with §29 evidence levels and confidence), `math_models` (variables, equations, parameter ranges, §13 open questions, critical assumptions), §21 experiment records (seed, version, results), `redteam_results` (verdict, attack-vector counts, §20 flaws), `prior_art`. Same DB state → byte-identical reports |
| §7 recommendation | `service.py::build_lab_report` | The single recommended candidate is the rank-1 finalist — deterministic (score desc, stable name tiebreak), completing §7's "5 finalists → 1 recommended candidate" tail |
| Lab report | `service.py` | Funnel summary: total candidates, per-status counts, finalist list, recommended id, §20 gate-rejection count, full ranking table |
| CLI `lab report` | `cli.py` | `lab report [candidate_id]` — single-candidate dossier printed to console (with rank if scored); batch mode writes one dossier per FINALIST to `reports/finalists/<id>.md` plus `reports/lab-latest.md`, then prints the artifact table + recommendation; `--no-dossiers` for the lab report alone |

## Evidence (E2E demo, `database/lab.db`)

- `lab report` over the 5 FINALIST candidates: **5 dossiers written**
  (`reports/finalists/cand-*.md`) + `reports/lab-latest.md`.
- **§7 recommendation:** `cand-1acbaa9de0b0` (AI-Compute Denominated
  Debt) — rank-1 finalist, selected deterministically.
- Verified dossier content: §23 sections all present; mathematical model
  rendered with equations, parameter ranges, §13 open questions, and the
  critical-assumption flag; adversarial verdicts with vector counts
  (oracle vectors correctly counted from `manipulation_vectors`);
  simulation §21 records with seed + reproducibility note; §12 forbidden
  novelty language absent.
- Lab report: funnel status (5 finalist / 10 scored / 5 rejected / 20
  total), ranking table of 15, gate-rejection count.
- Determinism verified in tests: two `write_reports` runs on the same DB
  produce byte-identical dossiers.

## Tests

- 233 passing (was 216): `tests/test_reporting.py` adds 17 tests —
  rendering (§23 section list matches spec exactly, all sections render,
  honest missing-evidence notes, lab-report table), dossier builder
  (full-evidence dossier with model equations + parameters + open
  questions + scores, §12 language discipline, missing-evidence
  sections, fatal flaws in Risks + metadata, §21 experiment rows with
  seed), lab report (recommendation = rank-1 finalist, deterministic
  across runs, status + gate counts), artifacts (dossiers + lab report
  written, `include_dossiers=False`, byte-identical reproducibility),
  CLI (single-candidate dossier output, unknown candidate exit 1,
  batch artifact write + recommendation line).
- `tests/test_cli.py` stub list updated (report implemented; `pipeline`
  is the only remaining stub).

## Lint

- `ruff check src tests` — all checks passed.

## Type checking

- `mypy` — no issues in 38 source files.

## Bugs found and fixed

- Oracle report vectors read from `attack_vectors` — the OracleReport
  schema stores them as `manipulation_vectors`, so dossiers showed "0
  attack vector(s)" for the oracle agent; now checks both keys.
- CLI imported `RankingService` from `blockchain_rd_lab.ranking`
  (it lives in `ranking.service`) — single-candidate reports crashed on
  import.
- First CLI draft carried a dead `if lab or True:` branch and an
  undefined `Markdown` reference; cleaned to plain `console.print`.
- Reproducibility test initially skipped finalist promotion, so
  `write_reports` had no finalists and no dossiers to compare — the test
  now promotes first (tests must exercise the real path, not a vacuous
  one).
- `open()` without context managers (SIM115) in tests; aliased imports
  tripping N814; import order (I001).

## Deliberate Non-Goals (Phase discipline, §39)

- No charts: §38 lists them, but the deterministic text tables carry the
  data; chart rendering (matplotlib) belongs with the public-release
  polish phase and a real dataset.
- No Regulatory Risk Agent deployment (§9 defines it; the dossier's
  Regulatory Risks section states that the lab does not provide legal
  advice, per §28/§37).
- No daily/weekly report cadence (`reports/daily/`, `reports/weekly/`
  in §23) — the lab is not yet running scheduled cycles; `lab-latest.md`
  is the current-cycle report.
- No Technical Architecture deep-dive (Blockchain Architect agent is a
  future phase); the section renders declared constraints honestly.
- No `lab pipeline` orchestration (Phase 8 scope).

## Known Limitations

- MVP and Competitors sections are intentionally thin placeholders —
  they require evidence streams (competitor synthesis, MVP scoping) that
  no phase has produced yet; they render status notes rather than
  invented content.
- Historical Analysis notes the synthetic-series limitation explicitly
  (real datasets arrive with the data phase).
- Report bodies are fixed templates around stored data; richer
  narrative synthesis would reintroduce LLM text into human-facing
  artifacts and is deliberately avoided (§2).
- The recommended candidate is a deterministic function of current
  scores — fixture-uniform demo scores make it a name tiebreak today;
  with a real provider the score spread differentiates it.

## Next phase

Phase 8 — Public Research (§38, §26/§27): README/methodology/reproducibility
polish for public release, research archive structure, rejected-mechanisms
index (§29 research asset), and `lab pipeline` (§34) — the full
discover→research→formalize→simulate→redteam→rank→report loop with
interruption/resume (§35), the last remaining command.
