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
  sections) + lab funnel report, ASSEMBLED BY CODE from stored evidence
  (no report-writer LLM; §2); rank-1 finalist is the §7 recommended
  candidate; `lab report [id]` writes reports/finalists/ + lab-latest.md.
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
- Archive: `src/blockchain_rd_lab/archive/` — §26 rejected-mechanisms
  index (ideas/rejected/index.{md,json}) with rejection reasons and §20
  flaw records; failed experiments are a research asset.
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
- `src/blockchain_rd_lab/testing/` — offline discovery fixtures
- `config/` — YAML configuration (lab, agents, scoring, research)
