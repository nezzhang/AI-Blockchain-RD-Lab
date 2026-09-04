# Phase 6 Report — Ranking

**Status:** complete
**Principle:** LLM proposes. Code tests. Evidence decides. (§2)
**Scope:** §38 Phase 6 — deterministic scoring, fatal flaw gate, ranking,
finalist selection (§19 weights, §20 gate, §7 funnel: red-team → 5
finalists → 1 recommended).

## Implemented

| Component | File(s) | Notes |
|-----------|---------|-------|
| Ranking schemas | `ranking/__init__.py` | `RankedRow` (rank, score, imputed dims, status), `RankingResult` (rows + `rejected_by_gate` count), `FinalistSelection` (top-N + cutoff score + §7 note), `RankingSummary` |
| RankingService | `ranking/service.py` | `score_candidate`: runs the deterministic §19 engine (11 weighted dimensions; missing dims imputed at neutral 5.0), persists `overall_score`, advances RED_TEAM → SCORED (§11). Belt-and-braces §20: a candidate arriving with a confirmed fatal flaw is REJECTED and never ranked, even if the Phase 5 gate was bypassed. `score_all` with §35 per-candidate isolation. `rank`: deterministic order (score desc, name asc — stable and reproducible; ties documented, not coin-flipped). `select_finalists`: top-N cut with optional SCORED → FINALIST promotion (§11). `run_ranking`: batch entry point with artifact |
| CLI `lab rank` | `cli.py` | Scores any RED_TEAM candidates first (§19 engine), ranks, selects `--finalists N` (default 5 per §7), `--no-promote` for rank-only runs; Rich table with FINALIST highlighting, imputed-dimension counts, gate-exclusion reporting; writes `ranking/ranking-latest.json`. Empty-lab guard points at `lab redteam` |
| CLI `lab score` (upgraded) | `cli.py` | Now routes through `RankingService.score_candidate` so single-candidate scoring applies the same §20 gate and §11 transitions as the batch path (previously set `overall_score` without advancing the state machine) |

## Evidence (E2E demo, `database/lab.db`)

- `lab rank --finalists 5` over the 15 RED_TEAM candidates from Phase 5:
  **15/15 scored, 15 ranked, top 5 promoted to FINALIST** (§7 funnel cut).
- Funnel state: 100 → … → 15 red-teamed → **5 FINALIST** + 10 SCORED,
  5 REJECTED. All §11 transitions via `Candidate.transition()`.
- Every candidate scored 5.0500 — correct deterministic behavior: the
  fixture agents attach 6 real dimension scores (novelty 2.0 class-E,
  coherence 5.0, game_theory 5.5, security 5.0, oracle 5.0, demand 5.0)
  and 5 dimensions are imputed at the neutral 5.0 midpoint (§19); the
  weighted sum lands at 5.05 for all. Tie order is stable (name asc).
- Artifact: `ranking/ranking-latest.json` (finalists, full ranking,
  gate-exclusion count).
- §20 gate verified in tests: a candidate with a confirmed fatal flaw
  (even injected post-scoring) is excluded from the ranking and counted
  in `rejected_by_gate`; the engine's fatal-flaw cap (5.0) also applies.

## Tests

- 216 passing (was 199): `tests/test_ranking.py` adds 17 tests —
  scoring (overall set + RED_TEAM→SCORED, determinism across identical
  inputs, confirmed flaw → REJECTED with capped score, batch isolation),
  ranking (score-desc order, stable name-asc tiebreak, confirmed-flaw
  exclusion with gate count, unscored exclusion), finalists (top-N
  promotes exactly the top N to FINALIST while others stay SCORED,
  `promote=False` leaves status, fewer-than-requested note), batch
  (`run_ranking` E2E with artifact + ordered scores + finalist statuses,
  empty-lab selection), CLI (`lab rank` batch promotes the best,
  `--no-promote` ranks without promotion, empty-lab guard, `lab score`
  now transitions to SCORED).
- `tests/test_cli.py` stub list updated (rank implemented; report is the
  new PHASE 7 pointer).

## Lint

- `ruff check src tests` — all checks passed.

## Type checking

- `mypy` — no issues in 36 source files.

## Bugs found and fixed

- `lab rank` ranked before scoring: RED_TEAM candidates had no
  `overall_score`, so the first CLI test showed "Ranking — 0
  candidate(s)". The command now scores RED_TEAM candidates first, then
  ranks.
- Unused imports across new files (auto-fix, reviewed before applying).

## Deliberate Non-Goals (Phase discipline, §39)

- No reporting (Phase 7): the ranking artifact is JSON, not the
  human-facing Markdown research report.
- No "1 recommended candidate" selection yet (§7 tail): all five
  finalists remain; the final recommendation belongs with reporting.
- No IMPROVEMENT loop (§11): finalists' red-team `what_would_save_it`
  notes are stored but no agent acts on them yet.
- No changes to the §19 weights or the scoring engine itself — Phase 6
  consumes the Phase 0 engine as specified.
- No SUPERSEDED handling (newer model versions superseding older
  candidates is a later data phase concern).

## Known Limitations

- E2E scores are uniform because every demo candidate shares fixture
  research + adversarial reports; score diversity requires a real
  provider. The deterministic machinery (ordering, gate, imputation,
  promotion) is fully exercised regardless.
- Imputed dimensions are counted in the table but not weighted
  differently — a candidate with many imputed dims can tie with a fully
  scored one; an imputation-confidence penalty is a future improvement
  candidate (noted for the improvement loop).
- Ranking covers SCORED + FINALIST statuses; REJECTED/FAILED candidates
  never appear (by design, §20).

## Next phase

Phase 7 — Reporting (§38, §26): automated Markdown research reports —
per-candidate dossiers and a lab-wide report funnel summary drawing on
candidates, scores, math models, simulation §21 records, adversarial
verdicts, and the ranking; charts optional; the §7 "1 recommended
candidate" recommendation lands here.
