"""Curriculum guard tests (anti-reward-hacking, SimSkill-inspired).

The guard answers the question SimSkill (arXiv 2609.03753, §3.1) names
the system-level analogue of reward hacking: is the corpus obtaining
repeated positive verdicts by farming one family of trivially-passing
candidates instead of expanding real competence?

The canonical case is the round-7 vacuum: six ranked finalists from a
narrow family whose §15 "clean" evidence was vacuous (saturated
trajectories) — positive verdicts farmed on non-evidence. The guard
must flag exactly that shape as DEGENERATE, tolerate honest
concentration as WARN, and report healthy diversity as OK.
"""

from __future__ import annotations

import pytest

from blockchain_rd_lab.discovery.curriculum import CurriculumGuard
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


class _StubDB:
    """Minimal LabDatabase stand-in: list_candidates only."""

    def __init__(self, cands: list[Candidate]) -> None:
        self.cands = cands

    def list_candidates(self, limit=None):
        return self.cands


def _cand(name: str, desc: str, status: CandidateStatus) -> Candidate:
    c = Candidate(
        name=name, category="x", description=desc, core_mechanism="m"
    )
    c.status = status
    return c


def _farm_corpus(vacuous: bool) -> _StubDB:
    """The pre-r7 shape: one family holds 75% of ranked, all unhealthy."""
    cands: list[Candidate] = []
    for i in range(6):
        c = _cand(
            f"m{i}",
            "market price volatility trade float",
            CandidateStatus.FINALIST,
        )
        cands.append(c)
    for i in range(2):
        cands.append(
            _cand(
                f"e{i}",
                "energy power grid electricity",
                CandidateStatus.SCORED,
            )
        )
    # unrelated coverage so the corpus is not 'starving'
    cands.append(
        _cand("c1", "climate carbon emission weather", CandidateStatus.RESEARCHING)
    )
    cands.append(
        _cand(
            "d1", "demographic population birth migration", CandidateStatus.RESEARCHING
        )
    )
    db = _StubDB(cands)
    health = {}
    if vacuous:
        health = {
            c.id: "vacuous"
            for c in cands
            if c.status is CandidateStatus.FINALIST
        }
    return _StubDB(cands) if not vacuous else _WithHealth(db.cands, health)


class _WithHealth(_StubDB):
    def __init__(self, cands, health):
        super().__init__(cands)
        self.health = health


class TestCurriculumGuard:
    def test_family_classification_uses_vocabulary(self):
        guard = CurriculumGuard(_StubDB([]))
        assert (
            guard.family_of("Carbon Gas", "carbon emission climate mechanism")
            == "climate-driven"
        )
        assert (
            guard.family_of("Foo", "totally unrelated words here") == "uncategorized"
        )

    def test_degenerate_farming_detected(self):
        """The pre-r7 vacuum: dominant family + vacuous evidence."""
        cands = _farm_corpus(vacuous=False).cands
        health = {
            c.id: "vacuous"
            for c in cands
            if c.status is CandidateStatus.FINALIST
        }
        verdict = CurriculumGuard(_StubDB(cands), health=health).assess()
        assert verdict.verdict == "degenerate"
        assert verdict.dominant_family == "market-driven"
        assert verdict.dominant_share > 0.5
        assert verdict.dominant_healthy is False
        assert any("reward-hacking" in r or "farmed" in r for r in verdict.reasons)

    def test_honest_concentration_is_warn_not_degenerate(self):
        """Same concentration, but evidence is real — a risk note, not
        a farming verdict (§12: honesty about what was measured)."""
        cands = _farm_corpus(vacuous=False).cands
        verdict = CurriculumGuard(_StubDB(cands)).assess()
        assert verdict.verdict == "warn"
        assert verdict.dominant_healthy is True

    def test_diverse_corpus_is_ok(self):
        cands = [
            _cand("a", "market price volatility trade float", CandidateStatus.SCORED),
            _cand("b", "energy power grid electricity", CandidateStatus.SCORED),
            _cand("c", "climate carbon emission weather", CandidateStatus.SCORED),
            _cand("d", "usage fee gas activity tx volume", CandidateStatus.SCORED),
            _cand(
                "e",
                "stablecoin settlement payment fx liquidity collateral",
                CandidateStatus.RESEARCHING,
            ),
            _cand(
                "f",
                "insurance float premium risk coverage",
                CandidateStatus.RESEARCHING,
            ),
            _cand(
                "g",
                "demographic population birth migration",
                CandidateStatus.RESEARCHING,
            ),
        ]
        verdict = CurriculumGuard(_StubDB(cands)).assess()
        assert verdict.verdict == "ok"
        assert verdict.dominant_share < 0.5

    def test_starving_corpus_flagged(self):
        """Fewer than 3 families = curriculum starvation (novelty gap)."""
        cands = [
            _cand("a", "market price volatility trade", CandidateStatus.SCORED),
            _cand("a2", "market price trade float", CandidateStatus.SCORED),
            _cand("b", "totally unrelated words", CandidateStatus.RESEARCHING),
        ]
        verdict = CurriculumGuard(_StubDB(cands)).assess()
        assert verdict.verdict == "starving"
        assert "starvation" in verdict.reasons[0]

    def test_live_corpus_is_healthy(self):
        """Post-r7 live corpus: 10 families, no dominant family >50%,
        all healthy — the guard must read OK (regression sentinel for
        the corrected corpus)."""
        from blockchain_rd_lab.config import REPO_ROOT, load_config
        from blockchain_rd_lab.database import LabDatabase

        db_path = REPO_ROOT / load_config().storage.database
        if not db_path.exists():
            pytest.skip(
                "live corpus database not present (CI / fresh checkout) — "
                "this sentinel only runs against a populated local corpus"
            )
        db = LabDatabase(db_path)
        verdict = CurriculumGuard(db).assess()
        assert verdict.verdict in ("ok", "warn")
        assert verdict.families_present >= 5
