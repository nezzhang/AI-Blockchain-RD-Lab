"""Tests for the §17 Token Supply Mechanism Laboratory (r39).

Probes cover:
- All 13 drivers instantiate and produce bounded output
- Combinator produces non-empty, deterministic output for rank-1 candidate
- Scoring dimensions are deterministic
- Empty-mechanism edge case renders honestly, never crashes
- §25 questions are all answered in the rendered report
- No existing gates broken
"""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.tokenomics.combinator import (
    TokenDesign,
    combine,
    combine_all_registered,
    extract_mechanism_tags,
)
from blockchain_rd_lab.tokenomics.report import build_token_report
from blockchain_rd_lab.tokenomics.scoring import (
    TokenScore,
    _supply_fn_has_burn_path,
    _supply_fn_has_mint_path,
    rank_designs,
    score_design,
)
from blockchain_rd_lab.tokenomics.supply_drivers import (
    DRIVER_REGISTRY,
    DriverCategory,
    SupplyDriver,
    drivers_for_tags,
    get_driver,
)

# ---------------------------------------------------------------------------
# Driver registry
# ---------------------------------------------------------------------------


class TestDriverRegistry:
    def test_thirteen_drivers_registered(self):
        assert len(DRIVER_REGISTRY) == 13

    def test_all_categories_present(self):
        cats = {d.category for d in DRIVER_REGISTRY}
        expected = set(DriverCategory)
        assert cats == expected

    def test_every_driver_is_frozen(self):
        for d in DRIVER_REGISTRY:
            with pytest.raises(AttributeError):
                d.name = "mutated"  # type: ignore[misc]

    def test_supply_fn_bounded_for_all_drivers(self):
        """Every driver's supply function must return [-1, 1] for any state."""
        extreme_states = [
            {},
            {k: 1e12 for k in ["trading_volume", "active_users",
                                "corridor_population", "network_nodes",
                                "ai_throughput_ops", "renewable_energy_mwh",
                                "commodity_basket_price", "claims_ratio"]},
            {k: -1e12 for k in ["gdp_growth_rate", "productivity_index",
                                 "climate_risk_index", "prediction_confidence"]},
        ]
        for d in DRIVER_REGISTRY:
            for state in extreme_states:
                val = d.supply_fn(state)
                assert not math.isnan(val), f"{d.name} returned NaN"
                assert -1.0 - 1e-9 <= val <= 1.0 + 1e-9, (
                    f"{d.name} unbounded: {val}"
                )

    def test_get_driver_by_name(self):
        d = get_driver("market-volume")
        assert d is not None
        assert d.category == DriverCategory.MARKET

    def test_get_driver_missing_returns_none(self):
        assert get_driver("nonexistent-driver") is None

    def test_drivers_for_tags_empty(self):
        assert drivers_for_tags(set()) == []

    def test_drivers_for_tags_deterministic_order(self):
        tags = {"escrow", "fx", "payment"}
        r1 = drivers_for_tags(tags)
        r2 = drivers_for_tags(tags)
        assert [d.name for d in r1] == [d.name for d in r2]


# ---------------------------------------------------------------------------
# Combinator
# ---------------------------------------------------------------------------


class TestCombinator:
    RANK1_DESC = (
        "A fee-smoothing escrow whose retention keys the SIGNED separation "
        "between fast pressure and a slow regime anchor: sustained premium "
        "pressure (up-ramps) raises retention, crash legs release it, and "
        "zero-mean resonance cycles average OUT instead of over-retaining "
        "at a clip ceiling on every ramp phase."
    )

    def test_extract_tags_from_rank1_description(self):
        tags = extract_mechanism_tags(self.RANK1_DESC)
        # Should find at least escrow, fee, stability
        assert "escrow" in tags
        assert "fee" in tags
        assert "stability" in tags

    def test_extract_tags_empty_description(self):
        assert extract_mechanism_tags("") == set()

    def test_extract_tags_no_match(self):
        assert extract_mechanism_tags("a completely unrelated string xyz") == set()

    def test_combine_rank1_produces_designs(self):
        designs = combine("cand-test", "Test", self.RANK1_DESC)
        assert len(designs) > 0
        assert all(isinstance(d, TokenDesign) for d in designs)

    def test_combine_empty_description_returns_empty(self):
        designs = combine("cand-test", "Test", "")
        assert designs == []

    def test_combine_max_designs_respected(self):
        designs = combine("cand-test", "Test", self.RANK1_DESC, max_designs=2)
        assert len(designs) <= 2

    def test_combine_deterministic(self):
        d1 = combine("cand-test", "Test", self.RANK1_DESC)
        d2 = combine("cand-test", "Test", self.RANK1_DESC)
        assert [x.design_id for x in d1] == [x.design_id for x in d2]

    def test_combine_sorted_by_score_descending(self):
        designs = combine_all_registered("cand-test", "Test", self.RANK1_DESC)
        scores = [d.compatibility_score for d in designs]
        assert scores == sorted(scores, reverse=True)

    def test_design_id_format(self):
        designs = combine("cand-test", "Test", self.RANK1_DESC)
        if designs:
            assert designs[0].design_id.startswith("cand-test+")


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _make_design(driver_name: str = "usage-growth") -> TokenDesign:
    d = get_driver(driver_name)
    assert d is not None
    return TokenDesign(
        mechanism_id="cand-test",
        mechanism_name="Test Mechanism",
        driver=d,
        tag_overlap=2,
        compatibility_score=0.5,
    )


class TestScoring:
    def test_score_design_returns_tokenscore(self):
        design = _make_design()
        score = score_design(design)
        assert isinstance(score, TokenScore)

    def test_scores_in_range(self):
        for d in DRIVER_REGISTRY:
            design = TokenDesign(
                mechanism_id="cand-test",
                mechanism_name="Test",
                driver=d,
                tag_overlap=1,
                compatibility_score=0.3,
            )
            score = score_design(design)
            assert 0.0 <= score.dilution_resistance <= 10.0
            assert 0.0 <= score.death_spiral_resistance <= 10.0
            assert 0.0 <= score.oracle_manipulability <= 10.0
            assert 0.0 <= score.game_theory_stability <= 10.0
            assert 0.0 <= score.overall <= 10.0

    def test_scoring_deterministic(self):
        design = _make_design()
        s1 = score_design(design)
        s2 = score_design(design)
        assert s1.overall == s2.overall

    def test_rank_designs_deterministic_order(self):
        designs = [_make_design(d.name) for d in DRIVER_REGISTRY[:3]]
        r1 = rank_designs(designs)
        r2 = rank_designs(designs)
        assert [x[0].design_id for x in r1] == [x[0].design_id for x in r2]

    def test_rank_designs_sorted_by_overall_descending(self):
        designs = [_make_design(d.name) for d in DRIVER_REGISTRY]
        ranked = rank_designs(designs)
        overalls = [s.overall for _, s in ranked]
        assert overalls == sorted(overalls, reverse=True)

    def test_oracle_manipulation_badness_lowers_overall(self):
        base = get_driver("usage-growth")
        assert base is not None
        low_risk = replace(
            base, name="usage-low-risk", manipulation_vectors=()
        )
        high_risk = replace(
            base,
            name="usage-high-risk",
            manipulation_vectors=("a", "b", "c", "d"),
        )
        low = score_design(TokenDesign("low", "Low", low_risk, 1, 0.5))
        high = score_design(TokenDesign("high", "High", high_risk, 1, 0.5))
        assert low.oracle_manipulability < high.oracle_manipulability
        assert low.overall > high.overall

    def test_driver_probe_states_match_supply_paths(self):
        """Every registry driver is scored using its own declared states."""
        for driver in DRIVER_REGISTRY:
            assert _supply_fn_has_burn_path(driver) == any(
                driver.supply_fn(state) < -1e-9
                for state in driver.burn_probe_states
            )
            assert _supply_fn_has_mint_path(driver) == any(
                driver.supply_fn(state) > 1e-9
                for state in driver.mint_probe_states
            )

    # -- r40: the lab's own hostile audit of the r39 tokenomics code --

    def test_climate_driver_is_honestly_burn_only(self):
        """r40 F1: the climate driver's mint probe previously asserted
        climate_risk_index=-1.0 — NEGATIVE risk, physically impossible
        for a 0-1 index — buying a bidirectional credit (mint path)
        no real input can exercise. The honest score is burn-only:
        no mint path, no bidirectional game-theory bonus."""
        d = get_driver("climate-risk-burn")
        assert d is not None
        # physical domain: risk in [0, 1]
        for risk in (0.0, 0.25, 0.5, 0.75, 1.0):
            val = d.supply_fn({"climate_risk_index": risk})
            assert val <= 1e-9, (
                f"climate fn must never mint on physical input; "
                f"risk={risk} -> {val}"
            )
        score = score_design(_make_design("climate-risk-burn"))
        # burn-only reality: no mint path credit
        assert not _supply_fn_has_mint_path(d)
        assert score.death_spiral_resistance == 5.0  # bounded only
        assert score.game_theory_stability == 3.0  # bounded, not bidirectional

    def test_jaccard_ordering(self):
        """r40 F2 executed: Jaccard intersection / union — unmatched tags on
        either side reduce the score. A 4-tag driver matching 3 of a
        6-tag mechanism must outrank an 8-tag driver matching 3."""
        from blockchain_rd_lab.tokenomics.supply_drivers import DriverCategory

        focused = SupplyDriver(
            category=DriverCategory.USAGE,
            name="focused-driver",
            signal_source="test",
            supply_fn=lambda s: 0.0,
            compatibility_tags=frozenset({"a", "b", "c", "d"}),
        )
        broad = SupplyDriver(
            category=DriverCategory.NETWORK,
            name="broad-driver",
            signal_source="test",
            supply_fn=lambda s: 0.0,
            compatibility_tags=frozenset(
                {"a", "b", "c", "e", "f", "g", "h", "i"}),
        )
        mech_tags = {"a", "b", "c", "x", "y", "z"}
        j_focused = len(mech_tags & focused.compatibility_tags) / len(
            mech_tags | focused.compatibility_tags)
        j_broad = len(mech_tags & broad.compatibility_tags) / len(
            mech_tags | broad.compatibility_tags)
        assert j_focused > j_broad, (
            "Jaccard must rank the focused driver above the broad one "
            "at equal overlap"
        )

    def test_report_renders_oracle_resistance_not_manip(self, tmp_path):
        """r40 F5: the table previously rendered raw badness
        (oracle_manipulability) beside three higher-better columns —
        a reader naturally parsed 'Oracle Manip. 10.0' as good in a
        table where Dilution 10.0 IS good. The table must render
        Oracle Resistance so every column reads higher = better."""
        db = LabDatabase(tmp_path / "test-r40-report.db")
        db.create_all()
        from blockchain_rd_lab.schemas import Candidate
        c = Candidate(
            id="cand-r40",
            name="Fee Smoothing Escrow",
            category="fx payments",
            description=(
                "A fee-smoothing escrow whose retention keys the SIGNED "
                "separation between fast pressure and a slow regime anchor. "
                "Cross-border FX remittance payment network."
            ),
            core_mechanism="retention = f(signed_separation(fast, slow))",
            overall_score=6.45,
        )
        db.save_candidate(c)
        txt = build_token_report(db, "cand-r40")
        assert "Oracle Resistance" in txt
        assert "Oracle Manip." not in txt
        # the §25 prose still discloses the raw vector count honestly
        assert "manipulation vector(s)" in txt


# ---------------------------------------------------------------------------
# Report renderer
# ---------------------------------------------------------------------------


class TestReport:
    @pytest.fixture()
    def brief_pair_db(self, tmp_path: Path) -> LabDatabase:
        """Minimal DB with one candidate that has a description."""
        db = LabDatabase(tmp_path / "token-report.db")
        db.create_all()
        from blockchain_rd_lab.schemas import Candidate
        c = Candidate(
            id="cand-tok1",
            name="Fee Smoothing Escrow",
            category="fx payments",
            description=(
                "A fee-smoothing escrow whose retention keys the SIGNED "
                "separation between fast pressure and a slow regime anchor. "
                "Cross-border FX remittance payment network."
            ),
            core_mechanism="retention = f(signed_separation(fast, slow))",
            overall_score=6.45,
        )
        db.save_candidate(c)
        return db

    def test_build_report_renders(self, brief_pair_db: LabDatabase):
        txt = build_token_report(brief_pair_db, "cand-tok1")
        assert "§17/§25 Token Economics Report" in txt
        assert "RESEARCH ONLY" in txt

    def test_report_answers_all_25_questions(self, brief_pair_db: LabDatabase):
        txt = build_token_report(brief_pair_db, "cand-tok1")
        q25_markers = [
            "What does 1 token represent?",
            "Why should the token have value?",
            "Does supply growth create dilution?",
            "Can supply reduction create a death spiral?",
            "Can the system be gamed?",
            "What happens during demographic collapse?",
            "What happens if data is revised",
        ]
        for marker in q25_markers:
            assert marker in txt, f"Missing §25 question: {marker}"

    def test_report_deterministic(self, brief_pair_db: LabDatabase):
        t1 = build_token_report(brief_pair_db, "cand-tok1")
        t2 = build_token_report(brief_pair_db, "cand-tok1")
        assert t1 == t2

    def test_report_missing_candidate_raises(self, brief_pair_db: LabDatabase):
        with pytest.raises(ValueError, match="candidate not found"):
            build_token_report(brief_pair_db, "cand-nonexistent")

    def test_report_no_matching_tags_honest_absence(self, tmp_path: Path):
        """A candidate whose description matches no driver tags gets honest absence."""
        db = LabDatabase(tmp_path / "empty-desc.db")
        db.create_all()
        from blockchain_rd_lab.schemas import Candidate
        c = Candidate(
            id="cand-empty", name="Unrelated", category="other",
            description="xyzzy plugh no relevant terms here at all",
            core_mechanism="nothing",
            overall_score=1.0,
        )
        db.save_candidate(c)
        txt = build_token_report(db, "cand-empty")
        assert "No mechanism tags extracted" in txt or "No compatible supply drivers" in txt

    def test_report_contains_ranked_table(self, brief_pair_db: LabDatabase):
        txt = build_token_report(brief_pair_db, "cand-tok1")
        assert "| Rank |" in txt
        assert "Dilution" in txt
        assert "Death Spiral" in txt
