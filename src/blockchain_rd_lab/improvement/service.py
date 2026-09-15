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

# §33 already-addressed matching: token overlap between a finding's text
# and a graph attack label/detail above this Jaccard threshold counts as
# "the same attack" (deterministic, §2).
_ADDRESSED_THRESHOLD = 0.5


def _tokens(text: str) -> set[str]:
    """Normalized keyword tokens (reuses the discovery normalizer rules)."""
    from blockchain_rd_lab.discovery.normalize import _STOPWORDS, _TOKEN_RE

    return {
        t
        for t in _TOKEN_RE.findall(text.lower())
        if t not in _STOPWORDS and len(t) >= 4
    }


def _matches_any(finding: dict[str, str], attacks: list[dict[str, str]]) -> bool:
    """True when the finding is token-similar to an already-addressed attack."""
    tokens = _tokens(finding.get("vector", ""))
    if not tokens:
        return False
    for attack in attacks:
        other = _tokens(attack.get("text", ""))
        if not other:
            continue
        overlap = len(tokens & other) / len(tokens | other)
        if overlap >= _ADDRESSED_THRESHOLD:
            return True
    return False


def _fixable_findings(reports: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Every attack vector worth fixing, strongest attention first.

    Rows carry `report_json` (canonical report dump), not a parsed dict.

    r36 (the r35 principle applied to the §34 fix loop): the agent's
    profitable_for_attacker boolean no longer FILTERS which vectors the
    improver sees — an agent asserting unprofitable must not be able to
    steer the fix loop away from a surface either. Every vector enters;
    profitable-asserted ones are ordered FIRST (attention allocation,
    not suppression) and each row carries the agent's profitability
    hypothesis so the improver prompt can state it honestly.
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
                profitable = bool(v.get("profitable_for_attacker"))
                findings.append(
                    {
                        "agent": agent,
                        "vector": v.get("description", "unspecified attack"),
                        # r36: honest ordering metadata — profitable-asserted
                        # first (attention), never a filter.
                        "profitable": "true" if profitable else "false",
                    }
                )
    findings.sort(key=lambda f: f["profitable"], reverse=True)
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

    def _graph(self):
        """Build the §33 knowledge graph over the current lab database."""
        from blockchain_rd_lab.graph.builder import GraphBuilder

        return GraphBuilder(self.database).build()

    def _addressed_attacks(
        self, candidate_id: str, version: int
    ) -> list[dict[str, str]]:
        """Attacks the CURRENT model version already ADDRESSES (§33 edges).

        The graph records improvement→attack ADDRESSES edges from §34 fix
        claims; a finding that matches an attack addressed at (or below)
        the current version is converged — the improver must not
        re-patch it (the v3 honesty rule, now deterministic).
        """
        from blockchain_rd_lab.graph import EdgeKind, NodeKind

        graph = self._graph()
        out: list[dict[str, str]] = []
        for e in graph.edges:
            if e.kind is not EdgeKind.ADDRESSES:
                continue
            src = graph.node_by_id(e.source)
            tgt = graph.node_by_id(e.target)
            if src is None or tgt is None or src.kind is not NodeKind.IMPROVEMENT:
                continue
            # Only this candidate's fixes, at or below the current version.
            if not src.id.startswith(candidate_id):
                continue
            try:
                fix_version = int(src.id.rsplit("v", 1)[-1])
            except ValueError:
                continue
            if fix_version > version:
                continue
            detail = str(tgt.meta.get("detail", ""))
            out.append({"text": tgt.label + " " + detail})
        return out

    def _smoke_test(self, model: MathModel) -> str | None:
        """One deterministic base-scenario step; None if simulatable.

        §14/§2: the §13 structural gate alone cannot see runtime
        unsimulatability — declared-but-unfed inputs, dependency cycles,
        missing initial values all pass §13 and then kill RETEST at step 0
        (terminal FAILED). This gate keeps failures at IMPROVE where the
        improver can resubmit.
        """
        try:
            from blockchain_rd_lab.simulation import MechanismSimulation

            sim = MechanismSimulation(model)
            state = sim.initial_state()
            # The battery's base row is exactly {"X_t": x, "dX_t": dx} with
            # model parameters injected alongside; any other declared input
            # must derive itself or the model fails here, deterministically,
            # with the missing symbol named.
            row: dict[str, float | list[float]] = {
                "X_t": 1000.0,
                "dX_t": 1.0,
                **{p.symbol: p.default for p in model.parameters},
                **state,
            }
            sim.transition(row)
            return None
        except Exception as exc:
            return f"{type(exc).__name__}: {exc}"

    def _prior_fixes(self, candidate_id: str) -> list:
        """Graph-derived how-similar-attacks-were-fixed records (§32 reuse)."""
        from blockchain_rd_lab.graph.builder import GraphBuilder
        from blockchain_rd_lab.improvement.agents import PriorFix

        builder = GraphBuilder(self.database)
        graph = builder.build()
        out: list[PriorFix] = []
        for fix in builder.attack_fixes(graph):
            if fix.fixed_by is None:
                continue
            if fix.attacked_idea == candidate_id:
                continue  # own history is handled by the addressed filter
            version = 1
            if fix.fixed_by.rsplit("v", 1)[-1].isdigit():
                version = int(fix.fixed_by.rsplit("v", 1)[-1])
            out.append(
                PriorFix(
                    candidate_id=fix.attacked_idea,
                    attack=fix.attack_label,
                    fix_summary=fix.fix_summary or "",
                    model_version=version,
                )
            )
        return out[:5]  # bounded context

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
                outcome.rejected_reason = "no attack vectors to fix"
                return outcome

            # §33→§34: graph-derived prior fixes for similar attacks (§32
            # reuse: consult how a similar attack was answered before) +
            # deterministic already-addressed filtering (a finding whose
            # attack the CURRENT model version already ADDRESSES is not
            # re-patched — the convergence rule, enforced by code not LLM
            # judgment, §2).
            prior_fixes = self._prior_fixes(candidate.id)
            current_version = int(json.loads(model_dump).get("version", 1))
            addressed = self._addressed_attacks(candidate.id, current_version)
            fresh = [
                f for f in findings if not _matches_any(f, addressed)
            ]
            if not fresh:
                outcome.rejected_reason = (
                    f"all findings already addressed by model "
                    f"v{current_version} (§33 convergence rule)"
                )
                return outcome

            brief = CandidateBrief.from_candidate(candidate)
            current = json.loads(model_dump)

            if offline:
                payload = build_improvement_fixture(brief, current, fresh)
                proposal = ImprovementProposal.model_validate(payload)
            else:
                agent_input = ImprovementInput(
                    brief=brief,
                    current_model=current,
                    attack_findings=fresh,
                    prior_fixes=prior_fixes,
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

            # §14 simulatability smoke test (deterministic, §2): one step of
            # the battery's base scenario at parameter defaults. A model can
            # pass §13 structure and still be unsimulatable (declared inputs
            # the series never feeds, dependency cycles, missing initial
            # values) — catching it HERE keeps the candidate RED_TEAM with
            # the improver able to resubmit, instead of RETEST → FAILED
            # (terminal) on a structurally valid but unrunnable patch.
            smoke = self._smoke_test(patched)
            if smoke is not None:
                raise LLMError(
                    f"patched model is not simulatable: {smoke} — fix the "
                    f"model (every declared input needs a value in the "
                    f"battery series or a derivation equation; equations "
                    f"must not cycle)"
                )

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
