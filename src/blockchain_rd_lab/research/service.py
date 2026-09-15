"""Phase 2 orchestration: research candidates and filter the funnel (§7).

Per candidate: Prior-Art → Economist → Market (LLM agents, structured
output) → deterministic post-processing (code): novelty class + score,
economic/market dimension scores, fatal-flaw gate, status transitions,
source + prior-art persistence. A failing agent never kills the run (§35).

The filter is pure deterministic code: cut class A/B (clearly existing /
very similar), keep the best N by novelty then coherence (§7: 100→20).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from blockchain_rd_lab.agents.base import LLMError, LLMProvider
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.research import (
    CandidateBrief,
    CandidateResearchResult,
    EconomistReport,
    FilterOutcome,
    MarketReport,
    PriorArtReport,
)
from blockchain_rd_lab.research.agents import (
    EconomistAgent,
    MarketAgent,
    PriorArtAgent,
)
from blockchain_rd_lab.schemas import (
    Candidate,
    CandidateStatus,
    FatalFlaw,
    NoveltyClass,
    ScoreBreakdown,
    novelty_score_for,
    utcnow,
)


@dataclass(frozen=True)
class VerifiedSource:
    """Retrieved source provenance accepted as prior-art evidence."""

    title: str
    url: str
    source_type: str
    content_sha256: str
    retrieved_at: datetime


class SourceVerifier:
    """Fetch and hash cited sources before they enter the evidence store."""

    max_bytes = 1_000_000
    timeout_seconds = 5

    def verify(self, source: Any) -> VerifiedSource | None:
        parsed = urlparse(source.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        try:
            request = Request(
                source.url,
                headers={"User-Agent": "AI-Blockchain-RD-Lab/1.0"},
            )
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content = response.read(self.max_bytes + 1)
            if len(content) > self.max_bytes:
                return None
        except Exception:
            return None
        return VerifiedSource(
            title=source.title,
            url=source.url,
            source_type=source.source_type,
            content_sha256=hashlib.sha256(content).hexdigest(),
            retrieved_at=utcnow(),
        )


class ResearchService:
    """Runs the Phase 2 research loop over generated candidates."""

    def __init__(
        self,
        provider: LLMProvider,
        database: LabDatabase,
        artifacts_dir: Path | None = None,
        source_verifier: SourceVerifier | None = None,
    ) -> None:
        self.provider = provider
        self.database = database
        self.artifacts_dir = artifacts_dir
        self.source_verifier = source_verifier or SourceVerifier()
        self.prior_art_agent = PriorArtAgent(provider, database=database)
        self.economist_agent = EconomistAgent(provider, database=database)
        self.market_agent = MarketAgent(provider, database=database)

    # -- public API -----------------------------------------------------------

    def research_candidate(self, candidate: Candidate) -> CandidateResearchResult:
        """Run all three research agents on one candidate; persist findings."""
        brief = CandidateBrief.from_candidate(candidate)
        result = CandidateResearchResult(candidate_id=candidate.id)

        # Status: GENERATED → RESEARCHING (§11)
        if candidate.status is CandidateStatus.GENERATED:
            candidate.transition(CandidateStatus.RESEARCHING)
            self.database.save_candidate(candidate)

        # 1) Prior art
        try:
            report, _ = self.prior_art_agent.execute(brief)
            assert isinstance(report, PriorArtReport)
            result.prior_art = self._persist_prior_art(candidate.id, report)
        except LLMError as exc:
            result.errors.append(f"prior_art: {exc}")

        # 2) Economist
        try:
            report, _ = self.economist_agent.execute(brief)
            assert isinstance(report, EconomistReport)
            result.economist = report
        except LLMError as exc:
            result.errors.append(f"economist: {exc}")

        # 3) Market
        try:
            report, _ = self.market_agent.execute(brief)
            assert isinstance(report, MarketReport)
            result.market = report
        except LLMError as exc:
            result.errors.append(f"market: {exc}")

        # 4) Deterministic post-processing (code, §2)
        self._apply_findings(candidate, result)
        self.database.save_candidate(candidate)
        return result

    def research_all(
        self,
        limit: int | None = None,
        only_status: CandidateStatus | None = CandidateStatus.GENERATED,
    ) -> list[CandidateResearchResult]:
        """Research every candidate in the given state (§35: failure-isolated)."""
        candidates = self.database.list_candidates(status=only_status, limit=limit)
        results = []
        for cand in candidates:
            results.append(self.research_candidate(cand))
        if self.artifacts_dir is not None:
            self._write_artifacts(results)
        return results

    # -- deterministic post-processing -------------------------------------------

    def _apply_findings(self, candidate: Candidate, result: CandidateResearchResult) -> None:
        pa = result.prior_art
        if pa is not None:
            candidate.novelty_class = pa.novelty_class
            candidate.novelty_score = novelty_score_for(pa.novelty_class)
            candidate.scores["novelty"] = ScoreBreakdown(
                dimension="novelty",
                score=novelty_score_for(pa.novelty_class),
                confidence=pa.confidence,
                rationale=pa.conclusion or NOVELTY_TEXT[pa.novelty_class],
                evidence_level="INFERENCE",
            )
            if candidate.status is CandidateStatus.RESEARCHING:
                candidate.transition(CandidateStatus.PRIOR_ART_CHECKED)

        eco = result.economist
        if eco is not None:
            candidate.scores["economic_coherence"] = ScoreBreakdown(
                dimension="economic_coherence",
                score=eco.economic_coherence_score,
                confidence=0.8,
                rationale=eco.summary,
                evidence_level=eco.evidence_level.value,
            )
            # The Economist's fatal bit is an agent hypothesis, not
            # deterministic confirmation (§2, §20). Preserve the concern as
            # evidence for later formalization/simulation/red-team stages,
            # but never reject or mark it confirmed on the LLM assertion alone.
            fatal_concerns = [c for c in eco.concerns if c.fatal]
            for concern in fatal_concerns:
                candidate.fatal_flaws.append(
                    FatalFlaw(
                        flaw_id=f"ff-{candidate.id}-{concern.topic[:24]}",
                        category="economic",
                        description=concern.note,
                        confirmed=False,
                        identified_by="economist",
                    )
                )

        mkt = result.market
        if mkt is not None:
            candidate.scores["market_demand"] = ScoreBreakdown(
                dimension="market_demand",
                score=mkt.market_demand_score,
                confidence=0.7,
                rationale=mkt.problem,
                evidence_level=mkt.evidence_level.value,
            )

        # Fatal flaw confirmed → REJECTED (§11, §20)
        terminal = (
            CandidateStatus.REJECTED,
            CandidateStatus.FAILED,
            CandidateStatus.SUPERSEDED,
        )
        if (result.rejected or candidate.has_confirmed_fatal_flaw) and (
            candidate.status not in terminal
        ):
            candidate.transition(CandidateStatus.REJECTED)

    def _persist_prior_art(self, candidate_id: str, report: PriorArtReport) -> PriorArtReport:
        """Store queries, sources, findings, similar mechanisms (§12, §22).

        One row per cited source; a report with NO sources still records
        its queries, findings, similar mechanisms and conclusion — an
        evidence trail must not vanish because the search cited nothing
        (the r8 gap: sourceless reports persisted zero rows silently).
        """
        agent_novelty_class = report.novelty_class.value
        verified_sources = [
            verified
            for source in report.sources
            if (verified := self.source_verifier.verify(source)) is not None
        ]
        if not verified_sources and report.novelty_class is not NoveltyClass.E:
            # A classification without retrieved evidence is not evidence.
            report = report.model_copy(update={
                "novelty_class": NoveltyClass.E,
                "confidence": 0.0,
                "conclusion": "Insufficient evidence: no cited source was retrieved and verified.",
            })
        finding = json.dumps(
            {
                "conclusion": report.conclusion,
                "similar_mechanisms": [m.model_dump() for m in report.similar_mechanisms],
                "findings": report.findings,
                "novelty_class": report.novelty_class.value,
                "agent_novelty_class": agent_novelty_class,
                "verified_sources": [
                    {
                        "url": source.url,
                        "content_sha256": source.content_sha256,
                        "retrieved_at": source.retrieved_at.isoformat(),
                    }
                    for source in verified_sources
                ],
                "unverified_source_count": len(report.sources) - len(verified_sources),
            },
            default=str,
        )
        query = "; ".join(report.search_queries) or "(none)"
        source_ids: list[int | None] = [
            self._save_source_ref(source) for source in verified_sources
        ] or [None]
        for source_id in source_ids:
            self.database.save_prior_art(
                candidate_id=candidate_id,
                query=query,
                finding=finding,
                similarity_class=report.novelty_class.value,
                source_id=source_id,
            )
        return report

    def _save_source_ref(self, source: VerifiedSource) -> int | None:
        """Persist one verified source with its retrieval provenance."""
        try:
            return self.database.save_source(
                title=source.title,
                url=source.url,
                source_type=source.source_type,
                content_sha256=source.content_sha256,
                retrieved_at=source.retrieved_at,
                verification_status="verified",
            )
        except Exception:
            return None

    def _write_artifacts(self, results: list[CandidateResearchResult]) -> None:
        if self.artifacts_dir is None:
            return
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "researched": len(results),
            "candidates": [
                {
                    "candidate_id": r.candidate_id,
                    "novelty_class": r.prior_art.novelty_class.value if r.prior_art else None,
                    "coherence": (
                        r.economist.economic_coherence_score if r.economist else None
                    ),
                    "demand": r.market.market_demand_score if r.market else None,
                    "rejected": r.rejected,
                    "errors": r.errors,
                }
                for r in results
            ],
        }
        first = results[0].candidate_id if results else "empty"
        assert self.artifacts_dir is not None  # set in __init__ or via call site
        path = self.artifacts_dir / f"research-{first}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


NOVELTY_TEXT = {
    NoveltyClass.A: "clearly existing",
    NoveltyClass.B: "very similar existing mechanism",
    NoveltyClass.C: "adjacent mechanism",
    NoveltyClass.D: "substantially novel relative to searched sources",
    NoveltyClass.E: "insufficient evidence",
}


# ---------------------------------------------------------------------------
# Deterministic filter (§7: 100 ideas → 20 serious candidates)
# ---------------------------------------------------------------------------


class ResearchFilter:
    """Pure-code funnel cut after prior-art research (§7, §12)."""

    def __init__(self, target: int = 20) -> None:
        self.target = target

    def apply(self, database: LabDatabase) -> FilterOutcome:
        """Cut class A/B candidates; keep top-N by (novelty, coherence, demand).

        Rejected A/B candidates move to REJECTED (§11) with an evidence note.
        Selected candidates stay PRIOR_ART_CHECKED for Phase 3 formalization.
        """
        outcome = FilterOutcome(target=self.target)
        candidates = database.list_candidates(status=CandidateStatus.PRIOR_ART_CHECKED)

        # 1) Cut class A / B (clearly / very-similar existing) — §12.
        survivors: list[Candidate] = []
        for cand in candidates:
            if cand.novelty_class in (NoveltyClass.A, NoveltyClass.B):
                outcome.rejected_class_a += cand.novelty_class is NoveltyClass.A
                outcome.rejected_class_b += cand.novelty_class is NoveltyClass.B
                outcome.rejected += 1
                outcome.rejected_details.append(
                    f"{cand.id} ({cand.name}) — novelty class {cand.novelty_class.value}"
                )
                cand.transition(CandidateStatus.REJECTED)
                database.save_candidate(cand)
            else:
                survivors.append(cand)

        # 2) Rank survivors deterministically: novelty, coherence, demand, name.
        def sort_key(c: Candidate) -> tuple[float, float, float, str]:
            coherence = c.scores.get("economic_coherence")
            demand = c.scores.get("market_demand")
            novelty = c.novelty_score if c.novelty_score is not None else 5.0
            return (
                -novelty,
                -(coherence.score if coherence else 5.0),
                -(demand.score if demand else 5.0),
                c.name,
            )

        ranked = sorted(survivors, key=sort_key)
        kept = ranked[: self.target]

        # 3) Overflow beyond target is REJECTED for this cycle (may be re-run).
        overflow = ranked[self.target :]
        for cand in overflow:
            outcome.rejected_details.append(
                f"{cand.id} ({cand.name}) — funnel overflow beyond {self.target}"
            )
            cand.transition(CandidateStatus.REJECTED)
            database.save_candidate(cand)

        outcome.considered = len(candidates)
        outcome.kept = len(kept)
        outcome.kept_ids = [c.id for c in kept]
        outcome.rejected += len(overflow)
        return outcome
