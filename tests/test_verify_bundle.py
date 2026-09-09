"""Round 25 probes: the external verifier is a NEW measurement layer
(its whole job is catching drift between published claims and
re-computed reality) — it gets its own tests the day it ships.

The pinned properties:
- tamper with a bundle file -> the verifier FAILS (the whole point)
- a clean bundle -> VERIFY-PASS with reproduced battery headlines
- the report lands NEXT TO the bundle (manifest coverage invariant)
- the manifest-coverage check catches unhashed files
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("blockchain_rd_lab")

import hashlib

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.reporting.release import (
    ReleasePackageBuilder,
)
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _mm(cid: str) -> MathModel:
    return MathModel(
        candidate_id=cid,
        version=1,
        variables=[
            {"name": "level", "symbol": "X_t", "role": "input",
             "units": "u", "description": "anchor level"},
            {"name": "delta", "symbol": "dX_t", "role": "input",
             "units": "u", "description": "level change"},
            {"name": "tracked", "symbol": "X_t1", "role": "state",
             "units": "u", "description": "tracked level"},
        ],
        parameters=[
            {"name": "speed", "symbol": "k", "description": "ema speed",
             "min_value": 0.1, "max_value": 0.9, "default": 0.5},
        ],
        equations=[
            {"name": "track", "expression": "X_t1 = X_t + k*dX_t",
             "description": "track the level"},
        ],
        assumptions=[
            {"statement": "level observable on-chain", "critical": True},
        ],
        open_questions=["does it hold under drift?"],
        rationale="test rationale long enough",
    )


def _cand() -> Candidate:
    c = Candidate(
        id="cand-ver",
        name="Verifier Test Mechanism",
        category="market",
        description="d",
        core_mechanism="c",
        problem="p",
    )
    for st in (CandidateStatus.RESEARCHING, CandidateStatus.PRIOR_ART_CHECKED,
               CandidateStatus.FORMALIZED, CandidateStatus.SIMULATING,
               CandidateStatus.RED_TEAM):
        c.transition(st)
    c.transition(CandidateStatus.SCORED)
    c.transition(CandidateStatus.FINALIST)
    c.overall_score = 6.0
    return c


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    db = LabDatabase(tmp_path / "v.db")
    db.create_all()
    db.save_candidate(_cand())
    db.save_math_model("cand-ver", _mm("cand-ver").model_dump_json(),
                       "v1", version=1)
    rb = ReleasePackageBuilder(db)
    rel = rb.build(candidate_id="cand-ver")
    assert rel is not None

    out = tmp_path / "bundle-cand-ver"
    out.mkdir()
    (out / "README.md").write_text("b\n", encoding="utf-8")
    (out / "release-package.md").write_text(rel, encoding="utf-8")
    (out / "model-v1.json").write_text(
        _mm("cand-ver").model_dump_json(), encoding="utf-8")
    # published bounds: computed honestly by the battery
    from blockchain_rd_lab.simulation.adversarial import (
        AttackPatternBattery,
        PatternSpec,
    )
    bat = AttackPatternBattery(_mm("cand-ver"))
    bounds = []
    kinds = [k for k in (
        "vol_oscillation", "wash_flow", "pump_unwind", "shock_timing",
        "crash_park", "drift_creep", "grind_harvest", "resonance")]
    for kind in kinds:
        b = bat.run_pattern(PatternSpec(kind=kind))
        bounds.append(b.model_dump(mode="json"))
    (out / "adversarial-bounds.json").write_text(
        json.dumps([{"experiment_id": "exp-test", "recorded_at": "t",
                     "parameters": {"battery": "attack_patterns"},
                     "bounds": bounds, "vacuous_count": 0,
                     "worst_edge": None}]), encoding="utf-8")
    (out / "prior-art.json").write_text("[]", encoding="utf-8")
    (out / "redteam-history.json").write_text("[]", encoding="utf-8")
    files = [f.name for f in out.iterdir()]
    (out / "MANIFEST.json").write_text(json.dumps({
        "candidate_id": "cand-ver",
        "files": {f: {"sha256": _sha(out / f), "bytes": (out / f).stat().st_size}
                  for f in files},
    }), encoding="utf-8")
    return out


class TestRound25Verifier:
    def test_clean_bundle_passes(self, bundle: Path) -> None:
        rep = Report()
        v = V
        # run main's pieces without SystemExit: call checks directly
        man = v._verify_manifest(bundle, rep)
        mm = v._verify_model(bundle, rep)
        assert mm is not None
        pub = v._verify_bounds(bundle, mm, rep)
        v._rerun_attack_battery(mm, pub, rep)
        v._verify_scenarios(mm, rep)
        v._verify_release_package(bundle, man, rep)
        assert rep.ok, [c.label for c in rep.checks
                        if c.verdict == "NOT-REPRODUCIBLE"]
        # and the battery re-run reproduced the published headlines
        rerun = [c for c in rep.checks if c.label.startswith("re-run ")]
        assert len(rerun) >= 8

    def test_tampered_file_fails_manifest(self, bundle: Path) -> None:
        (bundle / "README.md").write_text("tampered\n", encoding="utf-8")
        rep = Report()
        v = V
        v._verify_manifest(bundle, rep)
        assert not rep.ok

    def test_unlisted_file_fails_coverage(self, bundle: Path) -> None:
        (bundle / "sneaky.txt").write_text("x", encoding="utf-8")
        rep = Report()
        v = V
        v._verify_manifest(bundle, rep)
        bad = [c for c in rep.checks if "coverage" in c.label]
        assert bad and bad[0].verdict == "NOT-REPRODUCIBLE"

    def test_drifted_headline_fails_rerun(self, bundle: Path) -> None:
        # tamper a published headline WITHOUT touching the manifest
        # hash? no — that would fail the hash first. The honest probe:
        # rebuild the manifest over tampered bounds (a publisher who
        # self-certifies wrong numbers) — the re-run must catch it.
        b = json.loads((bundle / "adversarial-bounds.json").read_text())
        b[0]["bounds"][0]["headline"] = 999.0
        (bundle / "adversarial-bounds.json").write_text(
            json.dumps(b), encoding="utf-8")
        # re-manifest honestly (publisher re-ran manifest step)
        files = [f.name for f in bundle.iterdir()
                 if f.name != "MANIFEST.json"]
        (bundle / "MANIFEST.json").write_text(json.dumps({
            "candidate_id": "cand-ver",
            "files": {f: {"sha256": _sha(bundle / f),
                          "bytes": (bundle / f).stat().st_size}
                      for f in files},
        }), encoding="utf-8")
        rep = Report()
        v = V
        mm = v._verify_model(bundle, rep)
        assert mm is not None
        pub = v._verify_bounds(bundle, mm, rep)
        v._rerun_attack_battery(mm, pub, rep)
        assert not rep.ok
        # the tampered row is flagged — as a headline drift when the
        # published value is a number, or as a vacuous disagreement
        # when the re-run is honestly vacuous; either vocabulary is
        # the catch, never silence
        flagged = [c for c in rep.checks
                   if c.label.startswith("re-run ")
                   and c.verdict == "NOT-REPRODUCIBLE"]
        assert flagged, "re-run must flag the tampered headline"

    def test_report_lands_beside_bundle(self, bundle: Path) -> None:
        # main() writes the report to bundle.parent — the manifest's
        # complete-coverage invariant must survive verification
        v = V
        import sys as _sys
        old_argv = _sys.argv[:]
        _sys.argv = ["r25_verify_bundle.py", str(bundle)]
        try:
            v.main()
        except SystemExit as e:
            assert e.code in (0, 1)
        finally:
            _sys.argv = old_argv
        assert (bundle.parent / f"{bundle.name}-VERIFICATION.md").exists()
        assert not (bundle / "VERIFICATION.md").exists()





def _load_verifier():
    """Import the verifier by path — it is a standalone script a third
    party runs directly against a bundle, not an installed module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r25_verify_bundle",
        Path(__file__).parent.parent / "scripts" / "r25_verify_bundle.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    import sys
    sys.modules[spec.name] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


V = _load_verifier()
Report = V.Report
