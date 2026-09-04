"""SQLite persistence layer (§22).

SQLAlchemy ORM with SQLite. Analytical workloads will move to DuckDB in a
later phase; Phase 0 stores the core lab records:

    candidates, experiments, agent_runs, sources, prior_art, scores
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from blockchain_rd_lab.schemas import (
    AgentRunRecord,
    Candidate,
    CandidateStatus,
    ExperimentRecord,
    FatalFlaw,
    NoveltyClass,
    ScoreBreakdown,
)

# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class CandidateORM(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[str] = mapped_column(String(96))
    description: Mapped[str] = mapped_column(Text)
    core_mechanism: Mapped[str] = mapped_column(Text)
    problem: Mapped[str] = mapped_column(Text, default="")
    innovation_claim: Mapped[str] = mapped_column(Text, default="")

    inputs_json: Mapped[str] = mapped_column(Text, default="[]")
    outputs_json: Mapped[str] = mapped_column(Text, default="[]")

    oracle_required: Mapped[bool] = mapped_column(Boolean, default=False)
    blockchain_required: Mapped[bool] = mapped_column(Boolean, default=True)
    token_required: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[str] = mapped_column(String(32), index=True, default="generated")
    novelty_class: Mapped[str] = mapped_column(String(48), default="insufficient_evidence")
    novelty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    fatal_flaws_json: Mapped[str] = mapped_column(Text, default="[]")
    source_agent: Mapped[str] = mapped_column(String(64), default="discovery")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    experiments: Mapped[list[ExperimentORM]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list[AgentRunORM]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    scores: Mapped[list[ScoreORM]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class ExperimentORM(Base):
    __tablename__ = "experiments"

    experiment_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    git_commit: Mapped[str] = mapped_column(String(64), default="unknown")
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    dataset: Mapped[str] = mapped_column(String(128), default="none")
    model: Mapped[str] = mapped_column(String(128), default="none")
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    simulation_version: Mapped[str] = mapped_column(String(64), default="none")
    results_json: Mapped[str] = mapped_column(Text, default="{}")

    candidate: Mapped[CandidateORM] = relationship(back_populates="experiments")


class AgentRunORM(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidates.id"), nullable=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    model: Mapped[str] = mapped_column(String(64), default="mock-model")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str] = mapped_column(Text, default="{}")

    candidate: Mapped[CandidateORM | None] = relationship(back_populates="agent_runs")


class ScoreORM(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    dimension: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_level: Mapped[str] = mapped_column(String(16), default="INFERENCE")
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    candidate: Mapped[CandidateORM] = relationship(back_populates="scores")


class SourceORM(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(512), unique=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    source_type: Mapped[str] = mapped_column(String(64), default="web")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class PriorArtORM(Base):
    __tablename__ = "prior_art"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    query: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    finding: Mapped[str] = mapped_column(Text)
    similarity_class: Mapped[str] = mapped_column(String(48), default="insufficient_evidence")
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class MathModelORM(Base):
    """Versioned formal models (Phase 3, §13). Never overwritten."""

    __tablename__ = "math_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    model_json: Mapped[str] = mapped_column(Text)  # canonical MathModel dump
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Serialization helpers (Pydantic <-> ORM)
# ---------------------------------------------------------------------------


def candidate_to_orm(candidate: Candidate) -> CandidateORM:
    return CandidateORM(
        id=candidate.id,
        name=candidate.name,
        category=candidate.category,
        description=candidate.description,
        core_mechanism=candidate.core_mechanism,
        problem=candidate.problem,
        innovation_claim=candidate.innovation_claim,
        inputs_json=json.dumps(candidate.inputs),
        outputs_json=json.dumps(candidate.outputs),
        oracle_required=candidate.oracle_required,
        blockchain_required=candidate.blockchain_required,
        token_required=candidate.token_required,
        status=candidate.status.value,
        novelty_class=candidate.novelty_class.value,
        novelty_score=candidate.novelty_score,
        overall_score=candidate.overall_score,
        fatal_flaws_json=json.dumps([f.model_dump(mode="json") for f in candidate.fatal_flaws]),
        source_agent=candidate.source_agent,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def candidate_from_orm(orm: CandidateORM) -> Candidate:
    flaws_raw: list[dict[str, Any]] = json.loads(orm.fatal_flaws_json or "[]")
    scores_raw: dict[str, ScoreBreakdown] = {}
    for s in orm.scores:
        scores_raw[s.dimension] = ScoreBreakdown(
            dimension=s.dimension,
            score=s.score,
            confidence=s.confidence,
            rationale=s.rationale,
            evidence_level=s.evidence_level,
        )
    return Candidate(
        id=orm.id,
        name=orm.name,
        category=orm.category,
        description=orm.description,
        core_mechanism=orm.core_mechanism,
        problem=orm.problem,
        innovation_claim=orm.innovation_claim,
        inputs=json.loads(orm.inputs_json or "[]"),
        outputs=json.loads(orm.outputs_json or "[]"),
        oracle_required=orm.oracle_required,
        blockchain_required=orm.blockchain_required,
        token_required=orm.token_required,
        status=CandidateStatus(orm.status),
        novelty_class=NoveltyClass(orm.novelty_class),
        novelty_score=orm.novelty_score,
        overall_score=orm.overall_score,
        fatal_flaws=[FatalFlaw.model_validate(f) for f in flaws_raw],
        source_agent=orm.source_agent,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        scores=scores_raw,
    )


def experiment_to_orm(record: ExperimentRecord) -> ExperimentORM:
    return ExperimentORM(
        experiment_id=record.experiment_id,
        candidate_id=record.candidate_id,
        timestamp=record.timestamp,
        git_commit=record.git_commit,
        parameters_json=json.dumps(record.parameters, default=str),
        dataset=record.dataset,
        model=record.model,
        seed=record.seed,
        simulation_version=record.simulation_version,
        results_json=json.dumps(record.results, default=str),
    )


def agent_run_to_orm(record: AgentRunRecord) -> AgentRunORM:
    return AgentRunORM(
        run_id=record.run_id,
        agent_name=record.agent_name,
        candidate_id=record.candidate_id,
        started_at=record.started_at,
        finished_at=record.finished_at,
        provider=record.provider,
        model=record.model,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        status=record.status,
        error=record.error,
        output_json=json.dumps(record.output, default=str),
    )


# ---------------------------------------------------------------------------
# Repository (data-access facade)
# ---------------------------------------------------------------------------


class LabDatabase:
    """Repository facade over SQLite for all lab records."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) == ":memory:":
            url = "sqlite:///:memory:"
        else:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{target}"
        self.engine = create_engine(url, echo=False)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        Base.metadata.drop_all(self.engine)

    # -- candidates ---------------------------------------------------------

    def save_candidate(self, candidate: Candidate) -> Candidate:
        with self._session() as session:
            # Upsert by primary key.
            obj = session.get(CandidateORM, candidate.id)
            if obj is None:
                obj = candidate_to_orm(candidate)
                session.add(obj)
            else:
                fresh = candidate_to_orm(candidate)
                for col in CandidateORM.__table__.columns:
                    setattr(obj, col.name, getattr(fresh, col.name))
            # Replace dimension scores (simple history: latest wins).
            obj.scores.clear()
            for dim, breakdown in candidate.scores.items():
                obj.scores.append(
                    ScoreORM(
                        candidate_id=candidate.id,
                        dimension=dim,
                        score=breakdown.score,
                        confidence=breakdown.confidence,
                        rationale=breakdown.rationale,
                        evidence_level=breakdown.evidence_level,
                    )
                )
            session.commit()
        return candidate

    def get_candidate(self, candidate_id: str) -> Candidate | None:
        with self._session() as session:
            obj = session.get(CandidateORM, candidate_id)
            if obj is None:
                return None
            return candidate_from_orm(obj)

    def list_candidates(
        self,
        status: CandidateStatus | None = None,
        limit: int | None = None,
    ) -> list[Candidate]:
        with self._session() as session:
            stmt = select(CandidateORM).order_by(CandidateORM.created_at)
            if status is not None:
                stmt = stmt.where(CandidateORM.status == status.value)
            if limit is not None:
                stmt = stmt.limit(limit)
            return [candidate_from_orm(o) for o in session.scalars(stmt)]

    def count_candidates(self, status: CandidateStatus | None = None) -> int:
        from sqlalchemy import func

        with self._session() as session:
            stmt = select(func.count()).select_from(CandidateORM)
            if status is not None:
                stmt = stmt.where(CandidateORM.status == status.value)
            return int(session.scalar(stmt) or 0)

    def delete_candidate(self, candidate_id: str) -> bool:
        with self._session() as session:
            obj = session.get(CandidateORM, candidate_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            return True

    # -- experiments ----------------------------------------------------------

    def save_experiment(self, record: ExperimentRecord) -> ExperimentRecord:
        with self._session() as session:
            session.merge(experiment_to_orm(record))
            session.commit()
        return record

    def get_experiment(self, experiment_id: str) -> ExperimentRecord | None:
        with self._session() as session:
            obj = session.get(ExperimentORM, experiment_id)
            if obj is None:
                return None
            return ExperimentRecord(
                experiment_id=obj.experiment_id,
                candidate_id=obj.candidate_id,
                timestamp=obj.timestamp,
                git_commit=obj.git_commit,
                parameters=json.loads(obj.parameters_json or "{}"),
                dataset=obj.dataset,
                model=obj.model,
                seed=obj.seed,
                simulation_version=obj.simulation_version,
                results=json.loads(obj.results_json or "{}"),
            )

    def iter_experiments(self, candidate_id: str | None = None) -> Iterator[ExperimentRecord]:
        with self._session() as session:
            stmt = select(ExperimentORM)
            if candidate_id is not None:
                stmt = stmt.where(ExperimentORM.candidate_id == candidate_id)
            for obj in session.scalars(stmt):
                yield ExperimentRecord(
                    experiment_id=obj.experiment_id,
                    candidate_id=obj.candidate_id,
                    timestamp=obj.timestamp,
                    git_commit=obj.git_commit,
                    parameters=json.loads(obj.parameters_json or "{}"),
                    dataset=obj.dataset,
                    model=obj.model,
                    seed=obj.seed,
                    simulation_version=obj.simulation_version,
                    results=json.loads(obj.results_json or "{}"),
                )

    # -- agent runs -----------------------------------------------------------

    def save_agent_run(self, record: AgentRunRecord) -> AgentRunRecord:
        with self._session() as session:
            session.merge(agent_run_to_orm(record))
            session.commit()
        return record

    def iter_agent_runs(self, agent_name: str | None = None) -> Iterator[AgentRunRecord]:
        with self._session() as session:
            stmt = select(AgentRunORM)
            if agent_name is not None:
                stmt = stmt.where(AgentRunORM.agent_name == agent_name)
            for obj in session.scalars(stmt):
                yield AgentRunRecord(
                    run_id=obj.run_id,
                    agent_name=obj.agent_name,
                    candidate_id=obj.candidate_id,
                    started_at=obj.started_at,
                    finished_at=obj.finished_at,
                    provider=obj.provider,
                    model=obj.model,
                    prompt_tokens=obj.prompt_tokens,
                    completion_tokens=obj.completion_tokens,
                    status=obj.status,
                    error=obj.error,
                    output=json.loads(obj.output_json or "{}"),
                )

    # -- sources & prior art (§22, Phase 2) ------------------------------------

    def save_source(self, title: str, url: str, source_type: str = "web") -> int:
        """Insert or reuse a source; returns the source id."""
        with self._session() as session:
            existing = session.scalar(select(SourceORM).where(SourceORM.url == url))
            if existing is not None:
                return int(existing.id)
            obj = SourceORM(url=url, title=title, source_type=source_type)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return int(obj.id)

    def list_sources(self, limit: int | None = None) -> list[dict[str, Any]]:
        with self._session() as session:
            stmt = select(SourceORM).order_by(SourceORM.id)
            if limit is not None:
                stmt = stmt.limit(limit)
            return [
                {
                    "id": int(o.id),
                    "url": o.url,
                    "title": o.title,
                    "source_type": o.source_type,
                }
                for o in session.scalars(stmt)
            ]

    def save_prior_art(
        self,
        candidate_id: str,
        query: str,
        finding: str,
        similarity_class: str,
        source_id: int | None = None,
    ) -> None:
        with self._session() as session:
            session.add(
                PriorArtORM(
                    candidate_id=candidate_id,
                    query=query,
                    finding=finding,
                    similarity_class=similarity_class,
                    source_id=source_id,
                )
            )
            session.commit()

    def list_prior_art(self, candidate_id: str | None = None) -> list[dict[str, Any]]:
        with self._session() as session:
            stmt = select(PriorArtORM)
            if candidate_id is not None:
                stmt = stmt.where(PriorArtORM.candidate_id == candidate_id)
            return [
                {
                    "candidate_id": o.candidate_id,
                    "query": o.query,
                    "finding": o.finding,
                    "similarity_class": o.similarity_class,
                    "source_id": o.source_id,
                }
                for o in session.scalars(stmt)
            ]

    # -- math models (Phase 3, §13) --------------------------------------------

    def save_math_model(
        self,
        candidate_id: str,
        model_json: str,
        rationale: str,
        version: int = 1,
    ) -> int:
        """Insert a new model version; returns the row id."""
        with self._session() as session:
            obj = MathModelORM(
                candidate_id=candidate_id,
                version=version,
                model_json=model_json,
                rationale=rationale,
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return int(obj.id)

    def latest_model_version(self, candidate_id: str) -> int:
        """Highest stored model version for a candidate (0 if none)."""
        with self._session() as session:
            stmt = (
                select(MathModelORM.version)
                .where(MathModelORM.candidate_id == candidate_id)
                .order_by(MathModelORM.version.desc())
                .limit(1)
            )
            v = session.scalar(stmt)
            return int(v) if v is not None else 0

    def get_latest_math_model(self, candidate_id: str) -> str | None:
        """Latest model JSON dump for a candidate (None if never formalized)."""
        with self._session() as session:
            stmt = (
                select(MathModelORM.model_json)
                .where(MathModelORM.candidate_id == candidate_id)
                .order_by(MathModelORM.version.desc())
                .limit(1)
            )
            dump = session.scalar(stmt)
            return str(dump) if dump is not None else None

    def list_math_models(self, candidate_id: str | None = None) -> list[dict[str, Any]]:
        with self._session() as session:
            stmt = select(MathModelORM).order_by(MathModelORM.candidate_id, MathModelORM.version)
            if candidate_id is not None:
                stmt = stmt.where(MathModelORM.candidate_id == candidate_id)
            return [
                {
                    "candidate_id": o.candidate_id,
                    "version": int(o.version),
                    "rationale": o.rationale,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in session.scalars(stmt)
            ]
