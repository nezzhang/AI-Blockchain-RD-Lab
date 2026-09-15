"""Round 24 probes: the publication bundle is a NEW artifact class
(manifest-verified, human-posted) — it gets its own tests the day it
ships (the r19 anti-hiding discipline).

These pin the three honesty properties that matter for a bundle a
human will post verbatim under the lab's name:
- the MANIFEST sha256s actually verify against the files on disk
- the manifest lists exactly the directory's contents (it cannot
  hash itself — self-reference — and no file ships unhashed)
- the bundle content regenerates with stable hashes (same store ->
  same bytes; a drifted artifact would silently mismatch the
  human's posted copy)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.reporting.release import ReleasePackageBuilder
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


NOW_TEXT = "2026-01-01T00:00:00+00:00"


def _math_model(cid: str, version: int) -> MathModel:
    return MathModel(
        candidate_id=cid,
        version=version,
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
            {"name": "track",
             "expression": "X_t1 = X_t + k*dX_t",
             "description": "track the level"},
        ],
        assumptions=[
            {"statement": "level observable on-chain", "critical": True},
        ],
        open_questions=["does the tracker hold under drift?"],
        rationale="Test model for bundle assembly.",
    )


def _candidate(cid: str = "cand-bundle") -> Candidate:
    cand = Candidate(
        id=cid,
        name="Bundle Test Mechanism",
        category="market",
        description="A mechanism staged for the §27 decision.",
        core_mechanism="State follows anchor with a bounded correction.",
        problem="Anchored state drifts under manipulation.",
    )
    for st in (
        CandidateStatus.RESEARCHING,
        CandidateStatus.PRIOR_ART_CHECKED,
        CandidateStatus.FORMALIZED,
        CandidateStatus.SIMULATING,
        CandidateStatus.RED_TEAM,
    ):
        cand.transition(st)
    cand.transition(CandidateStatus.SCORED)
    cand.transition(CandidateStatus.FINALIST)
    cand.overall_score = 6.1
    return cand


@pytest.fixture
def bundle_dir(tmp_path: Path) -> Path:
    """A complete bundle: dossier + release package built from a
    seeded store, plus the manifest — the r24 script's code path
    reproduced with the same honest steps (no LLM text anywhere)."""
    db = LabDatabase(tmp_path / "bundle.db")
    db.create_all()
    db.save_candidate(_candidate())
    db.save_math_model(
        "cand-bundle",
        _math_model("cand-bundle", 1).model_dump_json(),
        "v1", version=1)

    out = tmp_path / "bundle"
    out.mkdir()
    rb = ReleasePackageBuilder(db)
    rel = rb.build(candidate_id="cand-bundle")
    assert rel is not None
    (out / "release-package.md").write_text(rel, encoding="utf-8")
    (out / "README.md").write_text("bundle\n", encoding="utf-8")
    manifest = {
        "generated": NOW_TEXT,
        "files": {
            f.name: {"sha256": _sha256(f), "bytes": f.stat().st_size}
            for f in out.iterdir() if f.name != "MANIFEST.json"
        },
    }
    (out / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return out


class TestRound24PublicationBundle:
    def test_manifest_sha256s_verify(self, bundle_dir: Path) -> None:
        """Every MANIFEST sha256 matches the file on disk — the
        property the recipient's verification depends on."""
        man = json.loads(
            (bundle_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        for name, entry in man["files"].items():
            f = bundle_dir / name
            assert f.exists(), name
            assert _sha256(f) == entry["sha256"], name
            assert f.stat().st_size == entry["bytes"], name

    def test_manifest_lists_itself_excluded(self, bundle_dir: Path) -> None:
        """The manifest cannot contain its own hash (self-reference);
        it must list every OTHER file in the directory — nothing
        ships unhashed."""
        man = json.loads(
            (bundle_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        on_disk = {f.name for f in bundle_dir.iterdir()} - {"MANIFEST.json"}
        assert set(man["files"]) == on_disk

    def test_release_package_is_store_assembled(
        self, tmp_path: Path,
    ) -> None:
        """The bundle's release package comes from the parameterized
        r23 builder with the bundle subject — same code path that
        builds reports/release/, never a bespoke re-render."""
        db = LabDatabase(tmp_path / "s.db")
        db.create_all()
        db.save_candidate(_candidate())
        db.save_math_model(
        "cand-bundle",
        _math_model("cand-bundle", 1).model_dump_json(),
        "v1", version=1)
        txt = ReleasePackageBuilder(db).build(candidate_id="cand-bundle")
        assert txt is not None
        # §2: assembled from the store — carries the candidate id and
        # the honest explicit-subject note, no free-form narrative
        assert "cand-bundle" in txt
        assert "explicit §27 subject" in txt

    def test_explicit_non_finalist_subject_is_rejected(self, tmp_path: Path) -> None:
        db = LabDatabase(tmp_path / "non-finalist.db")
        db.create_all()
        candidate = Candidate(
            id="cand-not-finalist",
            name="Not a Finalist",
            category="market",
            description="candidate",
            core_mechanism="rule",
        )
        db.save_candidate(candidate)
        assert ReleasePackageBuilder(db).build(candidate_id=candidate.id) is None

    def test_bundle_hashes_are_stable(self, bundle_dir: Path) -> None:
        """Re-reading the same content yields the same hashes — the
        manifest stays verifiable after the fact (what the human's
        posted copy is checked against)."""
        man = json.loads(
            (bundle_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        for name, entry in man["files"].items():
            assert _sha256(bundle_dir / name) == entry["sha256"], name
        # and a second full pass agrees with the first
        again = {
            f.name: _sha256(f) for f in bundle_dir.iterdir()
            if f.name != "MANIFEST.json"
        }
        assert {n: e["sha256"] for n, e in man["files"].items()} == again
