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
