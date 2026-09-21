# r49 — §19 score hardening: the 5 no-agent dimensions now carry real evidence

## What this is

AUDITING.md's known weakness #1: **5 of the 11 §19 score dimensions were imputed
at the 5.0 offline floor for every ranked candidate** — `technical_feasibility`,
`capital_efficiency`, `network_effects`, `communication`, `viral_potential`.
Those five are the §9 Blockchain-Architect / Quant / Market scoring roles, which
were never implemented as scoring agents, so nothing ever wrote them and the
scorer silently substituted the midpoint.

This round closes that for the finalist set through the §30 bridge provider (the
operator-as-LLM, no API key, no spend): the lab emits one structured bridge
request per missing no-agent dimension per candidate; the operator's judgment is
validated against a Pydantic schema, recorded as a §22 agent run, and stored as
a `ScoreBreakdown`; `save_candidate` (r48) recomputes the composite from the
fuller dimension set in the same transaction.

## What was built

- **`src/blockchain_rd_lab/scoring/assessment.py`** — `DimensionAssessment`
  (the bridge output contract: score 0-10, confidence ≤ 0.8, `INFERENCE`/
  `HYPOTHESIS` only, mechanism-specific rationale ≥ 20 chars),
  `DimensionAssessmentAgent` (the prompt: dimension rubric + candidate evidence
  + stored scores so far), `missing_dimensions`, `no_agent_dimensions`, and
  `assess_candidate`.
- **`lab assess`** CLI command — emits the bridge requests, fails closed
  (§30/§35), resumes as the operator answers.
- **`scripts/r49_assess_finalists.py`** — the operator-answer driver holding the
  authored judgments.
- **`tests/test_assessment.py`** — 14 pins.

## Hard rules the path enforces (each pinned by a test)

- **Additive only.** A dimension with a stored `ScoreBreakdown` is never
  overwritten — never a silent re-score (`test_never_overwrites_existing_dimension`).
- **Never impersonates a dedicated agent.** Dimensions a real agent produces
  (research: novelty / economic_coherence / market_demand; red team: game_theory
  / security / oracle_feasibility) are outside the assessor's scope even when
  missing — a missing agent-covered dim means an incomplete evidence trail to
  rebuild by re-running that stage, not a gap for a generic assessor to paper
  over (`test_never_fills_agent_covered_dimension`). This is why the thin
  finalists still show imputed `security`/`oracle_feasibility`/etc.: those need
  a red-team re-run (§41, live budget), which a generic assessor must not fake.
- **Confidence capped at 0.8, never FACT.** Operator readings of a dossier are
  calibrated judgments, not measurements, and are labeled as such.
- **Composite recomputes on write** (r48 invariant).
- **Dimension-mismatch guard**: a mislabeled answer can never write the wrong row.
- **Invalid answers never enter the store** (schema validation, §2).

## What changed in the scores (disclosed, never silent)

50 assessments installed (10 finalists × 5 no-agent dims), all `INFERENCE`,
all with mechanism-specific rationales a dossier reader can check. The
composites recomputed; the ranking shifted honestly:

| Candidate | before (5+ imputed) | after (0 no-agent imputed) |
|---|---|---|
| Separation-Keyed Fee Smoothing Escrow | 6.45 | **6.725** (11/11 real) |
| Demand-Index Escalation Ladder for FX Batches | 5.95 | 6.350 |
| Disagreement-Weighted Oracle Quorum | 6.025 | 6.325 |
| Quote-Deviation Slashed FX Reference Feed | 5.875 | 6.300 |
| Forecast-Indexed Fee Smoothing Pool | 5.95 | 6.200 |
| Prediction-Settled Hashprice Hedge Board | 5.95 | 6.175 |
| Escrowed Batch-Clearing Insurance Pool | 5.20 | 5.625 |
| Corridor-Native FX Batch Matching | 5.20 | 5.550 |
| Dual-Sided Bond Auction Rebalancer | 5.25 | 5.400 |
| Tranche-Segmented Settlement Guarantee Stack | 5.20 | 5.275 |

Rank-1 is unchanged (Separation-Keyed Fee Smoothing Escrow) and its composite
**strengthened** (6.45 → 6.725) with all 11 dimensions now real. The rank-2/3
order swapped (Demand-Index above Disagreement-Weighted) — a real, disclosed
consequence of replacing placeholders with evidence, not a defect.

## Honest side effect: the thin finalists' dossiers (§2, not a bug)

Regenerating reports exposed that the 9 non-published finalists carry **no
stored evidence** (0 models / red-team / experiments / prior-art — the r40
store-rebuild loss), while their previously committed dossiers *claimed* red-team
verdicts and scenario records. The regenerated dossiers are thinner because they
now reflect only what the store can prove — the §2 requirement ("nothing in this
report is free-form narrative; every claim traces to stored evidence"). The old
rich dossiers referenced evidence the current store no longer holds. This is
honest thinning, and it is the documented "9 thin finalists" limitation: their
full trails would require a pipeline re-run (§41).

## Publication surface after hardening

The rank-1 bundle regenerated: `score-decomposition.json` now shows **0 imputed
dimensions** (was 5), the README's imputation line is computed (no longer the
hardcoded "5 of the 11"), and the bundle's `verify.py` reproduces the hardened
composite (`sum(score*weight) = 6.7250 == published 6.7250`), exit 0, zero `[!]`
warnings. The rank-1 headline no longer rests on any imputed dimension.

## Validation

- 607 tests passed (593 prior + 14 new), ruff clean, mypy clean (61 files)
- Bundle `verify.py` exit 0, 0 warnings, hardened score reproduces
- 50 dimension-assessment agent runs recorded in the store (§22 provenance)
