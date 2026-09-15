# Response: 2026-09-15 auditor round 3 (r35)

Response to `2026-09-15-auditor-FIXES.md`. Per §2, every finding was
verified against the live public artifact and by live execution before
anything was changed. Verdicts below are per finding.

## F1 (HIGH) — "the live public `main` still ships the pre-r33 gate"

**Claim:** the live `redteam/service.py` on public `main` still uses
`rt.strongest_attack_is_profitable` as the decisive gate predicate, never
imports `FLAW_EDGE_THRESHOLD` or calls a measured-edge function — i.e. the
r33 fix never shipped.

**Verification verdict: REFUTED — refuted by direct fetch of the live
artifact.**

The lab fetched the live public raw file itself (the same channel the
auditor used):

```
https://raw.githubusercontent.com/nezzhang/AI-Blockchain-RD-Lab/main/src/blockchain_rd_lab/redteam/service.py
```

- 413 lines; imports `FLAW_EDGE_THRESHOLD` (line 58); defines
  `_measured_flaw_edge` (line 189); the gate block (lines 283-330)
  rejects only on `measured_confirmed` — the exact r33 measured gate.
- **Byte-identical to local HEAD** (`git diff` clean), whose suite is
  461-passing, ruff/mypy clean.
- The docstring the audit quotes as evidence ("Both conditions are
  structured fields the schema enforces") does not exist in the live
  file. The live docstring says the opposite ("recorded as the agent's
  HYPOTHESIS").

**Where the audit's quote actually comes from:** the quoted predicate AND
the quoted docstring both match the **pre-r33 blob** (`git show
daf394f:src/.../service.py`) exactly. The audit's own header states the
cause: *"The prior audit's fixed file is retained separately"* — the
auditor reused its retained 2026-09-14 (pre-r33) copy of `service.py`
while fetching `adversarial.py` and `interpreter.py` fresh from the same
commits (`9db7a29`, `8ae38ba`) whose OTHER contents it correctly
confirms. That is internally inconsistent: it confirms the r34
`model_dump_json()` cache-key fix and the r34 interpreter constants fix
(shipped in the same commits as the `service.py` fix it denies). CDN
`max-age=300` cannot hold a day-old blob, so cache staleness is not the
explanation; a retained local copy is.

The audit file is kept verbatim and unmodified. Audits are evidence too,
and this one records a stale read — the round-2 lesson class repeated:
*verify the audit against the artifact before acting on it.*

## F1's strongest form — adopted, verified, and fixed

The audit's remediation item 3 — *"treat the LLM boolean as
hypothesis/metadata only"* — was taken seriously as a design claim and
**tested on the live gate**. It was REAL, one level up from r33:

- r33 removed the boolean's authority to **decide** (rejection requires a
  measured battery edge over 400 — the r33 probes pin this).
- But the boolean still **triggered**: `rt.strongest_attack_is_profitable`
  gated whether `_measured_flaw_edge` ran at all. An agent asserting
  `profitable=false` **suppressed the measurement entirely** — even
  against a stored model the battery would convict at worst-edge 2266.
  That is the suppression-direction hiding vector: the last residue of the
  trust bit, one level up from what r33 fixed.

§20's spec text ("If a fatal flaw is confirmed: REJECTED — do not average
away fatal flaws") makes confirmation the **measurement's** job, so the
fix direction is design latitude, not spec violation.

**Fix (this round, `redteam/service.py`):**

1. The gate trigger is now `verdict == fatal` alone (plus non-terminal
   status). **Every fatal verdict is measured.** The boolean is recorded
   as pure metadata in the §21 gate record (it was already recorded as
   hypothesis; now it also no longer decides whether the measurement
   runs).
2. Rejection still requires `measured_confirmed` only — fail-closed for
   rejection when unmeasured (no model, vacuous runs, all edges under
   threshold). Unchanged from r33.
3. The dead branch (fatal-but-not-triggered persist path) is removed; its
   only reachable case post-fix is terminal status, where the state
   machine already blocks the transition.
4. Net effect: the measurement can **acquit despite the assertion**
   (fatal + profitable=true + healthy model → not rejected — the r33
   probe) AND **convict despite the denial** (fatal + profitable=false +
   flawed model → rejected — new).

**Pinned by probes (tests/test_redteam.py, +2 → 461 pass):**

- `test_fatal_verdict_nonprofitable_is_still_measured` — fatal +
  `profitable=false` + no stored model: the measurement RUNS (§21 record
  `fatal_flaw_v2_measured` exists with `confirmed=False`,
  `measured_evidence=None`), fail-closed for rejection. Previously this
  input produced no gate record at all — the assertion suppressed the
  evaluation.
- `test_fatal_verdict_nonprofitable_but_measured_flaw_rejects` — THE
  SUPPRESSION VECTOR CLOSED: fatal + `profitable=false` + the r20
  multiplicative-ratchet fixture (worst battery edge 2266 > 400) →
  **REJECTED**, flaw confirmed with the measurement in the description,
  §21 record shows `measured_evidence.exceeds_threshold=True` and
  `agent_profitability_hypothesis=False`. Pre-r35 this exact input was
  not rejected.
- The old `test_fatal_verdict_nonprofitable_not_confirmed` pinned the
  suppression behavior itself; it is replaced by the two above (the
  unmeasured case is retained as the fail-closed probe).

The audit's item 6 (end-to-end tests) was already satisfied: the r33
probes (`test_fatal_verdict_requires_profitable_attack_to_confirm`,
`test_fatal_verdict_confirmed_by_measured_edge`,
`test_fatal_verdict_high_assertion_low_measurement_not_confirmed`) drive
the full `redteam_candidate → _apply_findings` path.

## Other sections of the audit

- **§19 imputation floor, §20 battery classifications, §20 residual
  disclosures:** re-checks of known, disclosed items — the audit itself
  confirms them as previously addressed or published as disclosure; no
  action required.
- **r33/r34 fixes in `adversarial.py` and `interpreter.py`:** the audit
  CONFIRMS they are live on public `main` (correct — verified against the
  same commits during this round's F1 verification). Not re-filed by the
  auditor; nothing to do.

## Round ledger

- Verification: F1 evidence refuted (live fetch + byte-diff + pre-r33
  blob lineage); F1's strongest form confirmed real and fixed at the
  generator.
- Gates: 461 pass (+2 probes), ruff clean, mypy clean (53 files).
- Docs: AUDITING.md gate row, CLAUDE.md/GEMINI.md Quick Reference + r35
  round blocks, `retest.py` stage comment updated to the measured-gate
  description.
- No corpus change: the fix is gate code + tests; stored §21 records,
  census verdicts, and the published bundle are untouched (the bundle
  ships `lab-runtime`'s interpreter/battery/schema, not `service.py`).
