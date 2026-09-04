# AI Blockchain R&D Lab

An autonomous, AI-powered research laboratory for discovering, evaluating,
simulating, attacking, and ranking **novel blockchain economic mechanisms**.

> The objective is NOT to create tokens, copy existing chains, or launch
> anything. The objective is to **discover genuinely interesting, economically
> coherent, technically feasible, and potentially novel economic primitives** —
> and to eliminate bad ideas through research, mathematical modeling,
> simulation, and adversarial testing.

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
| 6 | Ranking: deterministic scoring, fatal-flaw gate, finalists | ⬜ next |
| 7 | Reporting: automated research reports | ⬜ |
| 8 | Public research release | ⬜ |

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

The remaining command surface (`lab simulate`, `lab redteam`, `lab rank`,
`lab report`, `lab pipeline`) is declared as stubs that point to their
future phase.

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

## Public Research Philosophy

Failed experiments are research assets. The `ideas/rejected/` directory and
all simulation results will eventually be published openly — assumptions,
known limitations, and rejected mechanisms included.

## License

MIT — see [LICENSE](./LICENSE).
