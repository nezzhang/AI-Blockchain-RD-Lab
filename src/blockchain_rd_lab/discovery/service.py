"""Discovery orchestration service (Phase 1).

Pipeline: generate (LLM) → normalize (code) → dedup (code) → store (code).
Every step records evidence; a failed batch never kills the run (§35).
"""

from __future__ import annotations

import json
from pathlib import Path

from blockchain_rd_lab.agents.base import LLMError, LLMProvider
from blockchain_rd_lab.config import LabConfig, load_config
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.discovery import (
    DiscoveryRunSummary,
    IdeaBatch,
    IdeaDraft,
    NormalizedIdea,
)
from blockchain_rd_lab.discovery.agent import DiscoveryAgent, DiscoveryPayload
from blockchain_rd_lab.discovery.normalize import Deduplicator, Normalizer
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


class DiscoveryService:
    """Runs the Phase 1 discovery loop against a lab database."""

    def __init__(
        self,
        provider: LLMProvider,
        database: LabDatabase,
        lab_config: LabConfig | None = None,
        research_config=None,
        ideas_dir: Path | None = None,
    ) -> None:
        self.provider = provider
        self.database = database
        self.lab_config = lab_config or load_config()
        self.research_config = research_config
        self.agent = DiscoveryAgent(
            provider,
            database=database,
            research_config=self.research_config,
        )
        self.normalizer = Normalizer(self.research_config)
        self.deduplicator = Deduplicator(
            self.research_config.dedup if self.research_config else None
        )
        self.ideas_dir = ideas_dir

    # -- public API -----------------------------------------------------------

    def discover(
        self,
        count: int = 20,
        avoid_existing: bool = True,
        combination_hints: list[str] | None = None,
    ) -> DiscoveryRunSummary:
        """Generate `count` ideas in batches; normalize, dedup, store.

        `combination_hints` (§18): free-text mechanism-combination briefs;
        each batch request carries the next hint, steering the agent
        toward economically compatible combinations instead of random
        mashups. Deterministic code (the combinator) proposes; the agent
        still generates; the normalizer/dedup still gate (§2).
        """
        research = self.research_config
        per_batch = research.discovery.ideas_per_batch if research else 5
        stored = self._stored_ideas() if avoid_existing else []
        hints = list(combination_hints or [])
        hint_index = 0

        summary = DiscoveryRunSummary()
        remaining = count
        batch_index = 0
        while remaining > 0:
            batch_size = min(per_batch, remaining)
            hint = ""
            if hints:
                hint = hints[hint_index % len(hints)]
                hint_index += 1
            try:
                payload = DiscoveryPayload(
                    count=batch_size,
                    combination_hint=hint,
                    seed=batch_index,  # reproducible domain draw (§21/§30)
                )
                result, _record = self.agent.execute(payload)
                if not isinstance(result, IdeaBatch):
                    raise LLMError("DiscoveryAgent returned unexpected output type")
                batch = result
            except LLMError as exc:
                summary.failed_batches += 1
                summary.errors.append(f"batch failed: {exc}")
                # §35: never crash the whole run because one LLM call failed.
                break

            drafts = batch.ideas[:batch_size]
            summary.generated += len(drafts)
            for draft in drafts:
                normalized = self.normalizer.normalize(draft, batch.batch_id)
                summary.normalized += 1
                verdict = self.deduplicator.check(normalized, stored)
                if verdict.is_duplicate:
                    summary.duplicates_removed += 1
                    summary.errors.append(
                        f"duplicate skipped: {normalized.name!r} ≈ "
                        f"{verdict.matched_name!r} ({verdict.reason})"
                    )
                    continue
                candidate = normalized.to_candidate()
                self.database.save_candidate(candidate)
                stored.append(normalized)
                summary.stored += 1
                summary.candidate_ids.append(candidate.id)
            remaining -= len(drafts)
            batch_index += 1

        self._write_artifacts(summary, stored)
        return summary

    # -- internals --------------------------------------------------------------

    def _stored_ideas(self) -> list[NormalizedIdea]:
        """Rebuild NormalizedIdea views from stored candidates for dedup.

        §35 fix: dedup against ALL non-terminal candidates, not just
        GENERATED — once a candidate advances (research/formalized/...),
        it must stay visible to dedup, or a resumed run re-stores the
        same mechanism as a "new" candidate.
        """
        out: list[NormalizedIdea] = []
        for cand in self.database.list_candidates(limit=None):
            if cand.status in (CandidateStatus.REJECTED, CandidateStatus.FAILED):
                # Rejected/failed ideas MAY be re-proposed in improved form;
                # the archive index still records the rejection (§26).
                continue
            out.append(self.normalizer.normalize(self._candidate_to_draft(cand)))
        return out

    @staticmethod
    def _candidate_to_draft(cand: Candidate) -> IdeaDraft:
        return IdeaDraft(
            name=cand.name,
            category=cand.category,
            description=cand.description,
            core_mechanism=cand.core_mechanism,
            problem=cand.problem,
            innovation_claim=cand.innovation_claim,
            inputs=cand.inputs,
            outputs=cand.outputs,
            oracle_required=cand.oracle_required,
            blockchain_required=cand.blockchain_required,
            token_required=cand.token_required,
        )

    def _write_artifacts(self, summary: DiscoveryRunSummary, stored: list[NormalizedIdea]) -> None:
        """Persist a JSON evidence artifact per discovery run (research asset)."""
        if self.ideas_dir is None:
            return
        self.ideas_dir.mkdir(parents=True, exist_ok=True)
        artifact = {
            "summary": summary.model_dump(mode="json"),
            "stored_ideas": [
                {
                    "name": i.name,
                    "category": i.category,
                    "domain": i.domain,
                    "description": i.description,
                }
                for i in stored
            ],
        }
        first_id = summary.candidate_ids[0] if summary.candidate_ids else "empty"
        path = (
            self.ideas_dir
            / f"discovery-run-{len(summary.candidate_ids)}-{first_id}.json"
        )
        path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
