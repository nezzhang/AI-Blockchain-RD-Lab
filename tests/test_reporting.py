"""Phase 7 reporting tests: dossiers, lab report, recommendation, CLI.

Reports are assembled by code from stored evidence (§2, §23); tests
verify section coverage, honest missing-evidence notes, deterministic
recommendation, and the §12 forbidden-claim discipline.
"""

from __future__ import annotations

import json

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.ranking.service import RankingService
from blockchain_rd_lab.reporting import (
    CandidateDossier,
    LabReport,
    ReportSection,
)
from blockchain_rd_lab.reporting.service import SECTIONS, ReportBuilder
from blockchain_rd_lab.schemas import (
    Candidate,
    CandidateStatus,
    FatalFlaw,
    ScoreBreakdown,
)


def make_candidate(name: str, scores: dict[str, float] | None = None, **overrides) -> Candidate:
    base = dict(
        name=name,
        category="monetary",
        description="Supply adjusts to a verified external anchor index.",
        core_mechanism="S_t1 = S_t * (1 + clip(alpha * dX_t / X_t, f, c)).",
        problem="Units drift from real productivity.",
        oracle_required=True,
    )
    base.update(overrides)
    cand = Candidate(**base)
    for dim, score in (scores or {}).items():
        cand.scores[dim] = ScoreBreakdown(dimension=dim, score=score)
    return cand


def advance(db: LabDatabase, cand: Candidate, to: CandidateStatus) -> Candidate:
    path = {
        CandidateStatus.RESEARCHING: [CandidateStatus.RESEARCHING],
        CandidateStatus.PRIOR_ART_CHECKED: [
            CandidateStatus.RESEARCHING,
            CandidateStatus.PRIOR_ART_CHECKED,
        ],
        CandidateStatus.FORMALIZED: [
            CandidateStatus.RESEARCHING,
            CandidateStatus.PRIOR_ART_CHECKED,
            CandidateStatus.FORMALIZED,
        ],
        CandidateStatus.SIMULATING: [
            CandidateStatus.RESEARCHING,
            CandidateStatus.PRIOR_ART_CHECKED,
            CandidateStatus.FORMALIZED,
            CandidateStatus.SIMULATING,
        ],
        CandidateStatus.RED_TEAM: [
            CandidateStatus.RESEARCHING,
            CandidateStatus.PRIOR_ART_CHECKED,
            CandidateStatus.FORMALIZED,
            CandidateStatus.SIMULATING,
            CandidateStatus.RED_TEAM,
        ],
    }
    for target in path[to]:
        cand.transition(target)
    db.save_candidate(cand)
    return cand


def make_finalist(db: LabDatabase, name: str, score: float) -> Candidate:
    cand = make_candidate(name, scores={"novelty": score})
    db.save_candidate(cand)
    advance(db, cand, CandidateStatus.RED_TEAM)
    RankingService(db).score_candidate(cand)
    return db.get_candidate(cand.id)


# ---------------------------------------------------------------------------
# Schemas / rendering
# ---------------------------------------------------------------------------


class TestRendering:
    def test_sections_match_spec(self):
        # §23 requires exactly these sections, in order.
        assert SECTIONS[0] == "Executive Summary"
        assert SECTIONS[-1] == "Recommendation"
        assert len(SECTIONS) == 19
        assert "Mathematical Model" in SECTIONS
        assert "Regulatory Risks" in SECTIONS
        assert "Open Questions" in SECTIONS

    def test_dossier_markdown_renders_all_sections(self):
        dossier = CandidateDossier(
            candidate_id="cand-x",
            name="Test Mechanism",
            category="monetary",
            status="finalist",
            overall_score=6.25,
            rank=1,
            recommended=True,
            sections=[ReportSection(title=t, body=f"body of {t}") for t in SECTIONS],
        )
        md = dossier.to_markdown()
        assert md.startswith("# Research Dossier: Test Mechanism")
        for t in SECTIONS:
            assert f"## {t}" in md
        assert "**Overall score:** 6.2500" in md
        assert "**Rank:** 1 (recommended)" in md

    def test_missing_evidence_renders_honestly(self):
        dossier = CandidateDossier(
            candidate_id="cand-x",
            name="Empty",
            category="monetary",
            status="generated",
            sections=[ReportSection(title="Problem", body="")],
        )
        md = dossier.to_markdown()
        assert "_(no recorded evidence yet)_" in md

    def test_lab_report_markdown(self):
        lab = LabReport(
            generated_at="2025-01-01T00:00:00+00:00",
            candidates_total=3,
            status_counts={"finalist": 1, "scored": 2},
            finalists=["cand-a"],
            recommended_id="cand-a",
            ranking_table=[(1, "cand-a", "Alpha", 6.0)],
        )
        md = lab.to_markdown()
        assert "# Lab Research Report" in md
        assert "**finalist:** 1" in md
        assert "cand-a" in md
        assert "| 1 | cand-a | Alpha | 6.0000 |" in md


# ---------------------------------------------------------------------------
# Dossier builder
# ---------------------------------------------------------------------------


class TestDossier:
    def test_dossier_from_full_evidence(self, memory_db):
        from blockchain_rd_lab.formalization import model_from_dict
        from blockchain_rd_lab.formalization.agents import build_math_model_fixture
        from blockchain_rd_lab.research import CandidateBrief

        cand = make_finalist(memory_db, "Full Evidence", 7.0)
        brief = CandidateBrief.from_candidate(cand)
        model = model_from_dict(build_math_model_fixture(brief))
        memory_db.save_math_model(
            cand.id, json.dumps(model.model_dump(mode="json")), "fixture", version=1
        )

        builder = ReportBuilder(memory_db)
        dossier = builder.build_dossier(cand, rank=1, recommended=True)

        md = dossier.to_markdown()
        # Math model rendered
        assert "`g_t = clip(g_raw_t, f, c)`" in md
        assert "coupling ∈ [0.0, 2.0]" in md
        assert "Open questions (§13)" in md
        # Scores rendered with evidence discipline
        assert "**novelty**: 7.00" in md
        # §12 forbidden claim never appears
        assert "Nobody has ever" not in md
        # Recommendation
        assert "Recommended candidate (§7)" in md
        # §23 order preserved
        titles = [s.title for s in dossier.sections]
        assert titles == list(SECTIONS)

    def test_dossier_missing_evidence_sections(self, memory_db):
        cand = make_candidate("Sparse")
        memory_db.save_candidate(cand)

        builder = ReportBuilder(memory_db)
        dossier = builder.build_dossier(cand)
        md = dossier.to_markdown()
        assert "No formal model stored yet" in md
        assert "No simulation runs recorded yet" in md
        assert "No adversarial review recorded yet" in md
        assert "No prior-art research recorded yet" in md

    def test_fatal_flaws_render_in_risks(self, memory_db):
        cand = make_candidate("Flawed", scores={"novelty": 5.0})
        cand.fatal_flaws.append(
            FatalFlaw(
                flaw_id="ff-t",
                category="security",
                description="oracle capture is structural",
                confirmed=True,
                identified_by="red_team",
            )
        )
        memory_db.save_candidate(cand)
        advance(memory_db, cand, CandidateStatus.RED_TEAM)

        builder = ReportBuilder(memory_db)
        dossier = builder.build_dossier(cand)
        md = dossier.to_markdown()
        assert "oracle capture is structural" in md
        assert "**Confirmed fatal flaws:** 1" in md

    def test_simulation_section_lists_experiments(self, memory_db):
        from blockchain_rd_lab.schemas import ExperimentRecord, utcnow

        cand = make_candidate("Simmed", scores={"novelty": 6.0})
        memory_db.save_candidate(cand)
        memory_db.save_experiment(
            ExperimentRecord(
                experiment_id=f"{cand.id}-scenarios",
                candidate_id=cand.id,
                timestamp=utcnow(),
                git_commit="abc123",
                parameters={"steps": 60},
                dataset="synthetic-anchor-v1",
                model="mathmodel-latest",
                seed=7,
                simulation_version="sim-0.1.0",
                results={"failures": 0},
            )
        )

        builder = ReportBuilder(memory_db)
        md = builder.build_dossier(cand).to_markdown()
        assert f"{cand.id}-scenarios" in md
        assert "seed 7" in md
        assert "reproducible" in md


# ---------------------------------------------------------------------------
# Lab report + §7 recommendation
# ---------------------------------------------------------------------------


class TestLabReport:
    def test_recommendation_is_rank_one_finalist(self, memory_db):
        f1 = make_finalist(memory_db, "Alpha Finalist", 7.0)
        f2 = make_finalist(memory_db, "Beta Finalist", 8.0)
        RankingService(memory_db).select_finalists(count=5)

        lab = ReportBuilder(memory_db).build_lab_report()
        # Highest score is Beta (8.0) — deterministic pick.
        assert lab.recommended_id == f2.id
        assert set(lab.finalists) == {f1.id, f2.id}

    def test_recommendation_deterministic_across_runs(self, memory_db):
        make_finalist(memory_db, "Alpha Finalist", 7.0)
        make_finalist(memory_db, "Beta Finalist", 8.0)
        RankingService(memory_db).select_finalists(count=5)
        b = ReportBuilder(memory_db)
        assert b.build_lab_report().recommended_id == b.build_lab_report().recommended_id

    def test_lab_report_counts(self, memory_db):
        make_finalist(memory_db, "Alpha Finalist", 7.0)
        rejected = make_candidate("Reject Me", scores={"novelty": 5.0})
        rejected.fatal_flaws.append(
            FatalFlaw(
                flaw_id="ff-r",
                category="economic",
                description="death spiral",
                confirmed=True,
                identified_by="economist",
            )
        )
        memory_db.save_candidate(rejected)
        advance(memory_db, rejected, CandidateStatus.RED_TEAM)
        RankingService(memory_db).score_candidate(rejected)  # → REJECTED

        lab = ReportBuilder(memory_db).build_lab_report()
        assert lab.candidates_total == 2
        assert lab.status_counts.get("rejected") == 1
        assert lab.gate_rejections == 1


# ---------------------------------------------------------------------------
# write_reports artifacts
# ---------------------------------------------------------------------------


class TestWriteReports:
    def test_writes_dossiers_and_lab_report(self, memory_db, tmp_path):
        make_finalist(memory_db, "Alpha Finalist", 7.0)
        make_finalist(memory_db, "Beta Finalist", 8.0)
        RankingService(memory_db).select_finalists(count=5)

        builder = ReportBuilder(memory_db)
        outcome = builder.write_reports(tmp_path)

        assert len(outcome.dossiers_written) == 2
        for path in outcome.dossiers_written:
            with open(path) as fh:
                content = fh.read()
            assert content.startswith("# Research Dossier:")
        assert outcome.lab_report_path is not None
        with open(outcome.lab_report_path) as fh:
            lab_md = fh.read()
        assert "# Lab Research Report" in lab_md
        assert outcome.recommended_id is not None

    def test_no_dossiers_flag(self, memory_db, tmp_path):
        make_finalist(memory_db, "Alpha Finalist", 7.0)
        outcome = ReportBuilder(memory_db).write_reports(
            tmp_path, include_dossiers=False
        )
        assert outcome.dossiers_written == []
        assert outcome.lab_report_path is not None

    def test_report_is_reproducible(self, memory_db, tmp_path):
        make_finalist(memory_db, "Alpha Finalist", 7.0)
        RankingService(memory_db).select_finalists(count=5)  # promote to FINALIST
        b = ReportBuilder(memory_db)
        out1 = b.write_reports(tmp_path / "a")
        out2 = b.write_reports(tmp_path / "b")
        assert out1.dossiers_written and out2.dossiers_written
        with open(out1.dossiers_written[0]) as fh:
            md1 = fh.read()
        with open(out2.dossiers_written[0]) as fh:
            md2 = fh.read()
        # Same DB state -> identical dossier bytes (deterministic §2).
        assert md1 == md2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestReportCommand:
    def test_single_candidate_dossier(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        cand = make_candidate("Solo Report")
        db.save_candidate(cand)

        runner = CliRunner()
        result = runner.invoke(app, ["report", cand.id])
        assert result.exit_code == 0
        assert "Research Dossier" in result.output
        assert "Solo Report" in result.output

    def test_unknown_candidate(self, tmp_lab_dir):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["report", "cand-nope"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_batch_writes_artifacts(self, tmp_lab_dir, monkeypatch):
        from typer.testing import CliRunner

        from blockchain_rd_lab.cli import app
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase
        from blockchain_rd_lab.schemas import CandidateStatus

        # Keep report artifacts out of the real reports/ tree.
        monkeypatch.setattr("blockchain_rd_lab.cli.REPO_ROOT", tmp_lab_dir)

        cfg = load_config()
        db = LabDatabase(REPO_ROOT / cfg.storage.database)
        db.create_all()
        cand = make_candidate("Final Report", scores={"novelty": 7.0})
        db.save_candidate(cand)
        advance(db, cand, CandidateStatus.RED_TEAM)
        RankingService(db).score_candidate(cand)
        RankingService(db).select_finalists(count=5)

        runner = CliRunner()
        result = runner.invoke(app, ["report"])
        assert result.exit_code == 0
        assert "Reports written" in result.output
        assert "Recommended candidate" in result.output

        reports_dir = tmp_lab_dir / "reports"
        assert (reports_dir / "lab-latest.md").exists()
        assert (reports_dir / "finalists" / f"{cand.id}.md").exists()
