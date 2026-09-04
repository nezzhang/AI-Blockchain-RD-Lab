# AGENTS.md — Operating Rules for AI Agents in This Repository

This document binds every AI agent (LLM or otherwise) working in this repo.

## Prime Directive

```text
LLM proposes. Code tests. Evidence decides.
```

LLMs generate hypotheses, research, mechanisms, and critiques. Deterministic
code simulates, validates, scores, and stores. **Never let unstructured LLM
text control deterministic parts of the system** — all agent output must pass
Pydantic schema validation before it enters the database.

## Phase Discipline (MASTER BUILD PROMPT §38, §39)

1. Work **phase by phase**. Never build ahead of the current phase.
2. After each phase: implement → test → fix → lint → typecheck → review →
   document → commit. Never skip tests.
3. Phase 0 is foundation only. No autonomous pipeline until later phases.

## Hard Safety Rules (§28, §37, §41)

NEVER:

- issue, deploy, or launch a real token, contract, or testnet
- transfer funds or connect wallets
- execute arbitrary shell commands from LLM output
- store or read private credentials; API keys come from env vars only
- modify files outside this repository
- spend significant API budget without human approval
- publish official claims of novelty
- provide legal advice (the Regulatory agent only flags risk areas)

The lab may **recommend**; it must not independently execute these actions.

## Research Integrity (§12, §29)

- Never claim "Nobody has ever done this." Say: "No substantially similar
  implementation was identified in the searched sources."
- Record search queries, sources, dates, findings, and similar mechanisms.
- Distinguish FACT / INFERENCE / HYPOTHESIS in all research output.
- Prefer academic papers, official docs/repos, government datasets, and
  international organizations.
- Do not hide failed experiments. `ideas/rejected/` is a research asset.
- Fatal flaws cap scores — they are never averaged away (§20).

## State Machine Discipline (§11)

Candidates move only through allowed transitions (`schemas.py`
`_ALLOWED_TRANSITIONS`). Never mutate `status` directly bypassing
`assert_transition` / `Candidate.transition`.

## Engineering Conventions

- Python 3.12+, `pyproject.toml`, `uv` preferred.
- Pydantic models for all structured data; Typer + Rich for the CLI;
  SQLAlchemy + SQLite for storage.
- `ruff check` and `mypy` must pass before every commit.
- Tests use synthetic data and the mock LLM provider — no network, no real
  API keys in CI.
- Do not commit bulky datasets (`data/`, `database/`, DuckDB files).
- Meaningful commits only: `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`.
