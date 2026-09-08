"""§27 release package: staged from stored evidence, honest by construction.

The release package is the §27 human-decision document: it assembles the
recommended candidate's evidence trail from the database ONLY (§2 — no
report-writer LLM), and its §4 residual disclosure applies TWO-LAYER
honesty:

  - layer 1 (the fix claim): §33 ADDRESSES edges record what each model
    version CLAIMS to address — a claim, not a proof;
  - layer 2 (the re-attack judgment): red-team reports created AFTER the
    final model version was stored saw the patched parameters in their
    prompts (§34 model-wired retest) — their profitable vectors are
    STILL-PROFITABLE residuals even when a fix claims them.

A residual with no covering claim is OPEN. Only claimed-closed residuals
(from older attacks, never re-found) stay off the disclosure page — they
live in the dossier. These tests build the full mini-evidence chain and
assert every layer.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.reporting.release import ReleasePackageBuilder
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

NOW = datetime.now(UTC)


def _candidate(cid: str = "cand-rel") -> Candidate:
    cand = Candidate(
        id=cid,
        name="Release Package Test Mechanism",
        category="stablecoins",
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
    # finalize via score path (RED_TEAM -> SCORED -> FINALIST)
    cand.transition(CandidateStatus.SCORED)
    cand.transition(CandidateStatus.FINALIST)
    cand.overall_score = 6.0
    return cand


def _model(cid: str, version: int) -> str:
    m = MathModel(
        candidate_id=cid,
        variables=[
            {"name": "S_t", "symbol": "S_t", "role": "state", "units": "u",
             "description": "supply"},
            {"name": "S_t1", "symbol": "S_t1", "role": "state", "units": "u",
             "description": "next supply"},
            {"name": "X_t", "symbol": "X_t", "role": "input", "units": "i",
             "description": "anchor"},
            {"name": "dX_t", "symbol": "dX_t", "role": "input", "units": "i",
             "description": "anchor change"},
        ],
        parameters=[
            {"name": "alpha", "symbol": "alpha", "description": "coupling",
             "min_value": 0.0, "max_value": 1.0, "default": 0.5},
        ],
        equations=[
            {"name": "supply", "expression": "S_t1 = S_t * (1 + alpha * dX_t)",
             "description": "supply follows anchor"},
        ],
        assumptions=[{"statement": "observable anchor", "critical": False}],
        constraints=[],
        open_questions=["is alpha right?"],
        rationale="test model rationale",
        version=version,
    )
    return m.model_dump_json()


def _report(verdict: str, vectors: list[dict]) -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "strongest_attack": "The strongest attack against the design.",
            "strongest_attack_is_profitable": True,
            "attack_vectors": vectors,
            "what_would_save_it": "Structural fixes, honestly listed.",
            "evidence_level": "INFERENCE",
        }
    )


def _v1_attack() -> str:
    return _report(
        "vulnerable",
        [
            {
                "vector": "Anchor spike manipulation",
                "description": "A whale spikes the anchor to inflate supply.",
                "attacker": "whale",
                "profitable_for_attacker": True,
                "requires_collusion": False,
                "evidence_level": "INFERENCE",
            },
            {
                "vector": "Routine wash drain",
                "description": "Wash volume drains the routine layer unseen.",
                "attacker": "attacker",
                "profitable_for_attacker": True,
                "requires_collusion": False,
                "evidence_level": "HYPOTHESIS",
            },
        ],
    )


def _v2_reattack() -> str:
    return _report(
        "survives",
        [
            {
                # claimed by v2 AND re-found by the final-version red team
                "vector": "Residual anchor leak",
                "description": "The fix claims the anchor channel; the "
                "re-attack still finds a reduced leak profitable.",
                "attacker": "whale",
                "profitable_for_attacker": True,
                "requires_collusion": False,
                "evidence_level": "INFERENCE",
            },
            {
                # never claimed by v2 at all
                "vector": "Carry-floor free option",
                "description": "The floor grants free calm-period income.",
                "attacker": "liquidity_provider",
                "profitable_for_attacker": True,
                "requires_collusion": False,
                "evidence_level": "HYPOTHESIS",
            },
        ],
    )


def _seed(db: LabDatabase) -> None:
    cid = "cand-rel"
    cand = _candidate(cid)
    db.save_candidate(cand)
    # v1 model stored, then the v1 attack
    db.save_math_model(cid, _model(cid, 1), "v1", version=1)
    db.save_redteam_result(cid, "red_team", _v1_attack())
    # v2 stored (the fix, claiming both v1 attacks), then the re-attack
    db.save_math_model(cid, _model(cid, 2), "v2: netting fix", version=2)
    db.save_redteam_result(cid, "red_team", _v2_reattack())
    # §33 ADDRESSES edges: the graph reads improvement proposals from
    # agent runs; seed the claims directly via the improvement record the
    # graph builder consumes (agent run with ImprovementProposal payload).
    from blockchain_rd_lab.improvement import AddressedAttack, ImprovementProposal

    proposal = ImprovementProposal(
        candidate_id=cid,
        summary="v2: net the anchor channel and wash filter",
        addressed_attacks=[
            AddressedAttack(
                agent_name="red_team",
                vector_description="Anchor spike manipulation: A whale spikes "
                "the anchor to inflate supply.",
                fix_strategy="Net whale flow out of the anchor input.",
                fixes_attack=True,
            ),
            AddressedAttack(
                agent_name="red_team",
                vector_description="Routine wash drain: Wash volume drains "
                "the routine layer unseen.",
                fix_strategy="Wash-filtered draws index netted flow.",
                fixes_attack=True,
            ),
            AddressedAttack(
                agent_name="red_team",
                vector_description="Residual anchor leak: The fix claims the "
                "anchor channel; the re-attack still finds a reduced leak "
                "profitable.",
                fix_strategy="Netting at k_net=0.8 — reduced, not closed.",
                fixes_attack=True,
            ),
        ],
        model=json.loads(_model(cid, 2)),
    )
    from blockchain_rd_lab.schemas import AgentRunRecord

    db.save_agent_run(
        AgentRunRecord(
            agent_name="improver",
            candidate_id=cid,
            status="success",
            finished_at=datetime.now(UTC),
            output=proposal.model_dump(),
        )
    )


@pytest.fixture
def seeded_db(tmp_path: Path) -> LabDatabase:
    db = LabDatabase(tmp_path / "test-release.db")
    db.create_all()
    _seed(db)
    return db


class TestResidualDisclosure:
    def test_still_profitable_residual_disclosed(self, seeded_db):
        """Claimed by v2 AND re-found by the final-version red team →
        STILL-PROFITABLE: on the page."""
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "Residual anchor leak" in pkg
        assert "still-profitable" in pkg

    def test_open_residual_disclosed(self, seeded_db):
        """Never claimed by any fix → OPEN: on the page."""
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "Carry-floor free option" in pkg
        assert "open" in pkg

    def test_claimed_closed_residual_off_page(self, seeded_db):
        """v1 attacks claimed by v2 and never re-found stay in the dossier
        (the disclosure is for what SHIPS, not what was fixed)."""
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "Anchor spike manipulation" not in pkg.split("## 4.")[1].split("## 5.")[0]
        assert "Routine wash drain" not in pkg.split("## 4.")[1].split("## 5.")[0]

    def test_no_absolute_security_claims(self, seeded_db):
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "not an absolute claim" in pkg or "no absolute" in pkg.lower() or \
            "No profitable attack remains" in pkg


class TestPackageStructure:
    def test_sections_present(self, seeded_db):
        pkg = ReleasePackageBuilder(seeded_db).build()
        for section in (
            "## 1. Publication Readiness",
            "## 2. The Mechanism",
            "## 3. Evidence Trail",
            "## 4. Residual Attacks Disclosure",
            "## 5. Build-in-Public Progression",
        ):
            assert section in pkg, f"missing section: {section}"

    def test_progression_marks_human_decision(self, seeded_db):
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "HUMAN DECISION" in pkg
        assert "[x] Research" in pkg
        assert "[x] Simulation" in pkg

    def test_score_and_versions_recorded(self, seeded_db):
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "6.0" in pkg
        assert "[1, 2]" in pkg

    def test_no_finalist_returns_none(self, tmp_path: Path):
        db = LabDatabase(tmp_path / "empty.db")
        db.create_all()
        assert ReleasePackageBuilder(db).build() is None

    def test_write_creates_file(self, seeded_db, tmp_path: Path):
        out = tmp_path / "reports"
        path = ReleasePackageBuilder(seeded_db).write(out)
        assert path is not None and path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Release Package" in content

    def test_deterministic(self, seeded_db, tmp_path: Path):
        """Same DB state → byte-identical package (§2)."""
        a = ReleasePackageBuilder(seeded_db).build()
        b = ReleasePackageBuilder(seeded_db).build()
        assert a == b


def _bounds_record(
    *, regime_tracking: dict | None = None, heal_flags: dict | None = None,
    in_transit: dict | None = None,
) -> dict:
    """A §20 adversarial-patterns record shaped like the r13/r14 battery:
    crash_park with an EMA excursion reclassified as regime tracking and
    (optionally) heal flags on the keyed protection states."""
    from blockchain_rd_lab.schemas import ExperimentRecord

    return ExperimentRecord(
        candidate_id="cand-rel",
        timestamp=NOW,
        git_commit="test",
        parameters={"battery": "attack_patterns_v2_crash_park", "steps": 60},
        dataset="adversarial_patterns",
        model="mathmodel-v2",
        seed=None,
        simulation_version="test",
        results={
            "bounds": [
                {"kind": "wash_flow", "headline": 4.68, "headline_metric": "T_t_drawn",
                 "vacuous": False, "edge": {"T_t_drawn": 4.68}},
                {"kind": "crash_park", "headline": 0.0, "headline_metric": None,
                 "vacuous": False, "edge": {},
                 "regime_tracking": regime_tracking or {},
                 "heal_flags": heal_flags or {},
                 "in_transit": in_transit or {}},
            ],
            "vacuous_count": 0,
        },
    )


class TestBoundsDisclosureHonesty:
    """The r14 4b fix: an EMA-of-level excursion under crash_park is the
    design FOLLOWING the moved level (regime tracking), not an attacker
    edge — publishing it as 'measured attacker edge +600' would be a
    misleading disclosure (§12/§2). The heal_flags carry the real
    crash-park signal: which protection states heal, by how much."""

    def test_regime_tracking_not_published_as_attacker_edge(self, seeded_db):
        seeded_db.save_experiment(_bounds_record(
            regime_tracking={"L_t_drawn": 600.0, "U_s_drawn": 262.1},
        ))
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "REGIME TRACKING" in pkg, (
            "the reclassification must be disclosed, not silently dropped"
        )
        # the excursion appears as regime tracking, explicitly NOT extraction
        assert "not extraction" in pkg
        assert "`L_t` +600.0" in pkg and "`U_s` +262.1" in pkg

    def test_heal_disclosure_rendered(self, seeded_db):
        seeded_db.save_experiment(_bounds_record(
            heal_flags={"F_t": 0.93, "F_t1": 0.93, "L_t": 1.0},
        ))
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "heal disclosure" in pkg
        assert "`F_t` retains 93% of peak" in pkg, (
            "the heal ratio is the real crash-park signal (r13): "
            "protection persistence, measured and disclosed"
        )
        # next-state symbols (…1) are dropped from the prose
        assert "`F_t1`" not in pkg

    def test_in_transit_rebasing_rendered(self, seeded_db):
        """r19: a slow pool still re-basing at window end (confirmed
        arriving at the doubled window, or resting at its base-run
        offset from its design target) is disclosed as re-basing in
        transit — never published as an attacker edge, never silently
        dropped."""
        seeded_db.save_experiment(_bounds_record(
            in_transit={"Z_t_drawn": 485.3},
        ))
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "re-basing in transit" in pkg
        assert "`Z_t` re-basing (+485.3 in motion at window end)" in pkg

    def test_zero_edge_with_tracking_shows_context(self, seeded_db):
        """crash_park headline 0.0 + regime tracking = the honest pair:
        'no positive attacker edge' PLUS why (the excursions were
        reclassified)."""
        seeded_db.save_experiment(_bounds_record(
            regime_tracking={"L_t_drawn": 599.7, "T_t_drawn": 599.7},
        ))
        pkg = ReleasePackageBuilder(seeded_db).build()
        block = pkg.split("### 4b.")[1].split("## 5.")[0]
        assert "no positive attacker edge" in block
        assert "REGIME TRACKING" in block

    def test_no_record_still_renders_without_4b(self, seeded_db):
        """No adversarial record → no 4b section (absence is honest)."""
        pkg = ReleasePackageBuilder(seeded_db).build()
        assert "### 4b." not in pkg
class TestRound23PublicationOptions:
    """r23: the three §27 options, literally buildable. The release
    builder takes a candidate override (the incumbent path — the
    human decides, not the rank), and the decision brief lives in
    the reporting library (one source of truth, any pair)."""

    def test_explicit_candidate_override_builds_incumbent(
        self, seeded_db,
    ) -> None:
        # the incumbent option: any finalist must be a buildable §27
        # subject, and the package must SAY it was the human's
        # selection, not the ranking's
        cand = _candidate("cand-rel")  # the seeded finalist
        seeded_db.save_candidate(cand)
        txt = ReleasePackageBuilder(seeded_db).build(
            candidate_id="cand-rel")
        assert txt is not None
        assert "explicit §27 subject" in txt
        # and the default path still says §7 recommended
        txt2 = ReleasePackageBuilder(seeded_db).build()
        assert txt2 is not None
        assert "§7 recommended, rank 1" in txt2

    def test_write_custom_filename_and_candidate(
        self, seeded_db, tmp_path: Path,
    ) -> None:
        p = ReleasePackageBuilder(seeded_db).write(
            tmp_path, candidate_id="cand-rel",
            filename="release-package-incumbent.md")
        assert p is not None
        assert p.name == "release-package-incumbent.md"
        assert "explicit §27 subject" in p.read_text(encoding="utf-8")

    def test_decision_brief_any_pair_from_library(self, seeded_db):
        # the brief moved r21-script -> library: any candidate pair,
        # one source of truth; missing candidates raise, never
        # silently render a one-sided brief
        from blockchain_rd_lab.reporting.decision import (
            build_decision_brief,
        )
        cand = _candidate("cand-rel")
        cand2 = _candidate("cand-rel2")
        cand2.name = "Second Test Mechanism"
        seeded_db.save_candidate(cand)
        seeded_db.save_candidate(cand2)
        txt = build_decision_brief(
            seeded_db, candidate_ids=("cand-rel", "cand-rel2"))
        assert "cand-rel" in txt and "cand-rel2" in txt
        with pytest.raises(ValueError, match="cand-missing"):
            build_decision_brief(
                seeded_db,
                candidate_ids=("cand-rel", "cand-missing"))

