# CLAUDE.md

Claude-specific notes for working in this repository.

**Read [`AGENTS.md`](./AGENTS.md) first — it is the binding rulebook for all
AI agents here.** Everything below is a convenience summary, not a
replacement.

## Quick Reference

- Prime directive: *LLM proposes. Code tests. Evidence decides.*
- Build phase by phase (see [`MASTER BUILD PROMPT.md`](./MASTER%20BUILD%20PROMPT.md) §38).
  Phase 0 = foundation only. Do not build the autonomous pipeline early.
- All agent output must pass Pydantic validation before storage.
- Candidate status changes only via `Candidate.transition()` (state machine,
  `src/blockchain_rd_lab/schemas.py`).
- Scoring is deterministic (`src/blockchain_rd_lab/scoring/`); confirmed fatal
  flaws cap scores and are never averaged away.
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
- `src/blockchain_rd_lab/database/` — SQLAlchemy + SQLite repository
- `src/blockchain_rd_lab/agents/` — agent + LLM provider abstractions, mock provider
- `src/blockchain_rd_lab/scoring/` — deterministic scoring engine
- `src/blockchain_rd_lab/cli.py` — Typer CLI (`lab`)
- `config/` — YAML configuration (lab, agents, scoring, research)
