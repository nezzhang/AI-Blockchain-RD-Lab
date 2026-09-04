# GEMINI.md

Gemini-specific notes for working in this repository.

**Read [`AGENTS.md`](./AGENTS.md) first — it is the binding rulebook for all
AI agents here.** This file is a convenience summary, not a replacement.

## Quick Reference

- Prime directive: *LLM proposes. Code tests. Evidence decides.*
- Build phase by phase (see [`MASTER BUILD PROMPT.md`](./MASTER%20BUILD%20PROMPT.md) §38).
  Phase 0 = foundation. Phase 1 = discovery. Phase 2 = research. Phase 3 =
  formalization. Phase 4 = simulation. Phase 5 = adversarial testing (done).
  No autonomous pipeline yet.
- All agent output must pass Pydantic validation before storage.
- Candidate status changes only via `Candidate.transition()` (state machine,
  `src/blockchain_rd_lab/schemas.py`).
- Scoring is deterministic; confirmed fatal flaws cap scores — never averaged away.
- Discovery: `src/blockchain_rd_lab/discovery/` — agent (LLM) + normalizer and
  deduplicator (pure code) + service; `lab discover --mock-fixtures` runs offline.
- Research: `src/blockchain_rd_lab/research/` — Prior-Art/Economist/Market
  agents + service + deterministic `ResearchFilter` (§7 funnel);
  `lab research --mock-fixtures` and `lab filter` run offline.
- Formalization: `src/blockchain_rd_lab/formalization/` — Mechanism Designer
  agent + `MathModel` schema (§13) + deterministic integrity checks;
  `lab formalize --mock-fixtures` runs offline.
- Simulation: `src/blockchain_rd_lab/simulation/` — safe equation
  interpreter + §15 scenario battery (13 scenarios incl. bank run, oracle
  failure, black swan) + Monte Carlo + parameter sweeps + Optuna (optional);
  `lab simulate` runs offline; every run persists §21 experiment records
  (seed, git commit, parameters, results).
- Red team: `src/blockchain_rd_lab/redteam/` — Game-Theory/Security/Oracle/
  Red-Team agents ("DESTROY THE IDEA", §9); the §20 fatal-flaw gate is
  deterministic code — a fatal verdict only rejects when the strongest
  attack is also profitable; `lab redteam --mock-fixtures` runs offline.
- Never issue tokens, deploy contracts, move funds, or spend significant API
  budget without explicit human approval.
- Novelty language: "No substantially similar implementation was identified
  in the searched sources." Never "Nobody has ever done this."

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
- `src/blockchain_rd_lab/scoring/` — deterministic scoring engine
- `src/blockchain_rd_lab/cli.py` — Typer CLI (`lab`)
- `src/blockchain_rd_lab/testing/` — offline discovery fixtures
- `config/` — YAML configuration (lab, agents, scoring, research)
