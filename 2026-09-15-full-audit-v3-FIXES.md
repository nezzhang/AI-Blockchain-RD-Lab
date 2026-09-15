# Full Audit Findings — 2026-09-15 (third full pass)

Scope: current public `main` of `nezzhang/AI-Blockchain-RD-Lab`, re-read from `AUDITING.md`, `AGENTS.md`, `CLAUDE.md`, `MASTER BUILD PROMPT.md`, and the current source/tests. Prior findings fixed in rounds 27–36 were not re-filed unless the current implementation still contains the defect.

Verification note: this pass is against the public repository source. The audit environment cannot execute a local clone of GitHub, so no claim of an independently executed full pytest suite is made. The user's prior Mac evidence showed GitHub access works locally; the current public source was inspected directly.

## F1 — HIGH — Economist `fatal` remains an LLM-controlled rejection path

### Code evidence
`src/blockchain_rd_lab/research/service.py::_apply_findings()`:
- iterates economist concerns with `if c.fatal`;
- creates `FatalFlaw(... confirmed=True, identified_by="economist")`;
- sets `result.rejected = True`;
- final branch transitions the candidate to `REJECTED`.

This is inconsistent with the repository's prime directive and AGENTS rule that deterministic decisions must not be controlled by LLM output. `AGENTS.md` says “LLMs generate hypotheses ... Deterministic code simulates, validates, scores, and stores” and `CLAUDE.md` says “LLM output never directly controls deterministic parts.”

### Impact
An Economist can prevent formalization, simulation, and red-team measurement merely by emitting `fatal=true`. This is a pre-measurement kill switch, separate from the corrected §20 measured gate.

### Existing test gap
The behavior is intentionally exercised by the research test suite rather than prevented: the prior audit recorded `test_fatal_concern_rejects` as the regression that proves the shortcut remains.

### Fix
Persist the economist concern as an unconfirmed hypothesis/evidence item. Do not set `confirmed=True` or transition to `REJECTED`. Let later deterministic formalization/simulation/red-team gates establish fatality.

---

## F2 — HIGH — §17 oracle-manipulability composite still rewards risk

### Code evidence
`src/blockchain_rd_lab/tokenomics/scoring.py`:
- `oracle_manipulability` is documented as “higher = MORE manipulable = WORSE”;
- `oracle_manip = max(0.0, 10.0 - n_vectors * 2.5)` means fewer attack vectors produce a larger numeric value;
- the composite then adds `oracle_manip * 0.25`;
- rankings sort overall scores descending.

Therefore an otherwise identical design with fewer manipulation vectors receives a larger oracle contribution, which is directionally correct only if the value is an oracle-safety score. But the field is explicitly a manipulability score and the implementation comment says “lower oracle_manip is better, so invert it” without actually inverting/subtracting it.

### Concrete consequence
0 manipulation vectors => `oracle_manipulability = 10`, contribution `+2.5`.
4 vectors => `oracle_manipulability = 0`, contribution `+0.0`.
Thus the code's numeric field has badness semantics but its contribution has goodness semantics. The formula and field meaning disagree.

### Test gap
`tests/test_tokenomics.py` checks ranges, determinism, and descending sort, but not semantic monotonicity of oracle risk.

### Fix
Either rename/redefine the field as an oracle-safety score, or subtract/invert manipulability before composition. Add a regression comparing otherwise-identical low-risk and high-risk drivers and assert that higher manipulability cannot increase overall rank.

---

## F3 — MEDIUM — §17 mint/burn capability probes do not exercise each driver's own state variables

### Code evidence
`src/blockchain_rd_lab/tokenomics/scoring.py` uses fixed generic probe states for `_supply_fn_has_burn_path()` and `_supply_fn_has_mint_path()`.

The driver registry contains driver-specific keys that are absent from those probe sets, including:
- `climate_risk_index`
- `commodity_basket_price` / `commodity_target_price`
- `renewable_energy_mwh` / `energy_target_mwh`
- `corridor_population` / `prev_corridor_population`

Example: `_climate_supply()` returns `-risk`, so it has a genuine burn path. But the burn probe never supplies `climate_risk_index`; it therefore sees the default `0.0` and can classify the driver as having no burn path.

### Impact
Deterministic scoring can mis-score entire driver families because the capability test is probing the wrong state space, not the driver's documented semantics.

### Fix
Put canonical `mint_probe_states` and `burn_probe_states` on each immutable `SupplyDriver`, or create one deterministic probe specification per driver. Add per-driver regression tests for the documented directionality.

---

## F4 — MEDIUM — Explicit release-package subject is not constrained to FINALIST

### Code evidence
`src/blockchain_rd_lab/reporting/release.py::ReleasePackageBuilder._select()` returns any existing candidate ID when `candidate_id` is explicitly supplied. There is no `CandidateStatus.FINALIST` check.

The same module documents the explicit path as a human publication subject/finalist path, while the rendered evidence describes the explicit subject accordingly.

### Impact
A REJECTED, FAILED, SUPERSEDED, RED_TEAM, SCORED, or other non-finalist candidate can enter the §27 release-package builder via an explicit ID, creating a status/provenance mismatch at the publication boundary.

### Fix
Require `CandidateStatus.FINALIST` for explicit IDs. Add tests for every non-finalist terminal/non-final state and for a valid finalist.

---

## Re-check of previous findings

- §19 imputation floor: still disclosed in `AUDITING.md`; not a new finding.
- §20 profitability trust/suppression path: fixed; current `redteam/service.py` measures every non-terminal fatal verdict using the canonical threshold and records the LLM boolean as metadata only.
- Battery full-calibration propagation/cache-key/pin-counterfactual fixes: present in current `adversarial.py`.
- Interpreter `e`/`pi` canonical-constant parity: present in current interpreter.
- r36 residual-vector disclosure filtering: current release renderer keeps the metadata-only profitability rule.

## Assessment

The adversarial measurement core is now materially stronger, but the current public `main` still contains the same four verified issues above. I did not discover a fifth independent defect in this pass that meets the repository's “verified before reporting” standard without relying on unexecuted assumptions.
