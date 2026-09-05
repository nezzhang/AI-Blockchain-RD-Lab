# AI Blockchain R&D Lab

An autonomous, AI-powered research laboratory for discovering, evaluating,
simulating, attacking, and ranking **novel blockchain economic mechanisms**.

> The objective is NOT to create tokens, copy existing chains, or launch
> anything. The objective is to **discover genuinely interesting, economically
> coherent, technically feasible, and potentially novel economic primitives** —
> and to eliminate bad ideas through research, mathematical modeling,
> simulation, and adversarial testing.

## Definition of Success (§42) — verified

```bash
lab pipeline --count 100 --mock-fixtures
```

Runs the spec's entire success funnel offline and deterministically:

```
100 mechanisms (§24: all 20 source domains)
  → prior-art analysis → 20 serious candidates
  → mathematical models → simulations → adversarial attacks
  → improvements → retests → 5 finalists → 1 recommended
  → reproducible reports + usage ledger + rejected archive
```

Locked in as `tests/test_success_criteria.py::TestDefinitionOfSuccess`
(~6s, part of the standard suite). The offline corpus generator
supplies 100+ distinct mechanisms across §24's domains; the same
normalization, dedup, §13 integrity, §15 battery, §20 gate, and §19
scoring code paths gate everything exactly as with a live provider.

## Core Principle

```text
LLM proposes. Code tests. Evidence decides.
```

- LLMs generate hypotheses, research, design mechanisms, and criticize ideas.
- Deterministic code calculates, simulates, validates, scores, and stores results.
- LLM output never directly controls deterministic parts of the system.

## Research Loop

```text
DISCOVER → RESEARCH → PRIOR ART → DE-DUPLICATE → FORMALIZE → SIMULATE
→ RED TEAM → IMPROVE → RE-SIMULATE → SCORE → RANK → REPORT → PUBLIC RESEARCH
```

## Status

**Phase 0 — Foundation (complete).** This phase provides the deterministic
backbone: configuration, Pydantic schemas, SQLite persistence, the CLI,
the agent/LLM abstractions with a mock provider, and the scoring engine.
The autonomous pipeline arrives in later phases (see
[`MASTER BUILD PROMPT.md`](./MASTER%20BUILD%20PROMPT.md) §38).

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Foundation: schemas, DB, CLI, agents, mock LLM, scoring, tests | ✅ done |
| 1 | Discovery: idea generation, normalization, dedup | ✅ done |
| 2 | Research: prior art, economist, market agents, 100→20 filter | ✅ done |
| 3 | Formalization: mathematical models | ✅ done |
| 4 | Simulation: scenario battery, Monte Carlo, sweeps, Optuna | ✅ done |
| 5 | Adversarial testing: Game Theory, Security, Oracle, Red Team agents, §20 fatal-flaw gate | ✅ done |
| 6 | Ranking: deterministic scoring, §20 fatal-flaw gate, top-5 finalists | ✅ done |
| 7 | Reporting: §23 dossiers (19 sections), lab report, §7 recommendation | ✅ done |
| 8 | Public research: §34 pipeline (resumable), §26 rejected archive, release docs | ✅ done |

## Install

Requires Python 3.12+.

```bash
# with uv (preferred)
uv venv --python 3.12
uv pip install -e ".[analytics,dev]"

# or with pip
pip install -e ".[analytics,dev]"
```

## Usage

```bash
lab init                 # initialize the SQLite database
lab seed                 # seed Experiment #001 (Population Money) as an ordinary candidate
lab discover --count 20  # generate ideas: LLM → normalize → dedup → store
lab discover --count 20 --mock-fixtures   # offline demo with fixture batches
lab research --mock-fixtures              # Phase 2: prior-art + economist + market per candidate
lab filter --target 20    # deterministic funnel cut after prior-art research (§7)
lab formalize --mock-fixtures              # Phase 3: math models with variables/equations/assumptions (§13)
lab simulate [--trials 20] [--steps 60]   # Phase 4: §15 scenario battery + Monte Carlo + sweep (§21 records)
lab redteam --mock-fixtures              # Phase 5: adversarial agents + §20 fatal-flaw gate (verdict: survives/vulnerable/fatal)
lab rank [--finalists 5]                # Phase 6: deterministic scoring + ranking + §7 finalist cut
lab report [candidate_id]               # Phase 7: §23 finalist dossiers + lab report (reports/finalists/, reports/lab-latest.md)
lab combine                               # §18: inspect mechanism families + combination pairs (pure code)
lab discover --combine                   # discovery steered by §18 combination hints
lab improve [candidate_id]                # §34: patch red-teamed models (LLM proposes; §13 integrity gates)
lab retest [candidate_id]                # §34: re-simulate + re-attack patched models (§20 gate re-evaluates)
lab pipeline --count 10 --mock-fixtures # Phase 8: full §34 loop incl. improve/retest (resumable via --stop-after, §35)
                                          #   --budget N caps token spend (§31: fail-closed; resumable with a fresh budget)
lab status               # candidate counts by lifecycle state
lab score <candidate_id> # deterministic scoring with fatal-flaw gate
lab search <query>       # search stored candidates
lab version              # lab version
```

Discovery and research run against the configured provider (default:
deterministic `mock`). To use a real provider, set `runtime.llm_provider` in
`config/lab.yaml` (options: `openai`, `local`) and export the provider's API
key — keys are read from environment variables only, never stored. A dry
mock queue (no `--mock-fixtures`) fails closed instead of emitting junk.

The full §34 pipeline runs offline end to end:
`lab pipeline --count 10 --mock-fixtures` — discover → research → filter →
formalize → simulate → red-team → score/rank → report, with `--stop-after
<stage>` for interruption and resumable re-runs (§35: the database is the
checkpoint; no progress is lost when an agent fails).

## Development

```bash
make dev        # lint + typecheck + test
make test       # pytest
make test-cov   # pytest with coverage
make lint       # ruff check
make typecheck  # mypy
```

## Repository Layout

```text
config/        lab.yaml, agents.yaml, scoring.yaml, research.yaml
src/           blockchain_rd_lab package (schemas, database, agents, discovery, scoring, CLI)
agents/        agent prompt/spec definitions by role (populated in later phases)
ideas/         active / promising / finalists / rejected candidates (+ discovery artifacts)
research/      papers, protocols, prior art, competitors
mechanisms/    formalized mechanism library
simulations/   models, monte carlo, agent-based, historical
redteam/       adversarial analyses by category
data/          raw / processed / external datasets (never committed)
database/      SQLite lab database (never committed)
reports/       daily / weekly / finalists reports (+ phase reports)
tests/         pytest suite
scripts/       operational scripts
```

## Safety & Human Approval Gates

This lab is a **research system**. It never issues real tokens, deploys
contracts, or moves funds. The following require explicit human approval
(MASTER BUILD PROMPT §28, §41): deploying contracts, launching testnets,
issuing tokens, significant API spend, wallet connections, fund movement,
publishing official novelty claims, and legal agreements.

## Methodology

The lab enforces one discipline end to end: **LLM proposes. Code tests.
Evidence decides.**

1. **Discovery** (LLM) proposes ideas; deterministic code normalizes and
   deduplicates them. The §18 Mechanism Combinator (pure code) mines
   mechanism families from the corpus and proposes economically
   compatible combination pairs — semantic bridges, never random
   mashups — as steering hints for discovery.
2. **Research** agents (prior art, economist, market) return structured,
   Pydantic-validated reports; a deterministic §7 filter cuts the funnel.
3. **Formalization** (LLM) proposes a mathematical model; deterministic
   integrity checks enforce declared symbols, ASCII equations, and §13
   open questions before anything is stored.
4. **Simulation** is pure code: a safe AST interpreter executes the
   stored equations across the §15 scenario battery (bank run, oracle
   failure, black swan, ...), Monte Carlo, and parameter sweeps.
5. **Adversarial review** (LLM) attacks the mechanism; the §20 fatal-flaw
   gate is deterministic code — a fatal verdict rejects only when the
   strongest attack is also profitable.
6. **Improvement loop** (LLM proposes, code gates): vulnerable mechanisms
   get a patched model v(n+1) that must pass the same §13 integrity checks,
   then re-run the §15 battery and a fresh adversarial review — the full
   §34 RED_TEAM → IMPROVEMENT → RETEST → SIMULATING → RED_TEAM loop.
7. **Scoring, ranking, and reports** are entirely deterministic — the
   §23 dossiers are assembled by code from stored evidence, with no
   report-writer LLM anywhere.

Every experiment stores seed, parameters, git commit, and results (§21);
reproducing a run is a lookup, not a guess.

## Cost Control (§31)

The founder has limited capital, so spending is enforced by code, not
good intentions:

- Every pipeline run wraps its provider in a **BudgetGuard**: a hard token
  ceiling (`--budget`, default from `config/lab.yaml`) that fails closed —
  once crossed, the run halts cleanly and the database remains resumable
  with a fresh budget (§35). No silent overspend.
- A **disk-backed response cache** memoizes identical agent calls across
  runs (§31 caching; §32: agents must not repeatedly re-pay for the same
  research). Cache hits cost zero tokens.
- A **usage ledger** (`reports/usage-latest.json`) records spend, calls,
  and cache savings per run — cost evidence is auditable like everything
  else (§21 spirit).

- Model routing follows §31's tiers (cheap for classification, medium for
  idea generation, strong for research synthesis, strongest for finalists)
  via `tier_models` in `config/lab.yaml`.

## Reproducibility

- All offline commands (`--mock-fixtures`) are fully deterministic: same
  inputs → identical database states, scores, and report bytes.
- Simulations record seed + git commit + parameters per run (§21).
- The research loop never averages away fatal flaws (§20) and never hides
  failed experiments (§26, §29).

## Research Knowledge Graph (§33)

Every piece of stored evidence — candidates, prior-art sources, math
model versions, §21 experiment records, adversarial attack vectors,
and §34 improvement rationales — is linked into one reusable graph:

```
Idea ↔ Source ↔ Mechanism ↔ Simulation ↔ Attack ↔ Improvement
```

- `lab graph` — node/edge inventory + artifact export
  (`reports/graph-latest.json`)
- `lab graph <idea_id>` — the full §33 chain for one idea
- `lab graph --similar-attack "..."` — §32 reuse: has a similar
  attack been recorded before, and how was it fixed?

The graph is DERIVED and deterministic (§2): rebuild over the same
database yields the identical graph. It is how future agents consult
previous discoveries instead of re-deriving them.

## Research Archive

- `reports/finalists/` — §23 dossiers per finalist
- `reports/lab-latest.md` — funnel status, ranking, §7 recommendation
- `reports/PHASE_*_REPORT.md` — phase engineering reports
- `ideas/rejected/index.md` — the rejected-mechanisms index (§26: failed
  experiments are a research asset, with rejection reasons and §20 flaw
  records)
- `ideas/active/` — stored idea batches from discovery runs

## Public Research Philosophy

Failed experiments are research assets. The `ideas/rejected/` directory and
all simulation results will eventually be published openly — assumptions,
known limitations, and rejected mechanisms included.

## License

MIT — see [LICENSE](./LICENSE).
