# Full Audit Findings — 2026-09-15 (fresh pass v4)

Scope: current public `main` of nezzhang/AI-Blockchain-RD-Lab, re-read from AUDITING.md, AGENTS.md, CLAUDE.md, current implementation, and current committed tests. Previously fixed issues were re-checked and not re-filed unless still present.

Verification limitation: the auditor execution environment still cannot resolve github.com for a literal clone/full local pytest run. Findings below are verified against the current public source and committed tests.

## F1 — MEDIUM — §17 mint/burn capability detection still probes the wrong state space

### Verified status
STILL PRESENT.

`src/blockchain_rd_lab/tokenomics/scoring.py` uses hard-coded generic probe dictionaries in `_supply_fn_has_burn_path()` and `_supply_fn_has_mint_path()` instead of each driver's declared input/state variables.

The driver registry declares driver-specific signals such as `climate_risk_index`, `commodity_basket_price`, `commodity_target_price`, `renewable_energy_mwh`, `energy_target_mwh`, and `corridor_population` / `prev_corridor_population`. The scoring probe lists do not cover those variables.

Example: `_climate_supply()` reads `climate_risk_index`; the burn probe never supplies it, so the function sees its default zero and can fail to detect the driver's real negative-pressure path.

### Why this is a real defect

The score dimensions `dilution_resistance`, `death_spiral_resistance`, and `game_theory_stability` depend on `has_burn` / `has_mint`. A capability detector that never exercises the driver's actual signal can therefore deterministically score a whole driver family incorrectly.

### Test gap

`tests/test_tokenomics.py` verifies score ranges, determinism, and sorting, but does not assert per-driver semantic directionality for mint/burn path detection.

### Fix

Move canonical probe states onto each immutable `SupplyDriver`, or define a deterministic probe specification per driver. Add per-driver tests asserting both positive and negative paths where the driver claims to support them.

---

## F2 — MEDIUM — §27 explicit release-package subject can be a non-finalist

### Verified status
STILL PRESENT.

`ReleasePackageBuilder._recommended()` correctly selects only `CandidateStatus.FINALIST`, but `_select(candidate_id)` accepts any existing candidate and returns it without a status check. `build()` then labels any explicit subject as:

`finalist (explicit §27 subject — the human's selection, not the ranking's)`

Thus a REJECTED, SCORED, RED_TEAM, FAILED, or SUPERSEDED candidate can be rendered through the §27 release-package path with finalist semantics.

### Why this matters

The release package is a publication-staging artifact and its own documentation says the human selects a finalist. Allowing arbitrary candidate IDs creates a provenance/status mismatch: the artifact can represent a non-finalist as the human-selected finalist.

### Test gap

`tests/test_release_package.py` covers the valid explicit-finalist path but has no negative test for explicit non-finalists.

### Fix

Require `CandidateStatus.FINALIST` for explicit candidate IDs, or explicitly rename/redefine the feature so arbitrary candidate publication staging is intentional. Add negative tests for non-final states and a positive finalist test.

---

## F3 — LOW / DOCUMENTATION-SEMANTIC — §17 `oracle_manipulability` naming/comments contradict the actual composite direction

### Verified status
PRESENT, but the prior audit overstated this as a ranking exploit.

The field is documented as `10 = MORE manipulable = WORSE`, and the score is calculated as:

`10 - 2.5 * n_vectors` (floored at zero).

The composite then ADDS that value with a positive weight while ranking overall scores descending.

The resulting behavior is actually directionally favorable to safer designs: fewer manipulation vectors produce a larger contribution, and more vectors reduce the contribution. Therefore this is NOT a demonstrated "more risk improves rank" exploit.

The real defect is that the numeric field is semantically a safety score while being named/documented as a manipulability/badness score, and the source comment says it is "inverted" without performing an inversion.

### Why it still matters

Ambiguous sign conventions are dangerous in a deterministic scoring layer. A future weight change, report consumer, or second-order use of the field can easily invert the intended semantics.

### Fix

Rename the field to `oracle_safety` and document it as higher-is-better, or retain `oracle_manipulability` as a badness score and explicitly transform it once in the composite. Add a monotonicity test that increasing manipulation vectors never increases overall score.

---

## Re-check of earlier findings

- §19 5.0 imputation floor: disclosed in AUDITING.md; no new bypass found.
- §20 profitability trust/suppression: fixed; current redteam service always measures fatal verdicts and treats the LLM boolean as metadata.
- Battery calibration propagation: fixed; the long-window constructor uses `model_copy` with the caller's full calibration.
- Interpreter `e` / `pi`: fixed; canonical constants and parity check are present.
- Economist `fatal` pre-measurement rejection: FIXED in current public main; the test now asserts the fatal concern remains unconfirmed and the candidate stays `PRIOR_ART_CHECKED`.
- Residual-vector reporting suppression: fixed; current release/decision tests require unprofitable-asserted surfaces to remain disclosed.

## Overall assessment

The current main is materially improved. The two substantive remaining defects are the §17 per-driver mint/burn probe mismatch and the §27 explicit-subject status mismatch. The §17 oracle issue is a semantic-contract defect rather than the ranking exploit claimed by the previous audit; that distinction should be preserved in the repository's audit history.
