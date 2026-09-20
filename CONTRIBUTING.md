# Contributing

This repo is an autonomous research lab whose prime directive is **LLM
proposes. Code tests. Evidence decides.** Contributions that strengthen the
*measurement*, *honesty*, or *reproducibility* of the system are the most
valuable. Criticism is a contribution — the audit trail (`*-FIXES.md` and
`*-FIXES-RESPONSE.md` files, and `CLAUDE.md` rounds 27–46) is the lab
catching its own errors, and external audits are how it improves.

## Before you start

- Read [`AGENTS.md`](./AGENTS.md) — the binding rules (state machine, safety,
  research integrity).
- Read [`AUDITING.md`](./AUDITING.md) — where the load-bearing claims live,
  what prior audits already fixed, and the honestly-disclosed open weaknesses.
  **Start at the frontier, not the walls** — do not re-report a finding a
  prior round already closed.
- Skim [`MASTER BUILD PROMPT.md`](./MASTER%20BUILD%20PROMPT.md) for the §-numbered
  spec the code references.

## Ways to contribute

### 1. File an audit finding (highest value)
Attack a load-bearing system (the §19 scorer, the §20 fatal-flaw gate, the
attack battery, the interpreter, the report assembler). Open a GitHub issue
using the **Audit finding** template, or write a `YYYY-MM-DD-<name>-FIXES.md`
in the style of the existing audits. Discipline on this side (§2 applies to
audits too): every finding is **verified against the store / by live execution
before any fix**, fixed at the generator, and pinned by a test the day it
ships. Disagreement is welcome.

### 2. Fix or extend code
- **Phase discipline** (§38/§39): work phase by phase; don't build ahead.
- LLM/agent output must pass **Pydantic validation** before storage — never
  let unstructured text control deterministic paths.
- Candidate status changes only via `Candidate.transition()` (the §11 state
  machine). Never mutate `status` directly.
- Tests use **synthetic data and the mock LLM provider** — no network, no real
  API keys in CI.
- Fatal flaws are **never averaged away** (§20); failed experiments are a
  research asset, never hidden (§29).

### 3. Improve docs / reproducibility
Every published number must trace to stored evidence. If prose drifts from
data, that's a bug.

## Development setup

```bash
git clone https://github.com/nezzhang/AI-Blockchain-RD-Lab.git
cd AI-Blockchain-RD-Lab

# uv is preferred; pip works too
uv sync --all-extras            # or: pip install -e ".[analytics,dev]"

uv run pytest                   # full suite (offline, deterministic)
uv run ruff check src tests     # lint
uv run mypy                     # typecheck

# reproduce the published bundle with no database, no install of the lab
python reports/release/bundle-cand-9200b07691c3/verify.py
```

## Pull requests

- CI runs `ruff`, `mypy`, `pytest`, and the bundle verifier on Python
  3.12 and 3.13. All must pass.
- Keep changes scoped; meaningful commit messages (`feat:`, `fix:`, `docs:`,
  `test:`).
- Do not commit bulky datasets (`data/`, `database/`, DuckDB files).
- If your change alters a published number, that is a **"never a silent
  re-score"** event: disclose it, publish side-by-side, and regenerate the
  affected artifacts.

## Hard safety rules (non-negotiable)

This lab **recommends**; it must not independently execute. Never: issue,
deploy, or launch a real token/contract/testnet; transfer funds or connect
wallets; execute arbitrary shell from LLM output; store/read private
credentials (API keys come from env vars only); or provide legal advice (the
Regulatory agent only flags risk areas).
