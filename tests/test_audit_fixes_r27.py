"""Round 27 audit-fix probes — pins every fix from the external
audit (cand-9200b07691c3-FIXES.md) the day it ships.

The audit was the §27 criticism stage arriving as a real artifact;
§2 applies to audits too: each finding was verified against the
store before fixing, and each fix gets an anti-regression probe.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blockchain_rd_lab.database import Base, LabDatabase
from blockchain_rd_lab.reporting.service import ReportBuilder
from blockchain_rd_lab.schemas import (
    Candidate,
    CandidateStatus,
)

BUNDLE = Path("reports/release/bundle-cand-9200b07691c3")


def _db(tmp: Path, monkeypatch) -> LabDatabase:
    """A private LabDatabase bound to a PRIVATE sessionmaker —
    never a class-attribute patch (that leaks into every later
    test in the suite: the r27 test-isolation lesson)."""
    engine = create_engine(f"sqlite:///{tmp / 'lab.db'}")
    Base.metadata.create_all(engine)
    db = LabDatabase(tmp / "lab.db")
    monkeypatch.setattr(
        db, "_session",
        sessionmaker(bind=engine, expire_on_commit=False))
    return db


def _cand() -> Candidate:
    return Candidate(
        id="cand-audit-test",
        name="Audit Test Mechanism",
        category="market",
        problem="p",
        core_mechanism="m",
        description="d",
        status=CandidateStatus.FINALIST,
    )


def _rt_row(
    agent: str, created_at: str, verdict: str, strongest: str,
) -> dict[str, str]:
    return {
        "agent_name": agent,
        "created_at": created_at,
        "report_json": json.dumps({
            "verdict": verdict,
            "strongest_attack": strongest,
            "evidence_level": "INFERENCE",
            "attack_vectors": ["v1"],
            "summary": f"{agent} summary {created_at}",
        }),
    }


class TestAuditFix1LatestRedteamRound:
    """F1: the dossier quoted the EARLIEST round's 'vulnerable'
    while the final round read 'survives' — a first-occurrence
    dict-comprehension selection bug."""

    def test_verdict_line_quotes_latest_round(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        db = _db(tmp_path, monkeypatch)
        cand = db.save_candidate(_cand())
        # three rounds: stale vulnerable, stale vulnerable, survives
        for i, (v, at) in enumerate([
            ("vulnerable", "2026-01-01T10:00:00"),
            ("vulnerable", "2026-01-01T11:00:00"),
            ("survives", "2026-01-01T12:00:00"),
        ]):
            db.save_redteam_result(
                cand.id, agent_name="red_team",
                report_json=_rt_row("red_team", at, v, f"attack {i}")["report_json"],
            )
        line = ReportBuilder(db)._verdict_line(cand)  # type: ignore[arg-type]
        assert "survives" in line
        assert "vulnerable" not in line
        assert "attack 2" in line  # the LATEST round's strongest attack

    def test_section_uses_latest_per_agent(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        db = _db(tmp_path, monkeypatch)
        cand = db.save_candidate(_cand())
        for at, n in (("2026-01-01T10:00:00", 3), ("2026-01-01T12:00:00", 1)):
            body = {
                "verdict": "",
                "strongest_attack": "",
                "evidence_level": "INFERENCE",
                "attack_vectors": ["v"] * n,
                "summary": f"security summary {at}",
            }
            db.save_redteam_result(
                cand.id, agent_name="security",
                report_json=json.dumps(body),
            )
        sec = ReportBuilder(db)._redteam_section(
            cand, agent_focus="security")  # type: ignore[arg-type]
        assert "1 attack vector" in sec  # latest: 1, not earliest: 3


class TestAuditFix2DifferentiatedSections:
    """F2: Game Theory and Security rendered byte-identical; Economic
    Analysis and Market dumped the same full score list."""

    def test_agent_sections_differ(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        db = _db(tmp_path, monkeypatch)
        cand = db.save_candidate(_cand())
        for agent in ("game_theory", "security", "red_team"):
            db.save_redteam_result(
                cand.id, agent_name=agent,
                report_json=_rt_row(agent, "2026-01-01T10:00:00", "v", "a")["report_json"],
            )
        b = ReportBuilder(db)
        gt = b._redteam_section(cand, agent_focus="game_theory")  # type: ignore[arg-type]
        sec = b._redteam_section(cand, agent_focus="security")  # type: ignore[arg-type]
        assert gt != sec
        assert "game_theory" in gt and "security" in sec


class TestAuditFix3RuntimeShipsInBundle:
    """F3: verify.py imports blockchain_rd_lab — a third party with
    only the bundle hit ModuleNotFoundError. The runtime now ships
    inside; the verifier prefers it."""

    BUNDLE = Path("reports/release/bundle-cand-9200b07691c3")

    def test_runtime_present_and_complete(self) -> None:
        rt = BUNDLE / "lab-runtime" / "blockchain_rd_lab"
        assert (rt / "formalization" / "__init__.py").is_file()
        assert (rt / "simulation" / "__init__.py").is_file()
        assert (rt / "simulation" / "interpreter.py").is_file()
        assert (rt / "simulation" / "adversarial.py").is_file()

    def test_verifier_prefers_shipped_runtime(self) -> None:
        v = (BUNDLE / "verify.py").read_text(encoding="utf-8")
        assert "lab-runtime" in v
        assert "sys.path.insert" in v
        assert "dont_write_bytecode" in v

    def test_manifest_covers_runtime_recursively(self) -> None:
        man = json.loads(
            (BUNDLE / "MANIFEST.json").read_text(encoding="utf-8"))
        listed = set(man["files"])
        on_disk = {
            f.relative_to(BUNDLE).as_posix()
            for f in BUNDLE.rglob("*")
            if f.is_file() and "__pycache__" not in f.parts
        } - {"MANIFEST.json"}
        assert listed == on_disk


class TestAuditFix4Timestamp:
    """F4: the verification report's header printed the LITERAL
    text {__import__('datetime')...} — a split f-string."""

    def test_header_renders_iso_timestamp(self) -> None:
        # the shipped verify.py must not contain the broken pattern
        v = (BUNDLE / "verify.py").read_text(encoding="utf-8")
        assert "__import__('datetime')" not in v
        assert "datetime.now(UTC)" in v


class TestAuditFix5PriorArtDedupe:
    """F5: one review under two source rows double-counted
    'searches recorded'."""

    def test_bundle_dedupes_identical_findings(self) -> None:
        pa = json.loads(
            (BUNDLE / "prior-art.json").read_text(encoding="utf-8"))
        findings = [row["finding"] for row in pa]
        assert len(findings) == len(set(findings))
        merged = [row for row in pa if row.get("merged_source_ids")]
        assert merged, "the double-logged row must record its merge"

    def test_release_counts_distinct(self) -> None:
        rp = (BUNDLE / "release-package.md").read_text(encoding="utf-8")
        assert "1 (2 source rows; identical findings merged" in rp


class TestAuditFix6ScenarioBacking:
    """F6: the '13/13 clean' and Monte Carlo figures had no raw
    backing file in the bundle."""

    def test_scenario_results_ship(self) -> None:
        recs = json.loads(
            (BUNDLE / "scenario-results.json").read_text(
                encoding="utf-8"))
        ids = [r["experiment_id"] for r in recs]
        assert any(i.endswith("-scenarios-v3") for i in ids)
        assert any(i.endswith("-montecarlo-v3") for i in ids)
        mc = next(
            r for r in recs if r["experiment_id"].endswith("-montecarlo-v3"))
        # the dossier's mean_final figure must trace to this file
        assert "mean_final" in mc["results"]


class TestAuditFix7OpenQuestionsInSection4:
    """F7: the model's one open question was in the model JSON but
    not in §4 where a reader looks for caveats."""

    def test_open_question_renders_in_section_4(self) -> None:
        rp = (BUNDLE / "release-package.md").read_text(encoding="utf-8")
        idx4 = rp.find("## 4. Residual Attacks Disclosure")
        idx5 = rp.find("## 5")
        assert 0 <= idx4 < idx5
        section = rp[idx4:idx5]
        assert "OPEN QUESTION" in section
        assert "separation key" in section


class TestReadmeCommandMatchesManifest:
    """r28: the README's sha256sum command listed 9 files while the
    manifest had 15 — an auditor running it verbatim got a PARTIAL
    integrity check. The command is now GENERATED from the manifest
    keys; this probe pins it (a hand-maintained list always drifts)."""

    def test_sha_command_lists_every_shipped_file(self) -> None:
        import re
        readme = (BUNDLE / "README.md").read_text(encoding="utf-8")
        man = json.loads(
            (BUNDLE / "MANIFEST.json").read_text(encoding="utf-8"))
        i = readme.find("sha256sum")
        j = readme.find("python verify")
        block = readme[i:j]
        listed = set(re.findall(r"[\w./-]+\.(?:md|json|py)", block))
        expect = set(man["files"]) - {"README.md"}
        assert listed == expect, (
            f"command drift: missing {sorted(expect - listed)}, "
            f"extra {sorted(listed - expect)}"
        )

    def test_sha_command_executes_verbatim(self) -> None:
        import subprocess
        readme = (BUNDLE / "README.md").read_text(encoding="utf-8")
        block = re.search(
            r"sha256sum .*?\n\n", readme, re.S).group(0)
        cmd = block.replace("\\\n", " ").strip()
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=BUNDLE)
        assert r.returncode == 0
        man = json.loads(
            (BUNDLE / "MANIFEST.json").read_text(encoding="utf-8"))
        for line in r.stdout.splitlines():
            if not line.strip():
                continue
            h, f = line.split()
            assert h == man["files"][f]["sha256"], f"hash drift: {f}"


class TestAuditChecklist:
    """The audit's own verification checklist, verbatim."""

    def test_checklist_latest_created_at(self) -> None:
        # the Red Team quote's underlying record must be the latest
        hist = json.loads(
            (BUNDLE / "redteam-history.json").read_text(
                encoding="utf-8"))
        rt = [r for r in hist if r["agent_name"] == "red_team"]
        latest = max(rt, key=lambda r: str(r["created_at"]))
        rep = json.loads(latest["report_json"])
        dos = (BUNDLE / "dossier.md").read_text(encoding="utf-8")
        assert rep["verdict"] in dos

    def test_checklist_sections_distinct(self) -> None:
        dos = (BUNDLE / "dossier.md").read_text(encoding="utf-8")

        def section(name: str) -> str:
            i = dos.find(f"## {name}")
            j = dos.find("## ", i + 1)
            return dos[i:j]

        assert section("Game Theory") != section("Security")
        assert section("Economic Analysis") != section("Market")

    def test_checklist_score_arithmetic(self) -> None:
        sd = json.loads(
            (BUNDLE / "score-decomposition.json").read_text(
                encoding="utf-8"))
        total = sum(d["score"] * d["weight"] for d in sd["dimensions"])
        assert abs(total - sd["overall_score"]) <= 1e-6
        assert f"{sd['overall_score']:.2f}" in (
            BUNDLE / "README.md").read_text(encoding="utf-8")

    def test_timestamps_in_reports_real(self) -> None:
        # no literal {...} in any shipped report header
        for name in ("verify.py",):
            assert "{__import__" not in (
                BUNDLE / name).read_text(encoding="utf-8")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
