# External Verification Report

Bundle: `bundle-cand-9200b07691c3` — verified from the published files alone (no database access), 2026-09-15T01:05:40Z

The verifier re-runs every reproducible claim with the lab's deterministic interpreter. A third party can re-run this script against the bundle and must obtain this report.

| Check | Verdict | Detail |
|---|---|---|
| README.md | **REPRODUCED** | sha256 verifies against the file |
| adversarial-bounds.json | **REPRODUCED** | sha256 verifies against the file |
| dossier.md | **REPRODUCED** | sha256 verifies against the file |
| lab-runtime/blockchain_rd_lab/__init__.py | **REPRODUCED** | sha256 verifies against the file |
| lab-runtime/blockchain_rd_lab/formalization/__init__.py | **REPRODUCED** | sha256 verifies against the file |
| lab-runtime/blockchain_rd_lab/simulation/__init__.py | **REPRODUCED** | sha256 verifies against the file |
| lab-runtime/blockchain_rd_lab/simulation/adversarial.py | **REPRODUCED** | sha256 verifies against the file |
| lab-runtime/blockchain_rd_lab/simulation/interpreter.py | **REPRODUCED** | sha256 verifies against the file |
| model-v3.json | **REPRODUCED** | sha256 verifies against the file |
| prior-art.json | **REPRODUCED** | sha256 verifies against the file |
| redteam-history.json | **REPRODUCED** | sha256 verifies against the file |
| release-package.md | **REPRODUCED** | sha256 verifies against the file |
| scenario-results.json | **REPRODUCED** | sha256 verifies against the file |
| score-decomposition.json | **REPRODUCED** | sha256 verifies against the file |
| verify.py | **REPRODUCED** | sha256 verifies against the file |
| manifest coverage | **REPRODUCED** | every bundle file is hashed; nothing unlisted ships |
| model integrity | **REPRODUCED** | parses and passes §13 checks (v3, 7 equations) |
| census records | **CONSISTENT** | 3 §20 census record(s) in the bundle (the §21 store is not part of the bundle; the re-run below recomputes them) |
| re-run crash_park | **REPRODUCED** | headline 0.5175 == published 0.5175 |
| re-run drift_creep | **REPRODUCED** | headline 0.0300 == published 0.0300 |
| re-run grind_harvest | **REPRODUCED** | headline 0.4915 == published 0.4915 |
| re-run pump_unwind | **REPRODUCED** | headline 0.9999 == published 0.9999 |
| re-run resonance | **REPRODUCED** | headline 0.0000 == published 0.0000 |
| re-run shock_timing | **REPRODUCED** | headline 0.4017 == published 0.4017 |
| re-run vol_oscillation | **REPRODUCED** | headline 0.9940 == published 0.9940 |
| re-run wash_flow | **REPRODUCED** | headline 5.1737 == published 5.1737 |
| default battery re-run (summary) | **REPRODUCED** | 8/8 default-calibration headlines reproduced from the published model JSON |
| re-run crash_park @park_shift=-0.3 | **REPRODUCED** | headline 0.2375 == published 0.2375 |
| re-run crash_park @park_shift=-0.9 | **REPRODUCED** | headline 0.8692 == published 0.8692 |
| re-run drift_creep @creep_rate=0.002 | **REPRODUCED** | headline 0.0048 == published 0.0048 |
| re-run drift_creep @creep_rate=0.01 | **REPRODUCED** | headline 0.1196 == published 0.1196 |
| re-run grind_harvest @harvest_shift=-0.3 | **REPRODUCED** | headline 0.1957 == published 0.1957 |
| re-run grind_harvest @harvest_shift=-0.9 | **REPRODUCED** | headline 0.9739 == published 0.9739 |
| re-run pump_unwind @amplitude=0.02 | **REPRODUCED** | headline 0.0000 == published 0.0000 |
| re-run pump_unwind @amplitude=0.1 | **REPRODUCED** | headline 0.9999 == published 0.9999 |
| re-run resonance @strike_shift=-0.3 | **REPRODUCED** | headline 0.0000 == published 0.0000 |
| re-run resonance @strike_shift=-0.9 | **REPRODUCED** | headline 0.0377 == published 0.0377 |
| re-run resonance @strikes=16 | **REPRODUCED** | headline 0.0010 == published 0.0010 |
| re-run resonance @strikes=2 | **REPRODUCED** | headline 0.0000 == published 0.0000 |
| re-run resonance @strikes=8 | **REPRODUCED** | headline 0.0002 == published 0.0002 |
| re-run shock_timing @lag_fraction=0.1 | **REPRODUCED** | headline 0.1862 == published 0.1862 |
| re-run shock_timing @lag_fraction=0.4 | **REPRODUCED** | headline 0.4017 == published 0.4017 |
| re-run vol_oscillation @amplitude=0.02 | **REPRODUCED** | headline 0.1187 == published 0.1187 |
| re-run vol_oscillation @amplitude=0.1 | **REPRODUCED** | headline 0.9999 == published 0.9999 |
| re-run wash_flow @wash_level=0.01 | **REPRODUCED** | headline 0.0023 == published 0.0023 |
| re-run wash_flow @wash_level=0.04 | **REPRODUCED** | headline 32.6375 == published 32.6375 |
| calibrated-sweep re-run (summary) | **REPRODUCED** | 19/19 calibrated-sweep headlines reproduced (the §4b @-tagged lines) |
| §15 battery | **REPRODUCED** | 13 scenarios run non-degenerately under the current interpreter |
| §19 score recomputation | **REPRODUCED** | sum(score*weight) = 6.4500 == published 6.4500 |
| score headline consistency | **REPRODUCED** | README carries the same 6.45 headline |
| imputation disclosure | **REPRODUCED** | 5 of 11 dimensions imputed at the 5.0 floor — disclosed per dimension |
| release package subject | **CONSISTENT** | release package names the manifest's candidate |
| §4b calibration completeness | **REPRODUCED** | 19 calibration-tagged records; §4b renders every one per kind |

Totals: 51 reproduced, 2 consistent, 0 not-reproducible.

**OVERALL: VERIFY-PASS** — every reproducible claim reproduces from the published files.
