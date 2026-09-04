"""Phase 3 orchestration: formalize researched candidates (§13).

Per candidate: Mechanism Designer agent proposes a MathModel; deterministic
integrity checks (declared symbols, ASCII equations, balanced parens)
already ran inside Pydantic validation; the service versions and stores the
model, transitions PRIOR_ART_CHECKED → FORMALIZED (§11), and isolates
per-candidate failures (§35).
"""

from __future__ import annotations

import json
from pathlib import Path

from blockchain_rd_lab.agents.base import LLMError, LLMProvider
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import (
    FormalizationResult,
    FormalizationSummary,
    MathModel,
    model_from_dict,
)
from blockchain_rd_lab.formalization.agents import (
    MechanismDesignerAgent,
    build_math_model_fixture,
)
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


class FormalizationService:
    """Runs the Phase 3 formalization loop over prior-art-checked candidates."""

    def __init__(
        self,
        provider: LLMProvider,
        database: LabDatabase,
    ) -> None:
        self.provider = provider
        self.database = database
        self.designer = MechanismDesignerAgent(provider, database=database)

    # -- public API -----------------------------------------------------------

    def formalize_candidate(self, candidate: Candidate) -> FormalizationResult:
        """Formalize one candidate; store the model version; transition state."""
        result = FormalizationResult(candidate_id=candidate.id)
        brief = CandidateBrief.from_candidate(candidate)

        try:
            model_obj, _ = self.designer.execute(brief)
            assert isinstance(model_obj, MathModel)
        except LLMError as exc:
            result.error = str(exc)
            return result

        # The agent may have raced an existing version; assign the next one.
        model_obj.candidate_id = candidate.id
        model_obj.version = self.database.latest_model_version(candidate.id) + 1

        stored_json = json.dumps(model_obj.model_dump(mode="json"), indent=2)
        self.database.save_math_model(
            candidate_id=candidate.id,
            model_json=stored_json,
            rationale=model_obj.rationale,
            version=model_obj.version,
        )

        candidate.transition(CandidateStatus.FORMALIZED)
        self.database.save_candidate(candidate)

        result.model = model_obj
        result.formalized = True
        return result

    def formalize_all(
        self,
        limit: int | None = None,
        only_status: CandidateStatus | None = CandidateStatus.PRIOR_ART_CHECKED,
    ) -> FormalizationSummary:
        """Formalize every candidate in the given state (§35 isolation)."""
        summary = FormalizationSummary()
        candidates = self.database.list_candidates(status=only_status, limit=limit)
        summary.attempted = len(candidates)
        for cand in candidates:
            result = self.formalize_candidate(cand)
            if result.formalized and result.model is not None:
                summary.formalized += 1
                summary.model_versions[cand.id] = result.model.version
            else:
                summary.failed += 1
                summary.errors[cand.id] = result.error
        return summary

    # -- offline fixture path ----------------------------------------------------

    def _formalize_one_fixture(self, candidate: Candidate) -> FormalizationResult:
        """Validate + store the fixture model for one candidate (offline path)."""
        brief = CandidateBrief.from_candidate(candidate)
        fixture = build_math_model_fixture(brief)
        try:
            model_obj = model_from_dict(fixture)  # full §2 validation
        except Exception as exc:  # fixture must always validate
            return FormalizationResult(
                candidate_id=candidate.id, error=f"fixture invalid: {exc}"
            )

        model_obj.candidate_id = candidate.id
        model_obj.version = self.database.latest_model_version(candidate.id) + 1
        stored_json = json.dumps(model_obj.model_dump(mode="json"), indent=2)
        self.database.save_math_model(
            candidate_id=candidate.id,
            model_json=stored_json,
            rationale=model_obj.rationale,
            version=model_obj.version,
        )
        candidate.transition(CandidateStatus.FORMALIZED)
        self.database.save_candidate(candidate)
        return FormalizationResult(
            candidate_id=candidate.id, model=model_obj, formalized=True
        )

    def formalize_all_fixtures(
        self,
        limit: int | None = None,
        only_status: CandidateStatus | None = CandidateStatus.PRIOR_ART_CHECKED,
        artifacts_dir: Path | None = None,
    ) -> FormalizationSummary:
        """Offline demo: same validation + storage path with fixture models.

        Uses the same MathModel validators and the same database writes as
        the LLM path; only the model *proposal* is deterministic.
        """
        summary = FormalizationSummary()
        candidates = self.database.list_candidates(status=only_status, limit=limit)
        summary.attempted = len(candidates)
        for cand in candidates:
            result = self._formalize_one_fixture(cand)
            if result.formalized and result.model is not None:
                summary.formalized += 1
                summary.model_versions[cand.id] = result.model.version
            else:
                summary.failed += 1
                summary.errors[cand.id] = result.error

        if artifacts_dir is not None:
            self._write_artifacts(artifacts_dir, summary)
        return summary

    def _write_artifacts(self, artifacts_dir: Path, summary: FormalizationSummary) -> None:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "attempted": summary.attempted,
            "formalized": summary.formalized,
            "failed": summary.failed,
            "model_versions": summary.model_versions,
        }
        path = artifacts_dir / "formalization-latest.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
