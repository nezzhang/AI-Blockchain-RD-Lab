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
.venv/bin/pytest            # 565 tests, all green = nothing hidden by a broken suite
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
| §20 fatal-flaw gate | `src/blockchain_rd_lab/redteam/service.py` | The profitability boolean is demoted to pure metadata (audit 2026-09-14 F1 demoted it from decider to hypothesis; round 35 demoted it from trigger to metadata): the gate MEASURES every fatal verdict — battery worst edge vs the canonical `FLAW_EDGE_THRESHOLD` (400, `simulation/adversarial.py`), fail-closed for rejection when unmeasured. The measurement can acquit despite the agent's assertion AND convict despite the agent's denial. Attack the measurement path: can a fatal-worthy flaw measure under threshold? Can the pin counterfactual (`_pin_is_load_bearing`) be fooled into calling a stopped drain a converged EMA? |
| Attack battery (8 choreographies) | `src/blockchain_rd_lab/simulation/adversarial.py` | Do the classification layers (regime-tracking, transit, ratchet, wedges) hide edges they claim to disclose? Read the tests named `test_*hidden*` / `test_*never*` first — they are the anti-hiding probes; try to defeat them. |
| Deterministic interpreter | `src/blockchain_rd_lab/simulation/interpreter.py` | Everything rests on this. Does the arithmetic faithfully express the model JSON? Are clips/steps/feedback (§14) correct? |
| Anti-reward-hacking guard | `src/blockchain_rd_lab/discovery/curriculum.py` | The r7 vacuum happened before this existed. Would it catch the next one? |
| Report assembly (no report-writer LLM) | `src/blockchain_rd_lab/reporting/` | Every published number should trace to stored evidence. Dossiers/release packages are code-assembled — can prose drift from data? §4 residual disclosure (r36): every named attack vector must publish, the agent's `profitable_for_attacker` assertion is rendered metadata, never a filter — can a vector still be silently dropped? |
| §17 Token Supply Mechanism Laboratory (r39-r43) | `src/blockchain_rd_lab/tokenomics/` | 13 supply drivers with pure supply functions, a tag-based combinator (§18), deterministic scoring across 4 dimensions (dilution/death-spiral/oracle-resistance/game-theory), a §25 question report renderer, (r41) a supply-dynamics attack battery, (r42) dynamics-informed scoring consuming the measured edges, and (r43) a supply-stock composition layer measuring death-spiral dynamics under 7 demand scenarios. Attack surfaces in the dedicated section below. |

### §17 tokenomics attack surface (audited r40 — findings F1/F2/F5 fixed, see `2026-09-15-r40-self-audit-FIXES.md`)

- **Supply-function boundedness**: every `supply_fn` must clamp to
  [-1, 1] on ANY input (NaN → 0.0, ±inf → ±1.0 — verified at `_clamp`).
  Try to construct a state dict that leaks an unclamped or NaN value.
- **Probe states are driver-declared** (`burn_probe_states` /
  `mint_probe_states`): the mint/burn path credits are computed from
  the driver's OWN declared probes. F1's class: the climate driver once
  declared a physically impossible probe (`climate_risk_index=-1.0`)
  and was credited a bidirectional defense no real input can trigger.
  Check every probe state against the driver's documented input domain.
- **Manipulation-vector counts are self-reported**: oracle resistance
  is `10 - 2.5 × len(manipulation_vectors)` (floored at 5.0 for
  live-oracle drivers) — a driver "scores safe" partly by DOCUMENTING
  fewer vectors. The number measures disclosed surface, not true
  surface. Also: the report table renders RESISTANCE (higher = better,
  r40); the raw count appears in the §25 prose.
- **Tag extraction is keyword matching** (`_MECHANISM_KEYWORDS`,
  word-boundary regex): no synonyms or stems — "remittance" matches fx
  but "money transfer" matches payment. Keyword-stuffing a description
  can force driver matches; empty extraction honestly yields no
  designs (absence is a result, §18).
- **Compatibility score is Jaccard** (r40; was
  overlap/max(|A|,|B|) which let breadth tie focus): unmatched tags on
  either side now reduce the score.
- **Composite weights** (0.30/0.25/0.25/0.20) sum to 1.0; composite
  bounds [0, 10]; oracle badness is SUBTRACTED. Structural scores
  only — but see the battery section below: supply DYNAMICS are now
  measured (r41), closing the structural-only boundary for the
  registry.

### §17 supply-dynamics battery (r41; consumed r42) + stock layer (r43)

`tokenomics/battery.py` runs the §20 pattern against supply
functions directly: 5 named choreographies (wash_mint, round_trip,
resonance, creep, burn_park) × 13 drivers = 65 runs, §21 census
`r41-supply-battery-census`. What to attack:

- **The neutral finder** (`_neutral_state`): the matched base is an
  exhaustively-searched zero-pressure state with per-axis
  guard-smoothness rejection and L1-closest-to-probe selection. Its
  own first three drafts had bugs the tests caught (a greedy false
  neutral on the hybrid; a symmetric (0,0) degenerate passing an
  all-axis perturbation; an inflated interpolation path) — try to
  construct a probe where it still picks wrong.
- **Crafts ride the driver's OWN declared probes** — a driver with no
  mint probe makes mint-side patterns honestly VACUOUS (headline=None,
  never 0.0; the §20 convention). Check the vacuous set matches the
  registry's declarations (climate's 4 mint-side, claims-ratio's
  burn-side).
- **Edges are RATE-UNITS** (steps × clamped rate) — deliberately NOT
  comparable to §20's FLAW_EDGE_THRESHOLD (400, $-denominated stock
  edges). Any future supply-flaw threshold is a separate calibration
  decision; do not import the number.
- **Measured results worth re-checking**: no ratchet anywhere
  (resonance = round_trip × cycles, linear — a measured negative
  result); corridor-population's burn 6.0 vs mint 30.0 (the §25
  demographic asymmetry); metcalfe-growth's creep 52.51 exceeding
  every linear driver (log-region grinding).

The full method is `MASTER BUILD PROMPT.md` (§2 evidence rules, §15
battery, §19 scoring, §20 gate, §27 ladder). `CLAUDE.md`/`GEMINI.md`
carry the round-by-round history — including every failure the lab
caught in itself. Read rounds 27-44 to see what four external
audits, the Codebuff full-audit pass, and six self-sweeps already
fixed; do not re-report those.

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
   the successor's final v3 model carries 14 NAMED open surfaces, every
   one unprofitable-asserted (the pre-r36 filter hid them; r36 publishes
   all of them with the assertion rendered as metadata per line); the
   wage-pool successor's `P_a` tenure-denial griefing vector is
   measured, disclosed, and unfixed by design (small honest cost).
6. **§17 oracle dimension is self-reported; the stock layer is a
   single-elasticity model** (narrowed r43): the composite CONSUMES
   the r41 measured edges (r42) and the r43 stock layer measures
   composed death-spiral dynamics (7 scenarios x 13 drivers, §21
   census — ratio drivers stable, corridor's clamp fails the crash,
   gdp spirals both directions, the mis-mint melt). Remaining
   honest limits: oracle manipulability still counts SELF-REPORTED
   vectors (no battery oracle analogue); the stock layer composes
   ONE demand axis per driver (the hybrid's node axis rides at
   neutral — disclosed), at ONE elasticity (eta=0.5; the eta=0
   control is pinned, the full curve is not swept); one-sided
   bounded indices (climate/claims/prediction) are honestly
   VACUOUS — their crisis-mapping is a modeling assumption the
   registry does not declare.

## How to file findings

Open a GitHub issue, or write a `*-FIXES.md` file in the repo style
the previous auditors used (`cand-...-FIXES.md`). Discipline on this
side: every finding is verified against the store before any fix
(§2 applies to audits too), fixed at the generator, and pinned by a
test the day it ships — see the matching `*-FIXES-RESPONSE.md`
beside each audit for the finding-by-finding verification and the
probe that pins each fix. Disagreement is welcome — the criticism
stage is the point of publishing.
