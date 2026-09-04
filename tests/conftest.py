"""Shared test fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate


@pytest.fixture()
def memory_db() -> LabDatabase:
    db = LabDatabase(":memory:")
    db.create_all()
    return db


@pytest.fixture()
def sample_candidate() -> Candidate:
    return Candidate(
        name="Population-Linked Supply",
        category="monetary economics",
        description="Token supply tracks verified global population changes.",
        core_mechanism="S(t+1) = S(t) * (1 + alpha * dP/P) with oracle-reported population deltas.",
        problem="Fixed-supply and arbitrary-inflation tokens lack an objective monetary anchor.",
        innovation_claim=(
            "No substantially similar implementation was identified in the searched sources."
        ),
        inputs=["global_population", "births", "deaths", "migration"],
        outputs=["supply_delta"],
        oracle_required=True,
        blockchain_required=True,
        token_required=True,
        source_agent="discovery",
    )


@pytest.fixture()
def fully_scored_candidate(sample_candidate: Candidate) -> Candidate:
    from blockchain_rd_lab.schemas import ScoreBreakdown

    for dim in (
        "novelty",
        "economic_coherence",
        "game_theory",
        "technical_feasibility",
        "oracle_feasibility",
        "security",
        "market_demand",
        "capital_efficiency",
        "network_effects",
        "communication",
        "viral_potential",
    ):
        sample_candidate.scores[dim] = ScoreBreakdown(
            dimension=dim, score=7.0, rationale="test", evidence_level="INFERENCE"
        )
    return sample_candidate


def assert_repr_roundtrip(obj: Any) -> None:
    """Utility: model_dump → model_validate must be lossless."""
    clone = type(obj).model_validate(obj.model_dump())
    assert clone == obj
