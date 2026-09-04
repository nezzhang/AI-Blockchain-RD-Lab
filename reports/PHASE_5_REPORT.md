# Phase 5 Report — Adversarial Testing

**Status:** complete
**Principle:** LLM proposes. Code tests. Evidence decides. (§2)
**Scope:** §38 Phase 5 — Game Theory Agent, Security Agent, Oracle Agent,
Red Team (§9 agent missions, §20 fatal-flaw system, §17 adversarial review).

## Implemented

| Component | File(s) | Notes |
|-----------|---------|-------|
| Adversarial schemas | `redteam/__init__.py` | `AttackVector` (attacker-role enum: whale/validator/oracle_provider/governance/arbitrageur/liquidity_provider/attacker, `profitable_for_attacker`, `requires_collusion`, §29 evidence level), `AdversarialConcern`, four agent reports (`GameTheoryReport`, `SecurityReport`, `OracleReport`, `RedTeamReport` with verdict `survives\|vulnerable\|fatal`), `RedTeamResult`/`RedTeamSummary` rollups. All reports require ≥1 attack vector — an adversarial report with no attacks cannot validate |
| Game Theory Agent | `redteam/agents.py` | §9 mission: rational profit maximizers; find arbitrage, manipulation, incentive misalignment, equilibrium failures, bank runs, death spirals, strategic attacks; scores `game_theory` 0-10 |
| Security Agent | `redteam/agents.py` | Contract/economic/oracle/governance/validator attacks, censorship, Sybil; `hardest_attack_to_defend` required; scores `security` |
| Oracle Agent | `redteam/agents.py` | Data sources, accuracy, latency, revisions, manipulation, decentralization, provider incentives, conflicting data; scores `oracle_feasibility`; mechanisms without oracles still assessed on implicit data dependencies |
| Red Team Agent | `redteam/agents.py` | "DESTROY THE IDEA" — the full §9 question battery (manipulate? arbitrage? whale/validator/oracle/governance exploit? liquidity disappearance? death spiral? profitable attack? crisis behavior? wrong assumptions?); strongest-tier model, temp 0.6; verdict + `what_would_save_it` required |
| §20 fatal-flaw gate | `redteam/service.py` | **Deterministic code, not the prompt**: a candidate is rejected ONLY when verdict == `fatal` AND `strongest_attack_is_profitable` — both structured schema fields. A fatal verdict with an unprofitable attack is recorded but does not reject; the prompt can never reject a candidate alone (§2). Confirmed flaws append `FatalFlaw(confirmed=True, identified_by="red_team")` and cap scores in Phase 6 |
| RedTeamService | `redteam/service.py` | Per candidate: four agents → dimension scores (`game_theory`, `security`, `oracle_feasibility` per `config/scoring.yaml`) → SIMULATING → RED_TEAM (§11) or → REJECTED via the gate; §35 isolation (agent failures recorded per candidate, status untouched); `redteam_all` batch with summary + artifact |
| Persistence | `database/__init__.py` | New `redteam_results` table (append-only): one row per agent report with validated `report_json` + red-team `verdict`; `save_redteam_result`/`list_redteam_results` |
| CLI | `cli.py` | `lab redteam [candidate_id] [--mock-fixtures] [--limit]` (replaces stub); single-candidate mode resolves and preconditions the candidate BEFORE building fixtures; dry-mock fails closed (§30); batch writes `redteam/runs/redteam-latest.json` |
| Fixtures | `redteam/agents.py::build_redteam_fixture` | Deterministic four-report sets (verdict configurable: survives/vulnerable/fatal; whale exit-timing, stale-oracle exploit, parameter capture, anchor-spike, bank-run trigger); same validation + storage path as LLM output (§2 prime directive) |

## Evidence (E2E demo, `database/lab.db`)

- `lab redteam --mock-fixtures` over the 15 SIMULATING candidates:
  **15/15 red-teamed, 0 agent errors**, all verdicts `vulnerable`, none
  rejected (fixture attacks are hypotheses, not profitable structural
  breaks) → all 15 now RED_TEAM (§11).
- 60 `redteam_results` rows (4 agents × 15 candidates), verdicts recorded.
- Dimension scores attached on every candidate: `game_theory`,
  `security`, `oracle_feasibility` (now 6 scored dimensions total with
  Phase 2's novelty/economic_coherence/market_demand).
- Fatal-gate E2E on the re-seeded Population-Linked Supply candidate:
  fatal verdict + profitable strongest attack → **confirmed fatal flaw
  `ff-cand-7f2f07fd4e9a-redteam` → REJECTED**. The state machine and the
  §20 gate both held.
- Artifact: `redteam/runs/redteam-latest.json`.

## Tests

- 199 passing (was 177): `tests/test_redteam.py` adds 22 tests —
  schemas (fixture validation, verdict pattern, empty attack_vectors
  rejected, short summary rejected, attacker-role pattern, fatal fixture),
  agents (happy path with run record, red-team tier=strongest/temp 0.6,
  wrong payload TypeError, LLMError, all four §9 missions in prompts),
  §20 gate (vulnerable survives gate → RED_TEAM with 3 dimension scores;
  fatal+profitable → REJECTED with confirmed flaw; fatal+unprofitable →
  recorded, NOT rejected; total agent failure → status untouched, 4
  errors), batch (§35 isolation with digest-garbage fallback errors
  counted, artifact written; 4-agent persistence round-trip with verdict),
  CLI (unknown candidate, status precondition, no-simulating early exit,
  batch run → RED_TEAM, dry-mock exit 2).
- `tests/test_cli.py` stub list updated (redteam implemented; rank is the
  new PHASE 6 pointer).

## Lint

- `ruff check src tests` — all checks passed.

## Type checking

- `mypy` — no issues in 35 source files.

## Bugs found and fixed

- `save_redteam_result` used `flush()` only — rows vanished after session
  close (every repo method needs explicit `commit()`); direct DB test
  caught it before E2E.
- CLI single-candidate mode built fixture queues from ALL simulating
  candidates before resolving the requested candidate — unknown-candidate
  and wrong-status errors were unreachable in an empty lab. Restructured:
  resolve candidate → precondition → build fixtures for exactly that one.
- `redteam_all` counted candidates with agent errors as "completed";
  now `completed` requires all four reports and erroring candidates are
  counted separately.
- Test initially queued mock errors AFTER responses — MockLLMProvider
  pops queued errors before responses regardless of order, so the
  isolation fixture needed the digest-garbage (schema-validation failure)
  path instead: the §2 fail-closed behavior is itself now under test.
- `EvidenceLevel(str, Enum)` → `enum.StrEnum` (repository convention,
  UP042); leftover unused imports; unraw regex patterns in `match=`
  (RUF043).

## Deliberate Non-Goals (Phase discipline, §39)

- No scoring/ranking integration yet (Phase 6) — dimension scores are
  attached but `overall_score` is still unset for red-teamed candidates.
- No IMPROVEMENT loop yet (§11): `what_would_save_it` is recorded for
  the future improvement agent; RED_TEAM → IMPROVEMENT is an allowed
  transition but no agent drives it yet.
- No Regulatory Risk Agent in this phase (it exists in §9 and
  `config/agents.yaml`; belongs with reporting/finalist review).
- No automatic re-simulation after adversarial findings (§34 retest loop).
- No attack *simulation*: vectors are recorded and scored, not yet
  executed as simulation scenarios (future: map attack vectors onto §15
  scenario configs).

## Known Limitations

- The gate's profitability condition relies on the Red Team agent's own
  `strongest_attack_is_profitable` judgment — an LLM claim, though a
  structured one. A stronger gate would cross-check against simulation
  evidence (Phase 6 improvement candidate).
- Fixture reports give every candidate the same generic attack inventory;
  verdict diversity requires a real provider.
- Verdict vocabulary is deliberately narrow (survives/vulnerable/fatal);
  severity nuance lives in the per-vector fields and dimension scores.
- `redteam_results` is append-only with no dedup — re-running a candidate
  appends a second generation of reports (visible history, by design).

## Next phase

Phase 6 — Ranking (§38, §19/§20): deterministic scoring engine integration
(overall_score over the 6 dimension scores), fatal-flaw cap application,
scored-candidate ranking, funnel cut RED_TEAM → SCORED → FINALIST, and the
top-3 finalist selection (§7).
