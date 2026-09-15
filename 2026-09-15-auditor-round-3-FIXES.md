# Audit Findings — 2026-09-15 (round 3)

Repository: `nezzhang/AI-Blockchain-RD-Lab` (`main`)

Scope: fresh hostile re-audit following the fixes applied after the 2026-09-15 second-pass audit. The audit followed `AUDITING.md` and `CLAUDE.md`, concentrating on the four load-bearing systems in the methodology table and excluding previously fixed rounds 27–30 and the already-filed 2026-09-14/15 findings.

## Result

**No new verified security/methodology finding was identified in the requested scope.**

### §19 deterministic scorer

The scorer still imputes every absent configured dimension to `5.0`, exactly as the documented methodology says. The implementation validates the configured weights, computes the weighted score deterministically, and applies the fatal-flaw cap only to confirmed flaws. The imputation-floor issue remains a disclosed methodological limitation, not a newly introduced bypass, so it is not re-filed here.

### §20 fatal-flaw gate

The previous trust-bit problem is fixed in the live implementation. `redteam/service.py` imports the canonical `FLAW_EDGE_THRESHOLD`, calls `_measured_flaw_edge()` for every non-terminal `fatal` verdict, persists the gate evidence, and rejects only when the deterministic battery reports a worst headline edge above the threshold. The `strongest_attack_is_profitable` field is retained only as recorded hypothesis metadata and does not trigger measurement or rejection.

The repository's current `CLAUDE.md` records two end-to-end regression probes for the suppression direction (`profitable=false` still measured; `profitable=false` cannot shield a measured 2266-edge model), and reports 466 passing tests after round 36. The relevant live service implementation matches that documented behavior.

### Attack battery classification

The previously identified calibration-reset defect is fixed: long-window confirmation uses `spec.model_copy()` and carries the full attack calibration while doubling the horizon. The pin counterfactual is present at the measured-window and long-window/quiet-tail guard sites, and the cache key uses full serialized `PatternSpec` content, preventing cross-calibration verdict reuse.

The regime-tracking, transient, transit, drift-wedge, and resonance/quiet-tail layers therefore remain explicit classifications rather than silent deletion paths in the current code inspected. The round-34/35 regression notes also record re-sweeps across the default and calibrated grids.

### Deterministic interpreter

The schema and interpreter now share the canonical math-constant set. `interpreter.py` imports `_MATH_CONSTANTS`, defines values for the same names, performs a module-load parity check, and resolves `e`/`pi` during evaluation. This closes the earlier schema-valid-but-unexecutable drift.

## Residual limitation (not filed as a new finding)

The §20 rejection instrument intentionally measures the eight **default** attack calibrations; off-default robustness is delegated to the census/calibration layer and disclosed separately. This is an explicit methodological scope choice in the current `AUDITING.md` and `service.py` documentation. A flaw visible only outside the default calibration therefore need not cause automatic rejection at §20, but it is expected to surface in the off-default census. I did not find a contradiction between that declared scope and the current implementation that rises to a newly verified defect.

## Verification note

Direct live-source inspection was possible through the repository's public raw files. The container still cannot resolve `github.com`, so I could not independently run the repository's full local pytest suite in this environment. Test status cited above is the repository's current recorded test result in `CLAUDE.md`; code-path conclusions were verified directly against the current public source.
