"""Improvement orchestration service (§3/§34 loop).

Deterministic flow per candidate:
1. Resolve the candidate (must be RED_TEAM status — the §11 input state).
2. Load the latest adversarial reports; extract fixable findings
   (profitable attacks from the strongest agent reports).
3. Ask the Improvement Agent for a patched model v(n+1).
4. Validate the patched model with the SAME MathModel integrity checks
   as Phase 3 (§13); reject anything that does not validate — the LLM
   never bypasses validation (§2).
5. Store the new model version (append-only) and transition
   RED_TEAM → IMPROVEMENT → RETEST (§11).

Failures are isolated (§35): one candidate's error never stops the run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from blockchain_rd_lab.agents.base import LLMError, LLMProvider
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.formalization import MathModel
from blockchain_rd_lab.improvement import (
    ImprovementOutcome,
    ImprovementProposal,
    ImprovementRunSummary,
)
from blockchain_rd_lab.improvement.agents import (
    ImprovementAgent,
    ImprovementInput,
    build_improvement_fixture,
)
from blockchain_rd_lab.research import CandidateBrief
from blockchain_rd_lab.schemas import Candidate, CandidateStatus

# Agents whose findings the improver must address first.
_PRIORITY = ("red_team", "game_theory", "security", "oracle")


def _fixable_findings(reports: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Profitable attacks worth fixing, strongest agent first.

    Rows carry `report_json` (canonical report dump), not a parsed dict.
    """
    import json as _json

    findings: list[dict[str, str]] = []
    for agent in _PRIORITY:
        for row in reports:
            if row.get("agent_name") != agent:
                continue
            raw = row.get("report_json")
            report = _json.loads(raw) if isinstance(raw, str) else (raw or {})
            vectors = report.get("attack_vectors") or report.get("manipulation_vectors")
            for v in vectors or []:
                if v.get("profitable_for_attacker"):
                    findings.append(
                        {
                            "agent": agent,
                            "vector": v.get("description", "unspecified attack"),
                        }
                    )
    return findings


class ImprovementService:
    """Runs the §34 improve stage over red-teamed candidates."""

    def __init__(
        self,
        provider: LLMProvider,
        database: LabDatabase,
        artifacts_dir: Path | None = None,
    ) -> None:
        self.provider = provider
        self.database = database
        self.artifacts_dir = artifacts_dir
        self.agent = ImprovementAgent(provider, database)

    # -- one candidate -----------------------------------------------------------

    def improve_candidate(
        self, candidate: Candidate, *, offline: bool = False
    ) -> ImprovementOutcome:
        outcome = ImprovementOutcome(candidate_id=candidate.id)
        try:
            if candidate.status is not CandidateStatus.RED_TEAM:
                outcome.rejected_reason = (
                    f"status {candidate.status.value} is not red_team"
                )
                return outcome

            model_dump = self.database.get_latest_math_model(candidate.id)
            if model_dump is None:
                outcome.rejected_reason = "no formal model to patch"
                return outcome

            reports = self.database.list_redteam_results(candidate_id=candidate.id)
            findings = _fixable_findings(reports)
            if not findings:
                outcome.rejected_reason = "no profitable attacks to fix"
                return outcome

            brief = CandidateBrief.from_candidate(candidate)
            current = json.loads(model_dump)

            if offline:
                payload = build_improvement_fixture(brief, current, findings)
                proposal = ImprovementProposal.model_validate(payload)
            else:
                agent_input = ImprovementInput(
                    brief=brief, current_model=current, attack_findings=findings
                )
                output = self.agent.execute(agent_input)[0]
                if not isinstance(output, ImprovementProposal):
                    raise LLMError("improver returned unexpected schema")
                proposal = output

            # Deterministic gate: validate the patched model (§13/§2).
            patched = MathModel.model_validate(proposal.model)
            if patched.candidate_id != candidate.id:
                raise LLMError("patched model does not reference this candidate")
            if patched.version <= int(current.get("version", 1)):
                raise LLMError("patched model must be a new version")

            # Store append-only + transition §11.
            self.database.save_math_model(
                candidate_id=candidate.id,
                model_json=patched.model_dump_json(),
                rationale=proposal.summary,
                version=patched.version,
            )
            candidate.transition(CandidateStatus.IMPROVEMENT)
            self.database.save_candidate(candidate)
            candidate.transition(CandidateStatus.RETEST)
            self.database.save_candidate(candidate)

            outcome.improved = True
            outcome.new_version = patched.version
            outcome.attacks_addressed = sum(
                1 for a in proposal.addressed_attacks if a.fixes_attack
            )
        except LLMError as exc:
            outcome.errors.append(str(exc))
        except Exception as exc:  # §35: isolate, never kill the run
            outcome.errors.append(f"{type(exc).__name__}: {exc}")
        return outcome

    # -- batch -------------------------------------------------------------------

    def improve_all(
        self,
        limit: int | None = None,
        only_status: CandidateStatus | None = CandidateStatus.RED_TEAM,
        offline: bool = False,
    ) -> ImprovementRunSummary:
        summary = ImprovementRunSummary()
        candidates = self.database.list_candidates(status=only_status, limit=limit)
        summary.attempted = len(candidates)
        for cand in candidates:
            outcome = self.improve_candidate(cand, offline=offline)
            summary.per_candidate.append(outcome)
            if outcome.improved:
                summary.improved += 1
            elif outcome.errors:
                summary.errors += 1
            elif outcome.rejected_reason:
                summary.rejected += 1
        return summary
