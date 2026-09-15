# r40 Self-Audit Response — Tokenomics Pre-Audit Sweep + Store Recovery

**Date:** 2026-09-15
**Trigger:** "audit this" — the lab's r28/r34 discipline: run the hostile
pass over the newest code (r39 §17 Token Supply Mechanism Laboratory)
BEFORE any external auditor sees it, so no external audit finds anything
the lab could have found itself.

**Scope:** `src/blockchain_rd_lab/tokenomics/` (supply_drivers,
combinator, scoring, report) + `tests/test_tokenomics.py`.

**Method:** every suspected defect verified by LIVE EXECUTION before any
fix (§2: measure, never trust prose — including my own memory of code I
wrote; the shipped file had already drifted from the draft in memory).

---

## Context: the mid-session Codebuff audit

The human separately ran a Codebuff-mediated audit (commits `813d940`,
`54c73ca`, `ec2297a`; docs `2026-09-15-full-audit-v2-FIXES.md` /
`-v3-FIXES.md`). Its F2 independently found the §17 composite semantics
bug and its fix (oracle_manipulability as badness, SUBTRACTED in the
composite) landed at 19:55 — after this audit's F5 analysis began and
before its fix was applied. The r40 fixes below sit ON TOP of that
state and were verified against the post-Codebuff tree. No conflicts;
the two audits are complementary evidence.

## Findings — 3 confirmed, all fixed at the generator, all pinned

### F1 (HIGH) — physically impossible probe state bought a bidirectional credit

`climate-risk-burn`'s mint probe asserted `climate_risk_index = -1.0` —
NEGATIVE risk, impossible for a 0–1 index. Live verification:

- `supply_fn({"climate_risk_index": 1.0})` → −1.0 (physical max: BURN)
- `supply_fn({"climate_risk_index": 0.0})` → −0.0
- `supply_fn({"climate_risk_index": -1.0})` → +1.0 (UNREACHABLE input)

The scorer credited this burn-only driver a mint path (+5
death-spiral, +5 game-theory — scored 10.0/8.0) that no real input can
trigger. Class: the r33/r34 lineage — credit that ships because a
fixture and a defense COINCIDE.

**Fix:** probe states span the physical domain only;
`mint_probe_states=()` — the driver is honestly burn-only
(death_spiral 5.0, game_theory 3.0).
**Pinned by:** `test_climate_driver_is_honestly_burn_only` (asserts the
fn never mints on the physical domain AND the reduced scores).

### F2 (MEDIUM) — non-standard compatibility denominator let breadth tie focus

`compatibility_score = overlap / max(|mech_tags|, |driver_tags|)` —
asymmetric; when the mechanism's tag set is the larger, the denominator
is CONSTANT across drivers, so a broad 8-tag driver matching 3 TIED a
focused 4-tag driver matching 3 (both 0.500). Live verification on the
rank-1 candidate's real description showed exactly that tie.

**Fix:** Jaccard — `intersection / union`. Unmatched tags on EITHER side
reduce the score; focus and coverage both count.
**Pinned by:** `test_jaccard_ordering` (focused > broad at equal
overlap).

### F5 (MEDIUM) — reader-facing column rendered badness beside goodness

The §25 report's ranked-designs table rendered raw
`oracle_manipulability` (a BADNESS score: 10.0 = 4 attack vectors =
worst) beside three higher-better columns with no direction marker. A
reader naturally parses "Oracle Manip. 10.0" as good in a table where
Dilution 10.0 IS good. (The composite arithmetic was already correct
post-Codebuff: badness is subtracted; this finding is about the
PRESENTATION layer.)

**Fix:** the table column now renders **Oracle Resistance**
(`10 − badness`); every column in the table reads higher = better. The
raw vector count stays in the §25 prose section where it is disclosed
honestly.
**Pinned by:** `test_report_renders_oracle_resistance_not_manip`
(header present, old header absent, prose vector count still disclosed).

### Verified clean (no action)

- **F3 weights**: 0.30 + 0.25 + 0.25 + 0.20 = 1.00 exactly; composite
  bounds [0, 10]. Verified by computation across all 13 drivers.
- **F4 NaN/inf leakage**: `_clamp` catches NaN (→ 0.0), ±inf (→ ±1.0)
  at every exit. Verified with nan/inf/-inf/1e309 inputs on live
  supply functions.

## The store-loss event and recovery (the round's second half)

Running the full gates surfaced two failures UNRELATED to the audit
fixes — verified pre-existing at HEAD by stash-testing. Root cause:

1. **The venv was rebuilt under Python 3.14** (Homebrew upgrade;
   `pyvenv.cfg` → python@3.14, fresh site-packages). The project
   reinstall (`pip install -e ".[dev]"` + optuna) restored it.
2. **`database/lab.db` was emptied (0 bytes) at 19:24** — the live
   corpus store. Never git-tracked (`.gitignore: database/*.db` —
   operator session state by design). The bridge cache `.bridge/` was
   likewise empty.

**Option 1 (Time Machine):** BLOCKED — the backup volume exists but
reads require Full Disk Access (macOS TCC), which this session does not
have; `sudo` is also unavailable. Manual restore remains available to
the operator: System Settings → Privacy & Security → Full Disk Access,
then `tmutil restore` from Terminal.

**Option 2 (rebuild from committed artifacts):** EXECUTED —
`scripts/r40_rebuild_store.py`. Sources: lab-latest.md (funnel +
26-row ranking), graph-latest.json (96 lineage nodes), mint/batch
scripts (AST-extracted candidate content), discovery-run artifacts,
finalist dossiers (11-dimension sub-scores), the publication bundle
(model-v3, adversarial-bounds). Original candidate IDs pinned
everywhere; the r16–r20 supersede waves reconciled (the graph snapshot
predates them — its finalist/scored rows not in the report's ranked set
carry SUPERSEDED).

**Verification (all exact):**
- funnel: 100 candidates — 4 failed / 10 finalist / 16 rejected /
  16 scored / 54 superseded (matches published funnel to the digit)
- ranking: 26/26 rows reproduce the published table (ids, order,
  scores)
- curriculum guard: ok, 10 families, dominant share 0.23 (matches the
  r20 census record)
- battery: 27/27 headlines vs the NEWEST published records (25 exact
  vs the r20/r22 baseline; the 2 differences ARE the r33-documented
  corrections — pump_unwind@0.02 0.3374→0.0, grind_harvest@-0.9
  0.8634→0.9739 — byte-exact against the r33 record, i.e. the rebuild
  lands on the post-r33 corrected evidence state)
- §21 record stored: `r40-store-recovery` (event, sources,
  verification, honest not-recoverable list)

**Honestly not recoverable** (disclosed, not hidden): pre-r7 discovery
descriptions (lineage rows carry a disclosure placeholder), historical
per-experiment §21 rows (content lives in dossiers/bundle prose), the
r1–r9 bridge request/answer pairs.

## Gates

- pytest: **509 passed** (501 + 5 r40 probes + 3 Codebuff-era tests
  net; corpus test green on the rebuilt store)
- ruff: clean (src, tests, scripts)
- mypy: clean (58 source files)

## §17 attack-surface disclosure (new honest weaknesses, for AUDITING.md)

1. **Structural, not behavioral**: token scores measure structural
   properties (boundedness, bidirectionality, vector count) — no §15/§20
   adversarial simulation of supply dynamics yet. A §20-style battery
   for supply functions is future work.
2. **Self-reported vector counts**: `manipulation_vectors` is registry
   metadata; a driver "scores safe" partly by documenting fewer
   vectors. The count measures DISCLOSED surface, not true surface.
3. **Keyword tag matching**: `extract_mechanism_tags` is
   word-boundary keyword matching — no synonyms/stems ("remittance"
   matches fx; "money transfer" matches payment). Disclosed limitation.
4. **Probe states are driver-declared**: the bounded/mint/burn probes
   use the driver's own `*_probe_states` (F1's fix makes this honest —
   but it means path coverage is only as good as the declared probes).

## Lessons

- The shipped-code-drift lesson, again: verify against the file, not
  memory of writing it — two of five suspected defects were already
  fixed/different in the tree (the mid-session Codebuff commits).
- Environment events are audit findings too: the gates caught a venv
  replacement and a data-loss event that no code review would have.
- A rebuild is only honest if it VERIFIES against pre-existing
  published evidence — the r33 pattern (battery re-run vs bundle JSON)
  is what turns "we regenerated a store" into "the store is
  measurement-equivalent to the published record".
