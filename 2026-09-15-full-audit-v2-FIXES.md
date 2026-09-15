# Full Audit Findings — 2026-09-15 (fresh pass)

Scope: current public `main` of `nezzhang/AI-Blockchain-RD-Lab`, audited against `AUDITING.md`, the repository's stated prime directive (`LLM proposes. Code tests. Evidence decides.`), and the round 27–39 history. Findings already fixed in rounds 27–36 were not re-filed except where the current implementation still contains the previously reported defect.

Verification note: the environment cannot resolve `github.com`, so a literal clone/full pytest execution was not possible. Findings below are verified by direct inspection of the current public source and committed tests.

## F1 — HIGH — Economist `fatal` output still directly rejects candidates before deterministic measurement

### Claim
Phase 2 still treats an LLM-provided `EconomicConcern.fatal` bit as a confirmed fatal flaw and transitions the candidate to `REJECTED`.

### Code evidence
`src/blockchain_rd_lab/research/service.py`:
- `EconomicConcern.fatal` is an agent output field.
- `_apply_findings()` selects `fatal_concerns = [c for c in eco.concerns if c.fatal]`.
- Each becomes `FatalFlaw(... confirmed=True, identified_by="economist")`.
- `result.rejected = True`.
- The final branch transitions the candidate to `REJECTED`.

This is directly visible at lines 101–109 of `research/__init__.py` for the field, and lines 127–158 of `research/service.py` for the rejection path.

### Why it matters
The repository explicitly says agent output must not directly control deterministic parts of the system. An Economist can therefore remove a candidate from the funnel before formalization/simulation/red-team evidence exists. This is not the §20 gate; it is an earlier bypass of the same evidence principle.

### Test that proves the behavior
`tests/test_research.py::TestResearchService::test_fatal_concern_rejects` deliberately constructs an LLM fixture with `fatal=True` and asserts `REJECTED` plus a confirmed Economist flaw.

### Recommended fix
Treat economist `fatal` as an evidence-tagged hypothesis only. Persist it, but do not create a `confirmed=True` fatal flaw or reject. Let the candidate continue to the deterministic formalization/simulation/red-team gates. Replace the current test with a regression test proving `fatal=True` does not directly change lifecycle status.

---

## F2 — HIGH — §17 tokenomics oracle-manipulability score is added in the wrong direction

### Claim
The tokenomics scoring engine declares `oracle_manipulability` as a badness score (`10 = more manipulable = worse`), but then ADDS it to the overall score while ranking higher overall scores as better.

### Code evidence
`src/blockchain_rd_lab/tokenomics/scoring.py`:
- Lines 28–29 define `oracle_manipulability` as `10 = MORE manipulable = WORSE`.
- Lines 141–145 compute `oracle_manip = max(0.0, 10.0 - n_vectors * 2.5)`.
- Lines 154–160 say "lower oracle_manip is better, so invert it", but no inversion occurs; the value is added directly:
  `+ oracle_manip * _WEIGHTS["oracle_manipulability"]`.
- `rank_designs()` then sorts `overall` descending (lines 170–174).

### Exploit / consequence
A driver with *fewer* manipulation vectors gets a *higher* oracle score and therefore a *higher* composite rank. For example:
- 0 vectors -> oracle_manipulability = 10.0 -> contributes +2.5 to overall.
- 4 vectors -> oracle_manipulability = 0.0 -> contributes +0.0.

Thus increasing the number of known oracle attack surfaces can improve the design's rank relative to an otherwise identical design. This is the exact opposite of the declared semantics.

### Test gap
`tests/test_tokenomics.py` checks range, determinism, and descending sort, but contains no semantic test asserting that increased oracle-manipulation risk lowers `overall`.

### Recommended fix
Either store a positive `oracle_safety` score and add it, or keep `oracle_manipulability` as badness and subtract/invert it in the composite. Add a regression test comparing otherwise-equivalent low-risk vs high-risk drivers and requiring the lower-risk design to score higher.

---

## F3 — MEDIUM — §17 burn/mint capability detection tests the wrong state space and can mis-score drivers

### Claim
`_supply_fn_has_burn_path()` and `_supply_fn_has_mint_path()` do not generate driver-specific states. They run a small generic list of keys, so drivers whose actual signal key is absent from that list can be incorrectly classified as having no burn or mint path.

### Code evidence
`src/blockchain_rd_lab/tokenomics/scoring.py`:
- `_supply_fn_has_burn_path()` only probes trading volume, active users, GDP growth, productivity, AI throughput and prediction confidence.
- `_supply_fn_has_mint_path()` only probes trading volume, active users, GDP growth, network nodes, claims ratio and prediction confidence.

But the registry contains drivers whose decisive keys are not represented in these lists, including:
- climate risk (`climate_risk_index`),
- commodity price/target (`commodity_basket_price`, `commodity_target_price`),
- renewable energy (`renewable_energy_mwh`, `energy_target_mwh`),
- demographic population (`corridor_population`, `prev_corridor_population`), etc.

For example, `_climate_supply()` returns `-risk` and therefore has a real burn path, but `_supply_fn_has_burn_path()` never supplies `climate_risk_index`, so the function sees its default `0.0` and reports no burn path. The resulting dilution/game-theory scores are therefore wrong for that driver.

### Test gap
`tests/test_tokenomics.py` only asserts that scores are within `[0,10]`, deterministic, and sortable. The driver-registry test checks output boundedness, not that the scoring probes actually exercise each driver's documented positive/negative paths.

### Recommended fix
Make the path-detection probe states part of each `SupplyDriver` definition (or expose explicit deterministic `mint_probe_states` / `burn_probe_states`). Add per-driver tests asserting that documented bidirectional/unidirectional behavior is detected correctly.

---

## F4 — MEDIUM — Release-package explicit-candidate path accepts non-finalists

### Claim
`ReleasePackageBuilder._select(candidate_id)` accepts any existing candidate ID, even though the documented §27 explicit-subject path is for a human-selected finalist.

### Code evidence
`src/blockchain_rd_lab/reporting/release.py`:
- `_select()` returns any `cand.id, cand.name` when `candidate_id` is supplied, with no `CandidateStatus.FINALIST` check.
- `build()` therefore renders a release package for any stored candidate.
- The rendered subject note nevertheless says `"finalist (explicit §27 subject — the human's selection, not the ranking's)"` for every explicit candidate.

### Consequence
A `REJECTED`, `FAILED`, `SUPERSEDED`, `RED_TEAM`, or otherwise non-finalist candidate can be rendered through the release-package path and labeled as an explicit finalist. Because this artifact is specifically the publication-staging document, that creates a provenance/status integrity failure at the reporting boundary.

### Test gap
The reporting tests cover deterministic rendering and content but do not appear to test that an explicit release-package subject must actually be a finalist.

### Recommended fix
Require `CandidateStatus.FINALIST` in `_select()` for explicit IDs, or rename the path/document semantics if arbitrary candidates are intentionally supported. Add tests for rejected and non-finalist candidates.

---

## Re-check of prior findings

- §19 5.0 imputation floor: still present and still explicitly disclosed in `AUDITING.md`; not a new finding.
- §20 profitability trust-bit/suppression: fixed in current `redteam/service.py`; every fatal verdict is measured and the boolean is metadata only.
- Battery long-window calibration reset: fixed; the long-window run uses `spec.model_copy(...)` and preserves full calibration.
- Interpreter `e`/`pi`: fixed; canonical constants are accepted and evaluated.
- Previous reporting residual-vector filtering issues: current release builder still follows the r36 all-vectors / metadata-only rule.

## Overall assessment

The adversarial measurement layer is substantially stronger than the earlier revisions. However, the new §17 scoring layer currently contains a real ranking-direction error, and the Phase-2 Economist shortcut means the overall pipeline still does not fully satisfy its own `LLM proposes. Code tests. Evidence decides.` contract.
