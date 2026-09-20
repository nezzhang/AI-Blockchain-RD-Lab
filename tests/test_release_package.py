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
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.reporting.release import ReleasePackageBuilder
from blockchain_rd_lab.schemas import (
    Candidate,
    CandidateStatus,
    ExperimentRecord,
    ScoreBreakdown,
)

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
    # r48: overall_score is derived from dimension scores by save_candidate —
    # it cannot be set independently. Provide real dimension evidence so the
    # candidate carries a composite (11 dims at 6.0 -> overall 6.0).
    for dim in (
        "novelty", "economic_coherence", "game_theory", "technical_feasibility",
        "oracle_feasibility", "security", "market_demand", "capital_efficiency",
        "network_effects", "communication", "viral_potential",
    ):
        cand.scores[dim] = ScoreBreakdown(dimension=dim, score=6.0)
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

    @pytest.fixture
    def unprofitable_db(self, tmp_path: Path) -> LabDatabase:
        """The r36 suppression fixture: the final re-attack finds a
        vector the AGENT asserts unprofitable — the exact input the
        pre-r36 §4 filter dropped. The vector must still publish."""
        db = LabDatabase(tmp_path / "test-release-r36.db")
        db.create_all()
        _seed(db)
        # a THIRD report after v2: the re-attack that 'survives' but
        # still names a surface, asserting it does NOT pay.
        db.save_redteam_result(
            "cand-rel", "red_team",
            _report(
                "survives",
                [
                    {
                        "vector": "Quiet-window alternation partial ride",
                        "description": "Long-period saw-tooth rides the "
                        "counter's handoff window; bounded by band "
                        "half-width.",
                        "attacker": "attacker",
                        "profitable_for_attacker": False,
                        "requires_collusion": False,
                        "evidence_level": "INFERENCE",
                    },
                ],
            ),
        )
        return db

    def test_unprofitable_asserted_vector_is_disclosed(self, unprofitable_db):
        """r36 (the r35 principle at the disclosure surface): the
        agent's profitable_for_attacker boolean is metadata, never a
        filter — a vector asserted unprofitable still publishes in §4,
        flagged as unprofitable-asserted. Pre-r36 this exact input was
        invisible in the published package."""
        pkg = ReleasePackageBuilder(unprofitable_db).build()
        section4 = pkg.split("## 4.")[1].split("## 5.")[0]
        assert "Quiet-window alternation partial ride" in section4, (
            "an unprofitable-asserted vector must not be suppressed "
            "from the published §4 disclosure"
        )
        assert "unprofitable-asserted" in section4

    def test_profitable_hypothesis_flag_rendered(self, seeded_db):
        """The flag renders on EVERY line — the reader weighs the
        assertion, the code does not."""
        pkg = ReleasePackageBuilder(seeded_db).build()
        section4 = pkg.split("## 4.")[1].split("## 5.")[0]
        assert "profitable-hypothesis" in section4
        assert "profitability flag = the attacking agent's own" in section4

    def test_dedup_tie_keeps_profitable_reading(self, tmp_path: Path):
        """The r36 dedup tie-break: same surface, same status, one
        report asserts profitable and one denies — the MORE honest
        reading (profitable-asserted) stays on the page."""
        db = LabDatabase(tmp_path / "test-release-tie.db")
        db.create_all()
        _seed(db)
        vec = {
            "vector": "Anchor-camp premium pumping",
            "description": "Pump the anchor to inflate the premium.",
            "attacker": "whale",
            "requires_collusion": False,
            "evidence_level": "INFERENCE",
        }
        db.save_redteam_result(
            "cand-rel", "security",
            _report("vulnerable", [dict(vec, profitable_for_attacker=True)]),
        )
        db.save_redteam_result(
            "cand-rel", "game_theory",
            _report("vulnerable", [dict(vec, profitable_for_attacker=False)]),
        )
        pkg = ReleasePackageBuilder(db).build()
        section4 = pkg.split("## 4.")[1].split("## 5.")[0]
        assert "Anchor-camp premium pumping" in section4
        line = next(
            ln for ln in section4.splitlines()
            if "Anchor-camp premium pumping" in ln
        )
        assert "profitable-hypothesis" in line, (
            "on a status tie the profitable-asserted reading must win"
        )


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

    def test_deterministic_across_second_boundary(
        self, seeded_db, tmp_path: Path,
    ):
        """r37: the transient the suite caught live — two builds
        crossing a wall-clock second boundary rendered different
        'Generated:' stamps for the SAME store, violating the
        byte-determinism contract this class pins. The stamp is
        now the store's latest-evidence timestamp (release.py no
        longer imports the wall clock at all — the module is
        clock-free), so the boundary is structurally impossible.
        Assert both: the bytes are identical, and the stamp names
        a STORED timestamp (the latest red-team report the fixture
        seeds), not now().
        """
        import blockchain_rd_lab.reporting.release as rel
        a = ReleasePackageBuilder(seeded_db).build()
        time.sleep(1.1)  # cross the second boundary, structurally
        b = ReleasePackageBuilder(seeded_db).build()
        assert a is not None and b is not None
        assert a == b
        # clock-free module: no datetime import remains to drift
        assert not hasattr(rel, "datetime")
        # the stamp is store-derived: the fixture's latest stored
        # red-team created_at, second-resolution
        stamps = sorted(
            r["created_at"]
            for r in seeded_db.list_redteam_results(
                candidate_id="cand-rel")
            if r["created_at"]
        )
        expected = stamps[-1]
        assert expected is not None
        assert f"Generated: {expected}" in a


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


class TestRound2AuditCalibrationCompleteness:
    """r29 (round-2 audit F1): §4b rendered 17 of 19 calibration
    lines — the dedupe key was the CALIBRATION TAG ALONE, and
    vol_oscillation/pump_unwind both sweep amplitude=0.02/0.1, so
    the second pattern's variants were silently dropped. The key
    must be kind+calibration: the same calibration under two
    patterns is two different measurements.

    Also pins the misdiagnosis lesson: 'render from the fullest
    record' was WRONG — the renderer already used the 27-bound
    record; verify the root cause against the store before fixing
    (the auditor's own numbers 19-vs-17 localized it)."""

    def test_two_patterns_sharing_a_calibration_both_render(
        self, memory_db, tmp_path,
    ) -> None:
        # a sweep record where TWO kinds share calibration names
        bounds = []
        for kind in ("vol_oscillation", "pump_unwind"):
            for amp in ("0.02", "0.1"):
                bounds.append({
                    "kind": kind, "calibration": f"amplitude={amp}",
                    "headline": 0.5, "vacuous": False,
                    "regime_tracking": {}, "transient_recovered": {},
                    "drift_wedges": {}, "heal_flags": {},
                })
        from blockchain_rd_lab.schemas import ExperimentRecord
        memory_db.save_candidate(_candidate("cand-x"))
        memory_db.save_experiment(ExperimentRecord(
            experiment_id="exp-sweep", candidate_id="cand-x",
            dataset="attack_parameter_sweep", seed=7,
            simulation_version="sim-0.1.0", parameters={},
            results={"bounds": bounds, "vacuous_count": 0},
        ))
        builder = ReleasePackageBuilder(memory_db)
        md = builder.build(candidate_id="cand-x")
        assert md is not None
        i = md.find("## 4b")
        assert i >= 0, "no 4b section rendered"
        section = md[i:]
        import re as _re
        tagged = _re.findall(r"\*\*(\w+) @([^\n]*?)\*\*", section)
        assert len(tagged) == 4, f"expected 4 lines, got {len(tagged)}"
        kinds = [k for k, _ in tagged]
        assert kinds.count("vol_oscillation") == 2
        assert kinds.count("pump_unwind") == 2


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

    # -- r37: the §27 decision brief under the r36/r37 honesty rules --

    @pytest.fixture
    def brief_pair_db(self, tmp_path: Path) -> LabDatabase:
        """Two finalists with asymmetric residual profiles: head's only
        named surface is asserted UNPROFITABLE (the pre-r36 invisible
        class), tail carries one profitable-asserted surface. The
        pre-r37 brief would have said the head carries nothing and
        flattered it in §6."""
        db = LabDatabase(tmp_path / "test-brief-r37.db")
        db.create_all()
        _seed(db)
        cand2 = _candidate("cand-rel2")
        cand2.name = "Second Test Mechanism"
        db.save_candidate(cand2)
        # tail needs a stored model: a named vector with NO model would
        # suppress the surface entirely (the pre-r36 invisible class,
        # re-created by fixture sloppiness) — the brief must render the
        # vector, and only the §33 claim-match can sort it
        db.save_math_model("cand-rel2", _model("cand-rel2", 1), "v1", version=1)
        # head: re-attack names a surface, asserts it does not pay
        db.save_redteam_result(
            "cand-rel", "red_team",
            _report(
                "survives",
                [
                    {
                        "vector": "Quiet-window alternation partial ride",
                        "description": "Long-period saw-tooth rides the "
                        "counter's handoff window.",
                        "attacker": "attacker",
                        "profitable_for_attacker": False,
                        "requires_collusion": False,
                        "evidence_level": "INFERENCE",
                    },
                ],
            ),
        )
        # tail: a profitable-asserted vector of its own
        db.save_redteam_result(
            "cand-rel2", "red_team",
            _report(
                "survives",
                [
                    {
                        "vector": "Fee-cap exhaustion grind",
                        "description": "Sustained pressure drains the "
                        "fee pool.",
                        "attacker": "attacker",
                        "profitable_for_attacker": True,
                        "requires_collusion": False,
                        "evidence_level": "FACT",
                    },
                ],
            ),
        )
        return db

    def test_brief_publishes_unprofitable_asserted_surface(
        self, brief_pair_db,
    ):
        """r37 (the r36 principle at the DECISION surface): the §27
        brief's §4 lists every NAMED surface with the assertion flag —
        pre-r37 its header still framed the list as 'Profitable
        vectors' and the head's unprofitable-asserted surface was
        exactly the kind of input that flattered a candidate."""
        from blockchain_rd_lab.reporting.decision import (
            build_decision_brief,
        )
        txt = build_decision_brief(
            brief_pair_db, candidate_ids=("cand-rel", "cand-rel2"))
        assert "never a filter" in txt
        assert "Quiet-window alternation partial ride" in txt
        assert "unprofitable-asserted" in txt
        assert "Fee-cap exhaustion grind" in txt
        assert "profitable-hypothesis" in txt

    def test_brief_residual_counts_computed_not_hardcoded(
        self, brief_pair_db,
    ):
        """r37: §6's residual comparison is COMPUTED from the store.
        The pre-r37 prose hardcoded 'zero open residuals' for the
        successor — true only under the pre-r36 filter; the store
        then held 14 named surfaces. A store change must move the
        brief's prose, never silently contradict it."""
        from blockchain_rd_lab.reporting.decision import (
            build_decision_brief,
        )
        from blockchain_rd_lab.reporting.release import ReleasePackageBuilder
        # the COMPUTED expectation, from the same store the brief
        # reads — never a magic string that can drift from the
        # fixture (the head's seed already carries two named
        # surfaces before the r37 report adds a third)
        rb = ReleasePackageBuilder(brief_pair_db)
        expected_head = len(rb._residual_attacks("cand-rel"))
        expected_tail = len(rb._residual_attacks("cand-rel2"))
        txt = build_decision_brief(
            brief_pair_db, candidate_ids=("cand-rel", "cand-rel2"))
        assert expected_head == 3 and expected_tail == 1
        assert f"carries {expected_head} open named surface(s)" in txt
        assert f"carries {expected_tail} open named surface(s)" in txt
        # the falsified r21-era claim must not survive in any form
        assert "zero open residuals" not in txt

    def test_brief_sweep_maxes_trace_to_census(
        self, brief_pair_db,
    ):
        """r37: §6's r22 sweep maxes are COMPUTED from the census
        history, never hardcoded. The pre-r37 prose carried
        'incumbent 63.9' — the pre-r25-purge stale row; the store's
        sweep max is 33.25."""
        from blockchain_rd_lab.reporting.decision import (
            build_decision_brief,
            census_history,
        )
        txt = build_decision_brief(
            brief_pair_db, candidate_ids=("cand-rel", "cand-rel2"))
        # no sweep records in the fixture -> the brief must render the
        # honest absence, never a stale number
        assert "63.9" not in txt
        assert "no sweep record" in txt
        # the discharge claim computes too: with NO sweep for either
        # candidate, the 'accrue stability evidence' option must
        # render OPEN — the pre-r37 prose asserted it discharged
        # unconditionally
        assert "remains OPEN" in txt
        # with a sweep record stored, the prose must carry the stored
        # number, computed — the bounds rows carry calibration tags
        # so the record classifies as a sweep BY CONTENT (the r33
        # v8 class: named like a battery, carries tagged variants)
        exp = ExperimentRecord(
            candidate_id="cand-rel2",
            parameters={"round": "22",
                        "battery": "attack_parameter_sweep"},
            results={
                "bounds": [
                    {"kind": "wash_flow", "calibration": "wash_level=0.04",
                     "headline": 41.7},
                ],
                "worst_edge": 41.7,
            },
        )
        brief_pair_db.save_experiment(exp)
        txt2 = build_decision_brief(
            brief_pair_db, candidate_ids=("cand-rel", "cand-rel2"))
        assert "41.7" in txt2
        assert census_history(
            brief_pair_db, "cand-rel2")[0][2] == 41.7
        # sweep stored for the TAIL only: discharge still OPEN (the
        # claim requires BOTH candidates swept) and the §6 census
        # depth names the record kind honestly (all-sweep branch —
        # no default-calibration record exists to claim flatness)
        assert "remains OPEN" in txt2
        assert "1 census record(s), all calibration-sweep" in txt2

    def test_brief_gap_carrier_computed_not_hardcoded(
        self, brief_pair_db,
    ):
        """r37: the §6 'ENTIRE gap is one dimension' claim is made
        only where the §19 decomposition actually shows it. The
        fixture's two candidates carry EQUAL dimensions (both
        seeded from the same _candidate shape) — the brief must say
        the scores are equal on every dimension, never the
        r21-era 'oracle_feasibility' line."""
        from blockchain_rd_lab.reporting.decision import (
            build_decision_brief,
        )
        txt = build_decision_brief(
            brief_pair_db, candidate_ids=("cand-rel", "cand-rel2"))
        assert "no dimension carries a difference" in txt
        assert "oracle_feasibility" not in txt.split("## 6.")[-1]
        assert "ENTIRE" not in txt.split("## 6.")[-1]

    def test_brief_census_depth_and_runs_computed(
        self, brief_pair_db,
    ):
        """r37: §6's census-generation depth ('N battery
        generation(s)') and §15 run counts are COMPUTED from the
        store. The pre-r37 prose hardcoded 'five battery
        revisions of flat worst-edge (0.318)' and 'three §15
        battery runs' — r21-era constants the store later
        falsified (r33's v8 is a later generation; the fixture's
        store carries different counts)."""
        from blockchain_rd_lab.reporting.decision import (
            build_decision_brief,
        )

        # add census records with NON-flat worsts to the tail: the
        # flat-worst phrasing must not render where records differ.
        # The sweep record carries TAGGED bounds (content-classified
        # as a sweep); the default record carries none.
        from blockchain_rd_lab.schemas import ExperimentRecord
        brief_pair_db.save_experiment(ExperimentRecord(
            candidate_id="cand-rel2",
            parameters={"round": "14",
                        "battery": "attack_patterns_v2_crash_park"},
            results={"bounds": [{"kind": "crash_park", "headline": 0.318}],
                     "worst_edge": 0.318},
        ))
        brief_pair_db.save_experiment(ExperimentRecord(
            candidate_id="cand-rel2",
            parameters={"round": "22",
                        "battery": "attack_parameter_sweep"},
            results={"bounds": [
                        {"kind": "wash_flow",
                         "calibration": "wash_level=0.04",
                         "headline": 33.25}],
                     "worst_edge": 33.25},
        ))
        txt = build_decision_brief(
            brief_pair_db, candidate_ids=("cand-rel", "cand-rel2"))
        # computed counts render; the hardcoded r21-era constants
        # must not. The tail holds one default-calibration record
        # (0.318, untagged bounds) and one sweep record (33.25,
        # tagged bounds) — the depth line must SPLIT them by CONTENT
        # kind, never flatten the sweep into the default-generation
        # flatness claim (the r21 prose mixed them: 'flat 0.318'
        # alongside a 33.25 sweep the same store held)
        assert "battery generation" in txt
        assert "1 default-calibration battery generation(s) at flat worst-edge (0.318)" in txt
        assert "1 calibration-sweep record(s)" in txt
        assert "flat worst-edge (0.318)" in txt
        # §15 run counts: neither fixture candidate carries a
        # scenarios experiment — the honest zero renders
        assert "0 §15 battery runs" in txt
        # the r21-era constants are gone in ALL forms
        assert "five battery revisions" not in txt
        assert "three §15 battery runs" not in txt

    def test_brief_no_models_does_not_crash(self, tmp_path: Path):
        """r38 pre-audit catch: the §6 loop-exercise line computed
        max(version) over an empty generator when a candidate had no
        stored models — ValueError. The brief must render honestly,
        never crash."""
        from blockchain_rd_lab.reporting.decision import (
            build_decision_brief,
        )
        db = LabDatabase(tmp_path / "test-brief-nomodel.db")
        db.create_all()
        c1 = _candidate("cand-nm1")
        c2 = _candidate("cand-nm2")
        c2.name = "Second No-Model"
        db.save_candidate(c1)
        db.save_candidate(c2)
        # neither gets a stored model — the r37 code would crash
        txt = build_decision_brief(
            db, candidate_ids=("cand-nm1", "cand-nm2"))
        assert "no stored model versions" in txt
        assert "0 §15 battery runs" in txt

