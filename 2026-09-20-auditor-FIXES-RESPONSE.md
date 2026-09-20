# Response: 2026-09-20 audit — F3 overall_score / dimension-scores drift

## Verification scope

The finding was produced by the lab's own robustness pass over the live corpus
(§2: verified by live execution against the store and the committed bundle
before any fix). Initial working diagnosis — "the published headline is stale"
— was itself **corrected mid-investigation** against the committed evidence.
What follows is the verified account.

## F3 — overall_score can drift from the dimension rows it summarizes

**Verdict: CONFIRMED (the invariant was unenforced). The DRIFT lived in the
local store, not the published bundle. Fixed at the write path; store healed
by evidence recovery; the committed bundle is unchanged and still verifies.**

### What was actually wrong (corrected diagnosis)

`overall_score` is a denormalized cache of the deterministic §19 composite over
a candidate's dimension `scores`. Before this fix, **nothing enforced that the
two stay consistent**: `RankingService.score_candidate` set the composite and
`save_candidate` persisted dimension rows, but any later save could rewrite the
dimension rows while carrying the old composite forward.

The r40 store recovery (`scripts/r40_rebuild_store.py`, "store recovery from
committed artifacts") exercised exactly that hazard **incompletely**:

- The committed publication bundle for `cand-9200b07691c3` is **internally
  consistent**: its `score-decomposition.json` carries 11 dimension rows
  (incl. `oracle_feasibility=8.0`, `security=7.0`) that sum to the published
  **6.45** headline.
- The r40-rebuilt local store kept only **4** of those dimension rows and,
  because the composite was never recomputed, still showed **6.45**. The same
  store's recomputed value over its (incomplete) rows was 5.95 — and it had
  also **lost entire evidence categories** the bundle ships (red-team history,
  prior-art, scenario results, most adversarial bounds).

So the store and the bundle disagreed, and an unguarded read of the store made
the published headline *look* wrong. Under §2 the artifact and the store must
agree; the incomplete recovery, not the published number, was the defect.

### The fix (root cause, at the write path)

`src/blockchain_rd_lab/database/__init__.py` — `save_candidate` now **derives**
`overall_score` from the very dimension rows being persisted, in the same
transaction, for candidates in the SCORED lifecycle (`SCORED` / `FINALIST` —
the only statuses that carry dimension evidence in practice):

- scored-status candidate **with** dimension rows → composite is recomputed
  from those rows (drift impossible);
- scored-status candidate with **no** dimension rows but a retained composite →
  the composite is dropped to `None` (no evidence, no score);
- **pre-scoring** statuses (`GENERATED`…`RED_TEAM`) are untouched: they
  accumulate sub-scores across stages and are unscored by design, so they do
  not gain a composite.

### Store healing (evidence recovery, the §2 pattern done completely)

The committed bundle's `score-decomposition.json` is the surviving **evidence**
for the candidate's full dimension set. The two rows the r40 rebuild dropped
(`oracle_feasibility=8.0`, `security=7.0`) were restored into the store from
that file with explicit provenance rationale; the store's composite now
recomputes to the published **6.45** and the bundle's headline reproduces from
the store. The recommended candidate is `cand-9200b07691c3` (6.45, rank 1),
consistent across store, ranking, dossier, release package, and bundle.

The committed publication artifacts were **not** regenerated — regenerating
from the degraded store would have *dropped* evidence (red-team history,
scenario results, adversarial bounds) the committed bundle carries. The
bundle remains the authoritative artifact and still passes `verify.py`
(exit 0).

### Hardening that ships regardless of diagnosis

`scripts/r24_publication_bundle.py` — the bundle README's rank/status line is
now **computed from the store's current finalist standings**, never asserted
("rank 1 of N (recommended)" only when the store actually ranks it 1). A
bundle can no longer claim a standing the store contradicts.

## Regression pins (each verified to FAIL on pre-fix code)

`tests/test_database.py::TestOverallScoreIntegrity`:
- `test_overall_score_derived_from_dimension_rows` — a manually-set wrong
  composite (9.99) is overridden by the engine's value over the actual rows;
- `test_scores_cleared_drops_composite` — clearing dimension evidence drops
  the composite to None;
- `test_dimension_update_rescores_atomically` — a dimension change re-scores
  in the same save;
- `test_unscored_status_never_gains_a_composite` — a RED_TEAM candidate with
  sub-scores stays unscored (composite None).

(`tests/test_release_package.py` fixture updated to supply real dimension
evidence instead of setting `overall_score` directly — the fixture, not the
invariant, was wrong.)

## Validation

- 591 tests passed (587 prior + 4 new integrity pins)
- Ruff clean (`src`, `tests`, `scripts`); mypy clean (60 source files)
- No import cycle (`database` ⇄ `scoring` verified)
- Committed bundle `verify.py .` exit 0 (51 reproduced + headline consistent)
- Store ↔ bundle ↔ ranking ↔ release package all agree on the recommended
  candidate at 6.45

## Honest residual (out of scope, flagged)

The r40 store rebuild's **other** evidence losses (red-team history, prior-art,
scenario results, full adversarial-bound censuses) are **not** restored by this
change — only the score-row drift is. The store is therefore consistent but
less complete than the committed bundle. A full store rebuild that recovers
*every* evidence category from the committed artifacts is the correct follow-up
before any future `lab report` / bundle regeneration should be trusted to
reproduce the committed bundle byte-for-byte.

---

## r48 follow-up — full evidence recovery for the publication subject

The residual above is now closed **for the publication subject**
(`cand-9200b07691c3`, the only candidate the committed bundle carries evidence
for). Recovered from the committed bundle into the store (additive-only; no
candidate re-save, so no composite was touched):

- **5 experiments** — the 3 adversarial-pattern census records
  (`exp-779ad60c78f9`, `exp-15a351751f2c`, `exp-2240c2647989`; the 8-bound
  default + two 27-bound sweeps) and the 2 §15/Monte-Carlo records
  (`cand-9200b07691c3-scenarios-v3`, `…-montecarlo-v3`). Restored with their
  original `experiment_id`s (§21: a record is a lookup, not a regeneration).
- **12 red-team reports** — the full v1→v3 red_team / oracle / security /
  game_theory history.
- **1 prior-art record** — the BIS margin-buffer prior-art finding.

Round-trip fidelity verified: the recovered scenario and adversarial-bounds
experiments reproduce the bundle's stored `results` exactly. The subject's
evidence trail is complete again (`models=1, rt=12, exp=9, priorart=1`), and
its composite is unchanged at 6.45.

### Latent bug the recovery exposed (fixed): §4b rendered the wrong battery

Regenerating the bundle against the recovered store surfaced a real disclosure
defect the thin r40 store had been *masking*: `ReleasePackageBuilder._adversarial_bounds`
picked the candidate's census record with the most `"bounds"` entries, and the
recovered §17 supply-attack census (`r41-supply-battery-census`, 65 tokenomics
rows) outranked the genuine §20 mechanism sweeps (27 rows) — so §4b silently
rendered tokenomics supply bounds (wash_mint / total_minted) instead of the
mechanism attack bounds (crash_park / vol_oscillation). The verifier's
`§4b calibration completeness` check caught it (`[!]`, exit 0). **Fix**
(`reporting/release.py`): the §4b picker now excludes any record explicitly
tagged as a non-mechanism battery (`parameters.battery` not starting
`attack_patterns`), so the census can never shadow the §20 disclosure; an
absent tag stays eligible (legacy r13/r14-era §20 records carry
`parameters={}`). Regenerated §4b then renders all 19 calibration lines and
the verifier reports it fully clean.

### The committed bundle was NOT regenerated

The recovery proved the local store is a **partial** rebuild: the DB layer
does not round-trip the prior-art merge provenance (`merged_source_ids`) or
red-team `created_at` values the committed bundle carries (they came from the
pre-r40 store's duplicate rows / full timestamps), and the other 9 finalists
have no recoverable evidence in the repo at all. Regenerating the bundle from
the recovered store produced a strictly *worse* artifact, so it was reverted
to the committed version. The committed bundle remains the authoritative
artifact and passes `verify.py` exit 0.

### Remaining honest limit (documented, not hidden)

The **other 9 finalists** have near-zero stored evidence (the local store was
rebuilt thin at r40, and the repo carries recoverable detail only for the
published subject — the bundle ships the rank-1's trail, not every finalist's).
Their dossiers remain thin and their composites recompute from their (sparse)
dimension rows. This is a data-recovery limitation of the local corpus, not a
scoring defect: there is no committed evidence source to restore them from.
Reconstructing their full trails would require re-running the pipeline for
them (§41 — human call, and live-provider budget for the non-mock dims). A
store that can round-trip `merged_source_ids` / `created_at` (and re-run
evidence for the other finalists) is the correct follow-up before a byte-
identical bundle regeneration from the store is possible.

