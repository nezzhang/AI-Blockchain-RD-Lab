# Auditing This Lab (a critic's map)

This repo is an autonomous research lab that discovers, simulates,
attack-tests, and ranks blockchain economic mechanisms. Its prime
directive: **LLM proposes. Code tests. Evidence decides.** This file
maps where the load-bearing claims live, what has already been
audited, and where the honest open weaknesses are — so a hostile
reviewer starts at the frontier, not the walls.

## Start here (30 minutes)

```bash
git clone https://github.com/nezzhang/AI-Blockchain-RD-Lab.git
cd AI-Blockchain-RD-Lab
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest            # 457 tests, all green = nothing hidden by a broken suite
.venv/bin/python scripts/r25_verify_bundle.py
```

The publication bundle (`reports/release/bundle-cand-9200b07691c3/`)
ships its own verifier and runtime: `python verify.py .` from inside
re-runs every reproducible published number with no repo, no database,
no package install.

## Where the load-bearing code lives

| System | Path | What to attack |
|---|---|---|
| §19 deterministic scorer | `src/blockchain_rd_lab/scoring/` | Can a candidate farm the imputation floor? Do weights/exclusions match the docs? |
| §20 fatal-flaw gate | `src/blockchain_rd_lab/redteam/service.py` | "Fatal only when the strongest attack is also profitable" — the profitability boolean is demoted to a hypothesis (audit 2026-09-14 F1); the gate now MEASURES: battery worst edge vs the canonical `FLAW_EDGE_THRESHOLD` (400, `simulation/adversarial.py`), fail-closed for rejection when unmeasured. Attack the measurement path: can a fatal-worthy flaw measure under threshold? Can the pin counterfactual (`_pin_is_load_bearing`) be fooled into calling a stopped drain a converged EMA? |
| Attack battery (8 choreographies) | `src/blockchain_rd_lab/simulation/adversarial.py` | Do the classification layers (regime-tracking, transit, ratchet, wedges) hide edges they claim to disclose? Read the tests named `test_*hidden*` / `test_*never*` first — they are the anti-hiding probes; try to defeat them. |
| Deterministic interpreter | `src/blockchain_rd_lab/simulation/interpreter.py` | Everything rests on this. Does the arithmetic faithfully express the model JSON? Are clips/steps/feedback (§14) correct? |
| Anti-reward-hacking guard | `src/blockchain_rd_lab/discovery/curriculum.py` | The r7 vacuum happened before this existed. Would it catch the next one? |
| Report assembly (no report-writer LLM) | `src/blockchain_rd_lab/reporting/` | Every published number should trace to stored evidence. Dossiers/release packages are code-assembled — can prose drift from data? |

The full method is `MASTER BUILD PROMPT.md` (§2 evidence rules, §15
battery, §19 scoring, §20 gate, §27 ladder). `CLAUDE.md`/`GEMINI.md`
carry the round-by-round history — including every failure the lab
caught in itself. Read rounds 27-33 to see what four external audits
and two self-sweeps already fixed; do not re-report those.

## Known honest weaknesses (start here, they are real)

1. **5 of 11 score dimensions are imputed at the 5.0 offline floor**
   for every ranked candidate (offline mode, disclosed per dimension
   in `score-decomposition.json`). The corpus-wide ranking carries
   this caveat.
2. **The rank-1 vs rank-2 gap rests on ONE agent judgment**
   (`oracle_feasibility`, +0.50 at 10% weight) — disclosed in
   `reports/release/decision-brief-r21.md`, never smoothed.
3. **Deterministic choreographies are not real attackers.** Every
   bound is "under named attack patterns against a deterministic
   interpreter" — simulation-stage evidence, labeled as such on every
   artifact. The next ladder stage (prototype) exists to test this.
4. **Prior-art depth: one distinct multi-source finding (BIS).**
   Novelty claims are corpus-relative to the searched sources,
   scoped verbatim in `prior-art.json` and every dossier.
5. **Open research vectors** (disclosed in §4 of the release package):
   the successor's final model carries zero open residuals, but
   earlier-era finalists carry honest open surfaces; the wage-pool
   successor's `P_a` tenure-denial griefing vector is measured,
   disclosed, and unfixed by design (small honest cost).

## How to file findings

Open a GitHub issue, or write a `*-FIXES.md` file in the repo style
the previous auditors used (`cand-...-FIXES.md`). Discipline on this
side: every finding is verified against the store before any fix
(§2 applies to audits too), fixed at the generator, and pinned by a
test the day it ships — see the matching `*-FIXES-RESPONSE.md`
beside each audit for the finding-by-finding verification and the
probe that pins each fix. Disagreement is welcome — the criticism
stage is the point of publishing.
