# Response: 2026-09-15 full audit v4

## Verification scope

The v4 audit was compared against the current local and remote `main` at
commit `54c73ca` (`fix: close full-audit evidence and tokenomics gaps`). The
four findings in v4 describe the pre-`54c73ca` implementation and are not
present in the current published source.

## F1 — Economist fatal shortcut

**Verdict: REFUTED against current `main`; fixed in `54c73ca`.**

`research/service.py` preserves an Economist `fatal=true` concern as a
`FatalFlaw` with `confirmed=False` and does not set `result.rejected`. The
candidate continues through research to `PRIOR_ART_CHECKED`.

Regression: `tests/test_research.py::TestResearchService::test_fatal_concern_is_hypothesis_not_rejection` asserts the full path: the result is not rejected, the candidate remains `PRIOR_ART_CHECKED`, and the Economist flaw is unconfirmed.

## F2 — Explicit release-package subject status

**Verdict: REFUTED against current `main`; fixed in `54c73ca`.**

`ReleasePackageBuilder._select()` now returns `None` unless an explicit
candidate ID resolves to `CandidateStatus.FINALIST`. The valid explicit
finalist path remains covered by the publication/verifier fixtures.

Regression: `tests/test_publication_bundle.py::test_explicit_non_finalist_subject_is_rejected` proves a generated non-finalist cannot enter the release-package path.

## F3 — Driver-specific mint/burn probes

**Verdict: REFUTED against current `main`; fixed in `54c73ca`.**

`SupplyDriver` now carries immutable `burn_probe_states` and
`mint_probe_states`. All 13 registered drivers declare canonical states for
their own signal variables, including climate, commodity, energy,
demographic, network, AI, and hybrid drivers. The scoring functions probe
those declarations rather than a generic key list.

Regression: `tests/test_tokenomics.py::TestScoring::test_driver_probe_states_match_supply_paths` checks every registered driver.

## F4 — Oracle-manipulability semantics

**Verdict: REFUTED against current `main`; corrected in `54c73ca`.**

The current implementation treats `oracle_manipulability` explicitly as a
badness score: manipulation vectors increase it, and the weighted value is
subtracted from the composite. Safer designs therefore cannot receive a
lower overall score solely because they have fewer manipulation vectors.

Regression: `tests/test_tokenomics.py::TestScoring::test_oracle_manipulation_badness_lowers_overall` compares otherwise-equivalent low- and high-risk drivers and requires the low-risk design to score higher.

## Validation

The current implementation was validated with:

- 502 tests passed, 2 skipped, with two unrelated environment-dependent tests deselected (`optuna` unavailable and the local live corpus database empty)
- Ruff clean
- Mypy clean for all changed modules
- `git status` confirms `HEAD` and `origin/main` both point to `54c73ca`

The v4 audit remains preserved as evidence. Its findings should be read as a
stale-source report, not as open defects in the current public revision.
