"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path
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
def tmp_lab_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated CLI test environment: config dir + private database.

    Monkeypatching CONFIG_DIR alone is NOT enough — an empty config dir
    makes load_config() fall back to the default `database/lab.db`, which
    silently reads and writes the real lab database. This fixture writes a
    lab.yaml pointing storage at a private tmp database so CLI tests can
    never pollute (or depend on) the real lab state.
    """
    import yaml

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    db_rel = tmp_path / "lab.db"
    (config_dir / "lab.yaml").write_text(
        yaml.safe_dump({"storage": {"database": str(db_rel)}}),
        encoding="utf-8",
    )
    monkeypatch.setattr("blockchain_rd_lab.config.CONFIG_DIR", config_dir)
    return tmp_path


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
