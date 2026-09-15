# Audit Findings — 2026-09-15

Repository audited: `nezzhang/AI-Blockchain-RD-Lab` (`main`)

Scope: second-pass hostile audit against the live public `main`, following the 2026-09-14 findings and the repository's own round-34 pre-audit notes. Rounds 27–30 findings were excluded from re-reporting; F2/F3 from 2026-09-14 were re-checked and are fixed in the live `main` code.

> Execution note: the container still cannot resolve `github.com`, so a literal filesystem clone was unavailable. The current public `main` was audited file-by-file through GitHub Raw. The prior audit's fixed file is retained separately; this file records only second-pass findings.

## F1 — HIGH: the live §20 gate still trusts `strongest_attack_is_profitable`; the documented r33 measurement fix is not present in the shipped `redteam/service.py`

### Status
**Confirmed in the current public `main`.** This is a regression / claim-vs-code mismatch, not a new conceptual variant of the 2026-09-14 finding.

### Evidence
`AUDITING.md` now says the gate “MEASURES” the battery's worst edge against `FLAW_EDGE_THRESHOLD`, and `CLAUDE.md` records the r33 fix as shipped. However, the actual public `src/blockchain_rd_lab/redteam/service.py` still implements the old predicate:

```python
if (
    rt is not None
    and rt.verdict == _VERDICT_FATAL
    and rt.strongest_attack_is_profitable
    and candidate.status not in _TERMINAL
):
```

The same file's module docstring also explicitly describes the boolean as a structured field that directly participates in the gate.

By contrast, the current `simulation/adversarial.py` does contain the canonical `FLAW_EDGE_THRESHOLD = 400.0`, but `redteam/service.py` does not import or call a measured-edge function and does not inspect persisted attack-battery evidence before rejection.

### Why this is decisive
The repository's central claim is “LLM proposes. Code tests. Evidence decides.” The live gate still lets the red-team agent decide the economic predicate through `strongest_attack_is_profitable`.

A fatal report with:

```json
{
  "verdict": "fatal",
  "strongest_attack_is_profitable": true
}
```

can still directly reject a candidate even when there is no deterministic battery measurement wired into the gate. Conversely, a fatal report with the bit set false can avoid rejection regardless of what the deterministic attack battery would measure. The r33 documentation describes a fail-closed measurement path, but that path is absent from the live service implementation.

### Verification against the earlier fix record
The current `CLAUDE.md` says the r33 fix should:

- measure the latest stored model;
- compare the worst deterministic headline to `FLAW_EDGE_THRESHOLD`;
- fail closed when unmeasured;
- persist a gate-v2 measurement record.

None of those operations appears in the current `redteam/service.py` shown above. This is therefore directly verifiable as an implementation/documentation mismatch.

### Required remediation
Restore the measured gate at the actual generator/source of truth, not just in documentation:

1. Import and invoke the deterministic battery measurement used by the published census.
2. Reject only when `verdict == fatal` **and** measured worst-edge > `FLAW_EDGE_THRESHOLD`.
3. Treat the LLM boolean as hypothesis/metadata only.
4. Fail closed when the model is missing, the battery is vacuous, or no measured edge exists.
5. Persist one gate-evaluation record containing verdict, hypothesis, measured evidence, threshold, and decision.
6. Add an end-to-end regression that exercises `RedTeamService._apply_findings()` with contradictory LLM and deterministic evidence, rather than testing only the boolean branch.

---

## §19 imputation-floor check — no new finding

The second pass still finds the documented behavior in `scoring/__init__.py`: each missing configured dimension receives `missing_score_default = 5.0`. This remains the explicitly disclosed offline weakness in `AUDITING.md`. I did not find a distinct new bypass or an implementation change that makes it worse than the known limitation, so it is not re-filed.

## §20 attack-battery classification check — prior transit/pin/calibration defects are fixed

The live `simulation/adversarial.py` now:

- carries the full `PatternSpec` calibration through the doubled-window transit test using `spec.model_copy(...)`;
- keys the pin counterfactual cache on `spec.model_dump_json()` plus state symbol, preventing cross-calibration collisions;
- uses the load-bearing counterfactual at the relevant classification sites;
- keeps the measured threshold constant in the adversarial module.

Those changes match the r34 notes in `CLAUDE.md` and are not re-reported.

I also did not find a verified new way, in the inspected classification path, to turn a genuine measured state/consumer edge into a `regime_tracking` / `transit` / `ratchet` disclosure solely through the previously identified calibration, pin-position, or cache-key weaknesses. The current code explicitly carries the calibration and counterfactual through the long-window and quiet-tail layers.

## Interpreter check — prior e/pi drift is fixed

The live interpreter imports the canonical `_MATH_CONSTANTS`, checks set parity at module load, and resolves `e`/`pi` during evaluation. This matches the r34 fix record and closes the 2026-09-14 F3 condition. It is not re-filed.
