# Phase 2 Report — Research (Prior-Art, Economist, Market Agents)

**Status:** complete
**Principle:** LLM proposes. Code tests. Evidence decides. (§2)
**Scope:** §38 Phase 2 — Prior-Art Agent, Economist Agent, Market Agent,
prior-art source storage, novelty classification A–E, evidence levels
(FACT/INFERENCE/HYPOTHESIS), and the 100→20 prior-art filter (§7 funnel).

## Implemented

| Component | File(s) | Notes |
|-----------|---------|-------|
| Research schemas | `src/blockchain_rd_lab/research/__init__.py` | `PriorArtReport` (§12 class A–E, language discipline enforced by validators), `EconomistReport`, `MarketReport`, `ResearchSource`, `SimilarMechanism`, `EvidenceLevel` (§29), `CandidateBrief`, `CandidateResearchResult`, `FilterOutcome` |
| Research agents | `src/blockchain_rd_lab/research/agents.py` | `PriorArtAgent` (novelty class, similar mechanisms, queries, sources, findings, conclusion), `EconomistAgent` (monetary policy, incentives, liquidity, stability, reflexivity, fatal-concern flag), `MarketAgent` (customer, problem, alternatives, size, adoption barriers) — all subclass `BaseAgent`, structured output only |
| Research service | `src/blockchain_rd_lab/research/service.py` | `ResearchService`: per-candidate orchestration (prior-art → economist → market), status transitions GENERATED→RESEARCHING→PRIOR_ART_CHECKED (§11), score-breakdown attachment (novelty, economic_coherence, market_demand), fatal-flaw → REJECTED gate, per-agent failure isolation (§35), prior-art persistence to `sources`/`prior_art` tables |
| Deterministic filter | `src/blockchain_rd_lab/research/service.py` | `ResearchFilter`: cuts novelty class A/B (clearly/very-similar existing), ranks survivors by (novelty, coherence, demand, name), keeps top-N (§7: 100→20), overflow → REJECTED; pure code, no LLM input |
| Persistence | `src/blockchain_rd_lab/database/__init__.py` | `save_source` (URL-deduped), `list_sources`, `save_prior_art`, `list_prior_art` — queries, findings, similar mechanisms, sources, similarity class recorded (§12, §22) |
| Offline fixtures | `research/agents.py::build_research_report_fixture` | Deterministic reports per candidate + CLI `--mock-fixtures` path exercising identical validation/persistence code |
| CLI | `src/blockchain_rd_lab/cli.py` | `lab research` (three agents per candidate, Rich table, rejection summary), `lab prior-art` (standalone §12 check), `lab filter` (§7 cut with A/B/overflow breakdown); stubs removed |

## Evidence (E2E demo, `database/lab.db`)

- Seed (Experiment #001 Population Money) + 18 discovered candidates researched:
  `lab seed` → `lab discover --mock-fixtures` ×2 → `lab research --mock-fixtures`
- 19/19 researched; each carries `novelty`, `economic_coherence`,
  `market_demand` score breakdowns with evidence levels recorded.
- Prior-art evidence persisted: 19 `prior_art` rows + 19 `sources` rows
  (queries, findings, similar mechanisms, conclusion, similarity class).
- `lab filter --target 15`: considered 19 → kept 15, rejected 4
  (funnel overflow). Class A/B cuts exercised in unit tests (fixtures
  default to class E insufficient_evidence).
- Research artifact JSON written to `research/prior_art/` per run.

## Tests

- 123 passing (was 91): `tests/test_research.py` adds 26 tests covering
  schema language discipline (forbidden/required claims, bare-digest
  rejection), agent happy paths via mock provider, service transitions and
  fatal-flaw rejection, per-agent failure isolation, filter cuts/overflow/
  ranking/terminality, source dedup, fixture generator, and CLI research /
  prior-art / filter paths including the dry-mock fail-closed guard.

## Lint

- `ruff check src tests` — all checks pass.

## Type checking

- `mypy` — no issues in 27 source files.

## Bugs found and fixed during this phase

1. **Schema under-gate (§2 violation):** `PriorArtReport` originally
   validated with all-default fields, so a bare mock-digest response
   (`{"mock": true, ...}` from a dry queue) passed validation and entered
   the DB as "evidence". Fixed: `search_queries`, `findings`, and
   `conclusion` (≥20 chars) are now required; a regression test asserts
   digest garbage is rejected.
2. **CLI silently used a dry mock queue:** `lab research` without
   `--mock-fixtures` under `runtime.llm_provider: mock` would consume
   digest responses. Fixed: fails closed with exit code 2 and a §30 hint.
3. **Test pollution of the real lab DB:** `tests/test_cli.py` monkeypatched
   `CONFIG_DIR` to an empty dir, which fell back to the default
   `database/lab.db` — seeding and researching against the real lab state
   (root cause of stray "Population-Linked Supply" rows). Fixed: new
   `tmp_lab_dir` conftest fixture writes an isolated `lab.yaml` + private
   DB; all CLI tests now use it; demo DB rebuilt from a clean re-run.

## Deliberate Non-Goals (Phase discipline, §39)

- No web search / live prior-art retrieval — the Prior-Art Agent proposes
  queries and mechanisms; a real search backend arrives with a later phase.
- No formalization, simulation, red-team, or ranking (Phases 3–6).
- No autonomous pipeline driver (Phase 8+); commands are operator-invoked.
- The Population-Money seed is treated as an ordinary candidate (§24) —
  no scoring favoritism in the filter's deterministic sort key.

## Known Limitations

- Offline fixtures report class E (insufficient_evidence) for every
  candidate — realistic A/B/D classifications require a real provider or a
  search-augmented prior-art agent.
- `EconomistReport`/`MarketReport` confidence values are service-set
  (0.8/0.7) pending per-dimension confidence from a later calibration pass.
- The filter's overflow rejection is per-cycle: overflowed candidates may
  be re-researched in a later cycle by transitioning REJECTED → RESEARCHING
  (allowed in the §11 table) after new evidence.
- Funnel counts in the demo (19→15) are smaller than the §7 100→20 scale
  because the offline fixture set is intentionally small.

## Next phase

Phase 3 — Formalization (§38): Formalizer Agent to turn PRIOR_ART_CHECKED
candidates into mathematical models (assumptions, variables, equations,
constraints, invariants), with schema-validated output feeding Phase 4
simulation. Transition: PRIOR_ART_CHECKED → FORMALIZED.
