"""Phase 7 orchestration: assemble research reports from stored evidence (§23).

The builder reads ONLY the database (candidates, dimension scores, math
models, §21 experiment records, red-team reports, ranking) and renders
§23 finalist dossiers plus a lab-wide funnel report. Deterministic by
construction: same database state → byte-identical reports.

§7 tail: among finalists, the single recommended candidate is the rank-1
finalist (deterministic; ties resolve via the ranking's stable name
order).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.reporting import (
    CandidateDossier,
    LabReport,
    ReportOutcome,
    ReportSection,
)
from blockchain_rd_lab.schemas import Candidate, CandidateStatus
from blockchain_rd_lab.scoring import ScoringEngine

# §23 finalist dossier section titles (fixed order).
SECTIONS = (
    "Executive Summary",
    "Problem",
    "Mechanism",
    "Mathematical Model",
    "Economic Analysis",
    "Game Theory",
    "Oracle Design",
    "Security",
    "Simulation",
    "Historical Analysis",
    "Prior Art",
    "Competitors",
    "Market",
    "Technical Architecture",
    "Regulatory Risks",
    "MVP",
    "Risks",
    "Open Questions",
    "Recommendation",
)


class ReportBuilder:
    """Assembles dossiers and lab reports from validated stored data."""

    def __init__(self, database: LabDatabase) -> None:
        self.database = database

    # -- per-candidate evidence gathering ------------------------------------

    def _score_lines(self, candidate: Candidate) -> list[str]:
        if not candidate.scores:
            return ["No dimension scores recorded yet."]
        lines = []
        for dim in sorted(candidate.scores):
            s = candidate.scores[dim]
            lines.append(
                f"- **{dim}**: {s.score:.2f} "
                f"({s.evidence_level}; confidence {s.confidence:.2f})"
            )
        return lines

    def _dimension_lines(
        self, candidate: Candidate, dims: tuple[str, ...],
    ) -> list[str]:
        """Score lines for ONE section's own dimensions (r27 audit
        fix #2: Economic Analysis and Market rendered byte-identical
        because both dumped the full score list).

        r27 fix (regression caught by the existing suite): imputed
        dimensions (no authored agent evidence -> §19 5.0 floor)
        were silently dropped. They now render with the IMPUTED
        flag — the dossier must disclose the floor, not hide it."""
        if not candidate.scores:
            return ["No dimension scores recorded yet."]
        lines = []
        for dim in dims:
            s = candidate.scores.get(dim)
            if s is not None:
                lines.append(
                    f"- **{dim}**: {s.score:.2f} "
                    f"({s.evidence_level}; confidence {s.confidence:.2f})"
                )
                continue
            # no authored row: §19 imputes at the floor — render the
            # imputation, never silence it
            res = ScoringEngine().score(candidate)
            for d in res.dimensions:
                if d.dimension == dim:
                    lines.append(
                        f"- **{dim}**: {d.score:.2f} "
                        f"(IMPUTED at the 5.0 floor; no authored "
                        "agent evidence, §19)"
                    )
                    break
        return lines or ["No scores recorded for these dimensions yet."]

    def _math_model_section(self, candidate: Candidate) -> str:
        dump = self.database.get_latest_math_model(candidate.id)
        if dump is None:
            return "No formal model stored yet (run `lab formalize`)."
        model = json.loads(dump)
        lines = []
        for var in model.get("variables", []):
            role = var.get("role", "?")
            lines.append(
                f"- `{var['symbol']}` ({role}, {var.get('units', 'unitless')}): "
                f"{var.get('description', '')}"
            )
        lines.append("")
        for eq in model.get("equations", []):
            lines.append(f"- `{eq['expression']}` — {eq.get('description', '')}")
        params = model.get("parameters", [])
        if params:
            lines.append("")
            lines.append("**Parameters:** " + ", ".join(
                f"{p['name']} ∈ [{p['min_value']}, {p['max_value']}] "
                f"(default {p['default']})"
                for p in params
            ))
        questions = model.get("open_questions", [])
        if questions:
            lines.append("")
            lines.append("**Open questions (§13):** " + "; ".join(questions))
        assumptions = model.get("assumptions", [])
        critical = [a for a in assumptions if a.get("critical")]
        if critical:
            lines.append("")
            lines.append(
                "**Critical assumptions:** "
                + "; ".join(a.get("statement", "") for a in critical)
            )
        return "\n".join(lines)

    def _simulation_section(self, candidate: Candidate) -> str:
        experiments = list(self.database.iter_experiments(candidate.id))
        if not experiments:
            return "No simulation runs recorded yet (run `lab simulate`)."
        lines = []
        for exp in experiments:
            results = exp.results if isinstance(exp.results, dict) else {}
            summary_bits = []
            for key in ("mean_final", "p5_final", "p95_final", "failures"):
                if key in results:
                    summary_bits.append(f"{key}={results[key]}")
            scenarios = results.get("scenarios") if "scenarios" in results else None
            if isinstance(scenarios, dict):
                summary_bits.append(f"{len(scenarios)} §15 scenarios")
            lines.append(
                f"- **{exp.experiment_id}** (seed {exp.seed}, "
                f"{exp.simulation_version}): "
                + (", ".join(summary_bits) if summary_bits else "results recorded")
            )
        lines.append("")
        lines.append(
            "All runs are reproducible from the stored seed, parameters, and "
            "git commit (§21)."
        )
        return "\n".join(lines)

    def _verdict_line(self, candidate: Candidate) -> str:
        """The overall red-team verdict from the LATEST round (r27
        audit fix #1: the dossier once quoted round 1 of 3 —
        selection bug, fixed by latest-per-agent overwrite)."""
        rows = self.database.list_redteam_results(candidate.id)
        rt = [r for r in rows if r["agent_name"] == "red_team"]
        if not rt:
            return ""
        latest = max(rt, key=lambda r: str(r.get("created_at", "")))
        report = json.loads(latest["report_json"])
        return (
            f"- **Red Team verdict:** {report['verdict']}"
            f" (strongest attack: {report['strongest_attack'][:200]}…)"
        )

    def _redteam_section(
        self, candidate: Candidate, agent_focus: str | None = None,
    ) -> str:
        """§23 adversarial sections, assembled from the LATEST
        red-team round per agent (r27 audit fix: a dict comprehension
        over all rounds silently kept the EARLIEST record — the
        dossier quoted the superseded v1 'vulnerable' verdict while
        the release package carried the final 'survives')."""
        rows = self.database.list_redteam_results(candidate.id)
        if not rows:
            return "No adversarial review recorded yet (run `lab redteam`)."

        def sort_key(r: dict[str, Any]) -> str:
            return str(r.get("created_at", ""))

        latest: dict[str, dict[str, Any]] = {}
        for r in sorted(rows, key=sort_key):
            latest[r["agent_name"]] = r  # later rounds overwrite

        lines: list[str] = []

        if agent_focus is None:
            rt = latest.get("red_team")
            if rt:
                report = json.loads(rt["report_json"])
                lines.append(
                    f"- **Red Team verdict:** {report['verdict']}"
                    f" (strongest attack: {report['strongest_attack'][:200]}…)"
                )
                if len(rows) > len(latest):
                    lines.append(
                        f"- {len(rows)} adversarial reports across "
                        f"{len(latest)} agent(s), {len(latest)} latest "
                        "shown (earlier rounds superseded; full history "
                        "in the bundle's redteam-history.json)"
                    )
        else:
            row = latest.get(agent_focus)
            if row:
                report = json.loads(row["report_json"])
                vectors = report.get(
                    "attack_vectors", report.get("manipulation_vectors", [])
                )
                lines.append(
                    f"- **{agent_focus}:** {len(vectors)} attack vector(s) "
                    f"recorded; evidence level "
                    f"{report.get('evidence_level', '?')}"
                )
                summary = report.get("summary") or report.get("rationale")
                if summary:
                    lines.append(f"- {str(summary)[:300]}")

        if candidate.fatal_flaws:
            confirmed = [f for f in candidate.fatal_flaws if f.confirmed]
            lines.append(
                f"- **Confirmed fatal flaws:** {len(confirmed)} (§20 gate applied)"
            )
        return "\n".join(lines) if lines else "Adversarial rows present."

    def _prior_art_section(self, candidate: Candidate) -> str:
        rows = self.database.list_prior_art(candidate.id)
        if not rows:
            return "No prior-art research recorded yet (run `lab research`)."
        lines = []
        for row in rows[:5]:
            lines.append(f"- Queries: {row['query'][:200]}")
            lines.append(f"  Class: {row['similarity_class']}")
        return "\n".join(lines)

    # -- dossier ----------------------------------------------------------------

    def build_dossier(
        self,
        candidate: Candidate,
        rank: int | None = None,
        recommended: bool = False,
    ) -> CandidateDossier:
        """Assemble the full §23 dossier from stored evidence."""
        bodies: dict[str, str] = {
            "Executive Summary": (
                f"**{candidate.name}** ({candidate.category}) currently holds "
                f"status **{candidate.status.value}**"
                + (
                    f" with an overall deterministic score of "
                    f"**{candidate.overall_score:.4f}**"
                    if candidate.overall_score is not None
                    else " and has not been scored yet"
                )
                + "."
                + (
                    " All evidence below is drawn from validated, stored agent "
                    "and simulation records; nothing in this report is "
                    "free-form LLM narrative (§2)."
                )
            ),
            "Problem": candidate.problem or "No problem statement recorded yet.",
            "Mechanism": candidate.core_mechanism,
            "Mathematical Model": self._math_model_section(candidate),
            "Economic Analysis": "\n".join(
                self._dimension_lines(
                    candidate,
                    ("novelty", "economic_coherence",
                     "capital_efficiency"))),
            "Game Theory": (
                # the OVERALL red-team verdict (latest round) leads
                # this section — r27 audit fix #1: the quote must be
                # the final round's, never the earliest
                self._verdict_line(candidate)
                + "\n"
                + "\n".join(self._dimension_lines(
                    candidate, ("game_theory",)))
                + "\n"
                + self._redteam_section(
                    candidate, agent_focus="game_theory")
            )
            if self.database.list_redteam_results(candidate.id)
            else "\n".join(self._dimension_lines(
                candidate, ("game_theory",)))
                or "No game-theoretic review yet.",
            "Oracle Design": (
                "\n".join(self._dimension_lines(
                    candidate, ("oracle_feasibility",)))
                + "\n"
                + (
                    "This mechanism requires external data (oracle)."
                    if candidate.oracle_required
                    else "No external data dependency declared."
                )
                + " See Security and adversarial sections for "
                "manipulation analysis."
            ),
            "Security": (
                "\n".join(self._dimension_lines(
                    candidate, ("security",)))
                + "\n"
                + self._redteam_section(
                    candidate, agent_focus="security")
            ),
            "Simulation": self._simulation_section(candidate),
            "Historical Analysis": (
                "Historical replay ran on synthetic anchor series (Phase 4); "
                "real-dataset historical analysis is planned with the data phase."
            ),
            "Prior Art": self._prior_art_section(candidate),
            "Competitors": "See Prior Art; competitor synthesis pending real research.",
            "Market": "\n".join(
                self._dimension_lines(
                    candidate,
                    ("market_demand", "network_effects",
                     "communication", "viral_potential"))),
            "Technical Architecture": (
                "\n".join(self._dimension_lines(
                    candidate, ("technical_feasibility",)))
                + "\nBlockchain required: "
                + ("yes" if candidate.blockchain_required else "no")
                + "; token required: "
                + ("yes" if candidate.token_required else "no")
                + ". Detailed architecture arrives with the Blockchain "
                "Architect review (future phase)."
            ),
            "Regulatory Risks": (
                "Regulatory review is pending. This lab does not provide "
                "legal advice; risks are flagged for professional review (§9)."
            ),
            "MVP": "MVP scoping pending; see Open Questions.",
            "Risks": "\n".join(
                f"- {f.description}" for f in candidate.fatal_flaws
            )
            or "No fatal flaws recorded. Residual risks live in the "
            "adversarial sections above.",
            "Open Questions": "See the Mathematical Model section's §13 open "
            "questions; unresolved items remain HYPOTHESIS-level (§29).",
            "Recommendation": (
                "**Recommended candidate (§7).** Rank 1 among finalists; "
                "selected deterministically from the ranking."
                if recommended
                else "Not the recommended candidate this cycle. See the lab "
                "report for the current recommendation."
            ),
        }
        sections = [ReportSection(title=t, body=bodies.get(t, "")) for t in SECTIONS]
        return CandidateDossier(
            candidate_id=candidate.id,
            name=candidate.name,
            category=candidate.category,
            status=candidate.status.value,
            overall_score=candidate.overall_score,
            rank=rank,
            recommended=recommended,
            fatal_flaws=[f.description for f in candidate.fatal_flaws if f.confirmed],
            sections=sections,
        )

    # -- lab report --------------------------------------------------------------

    def build_lab_report(self) -> LabReport:
        candidates = self.database.list_candidates(limit=None)
        counts: dict[str, int] = {}
        for c in candidates:
            counts[c.status.value] = counts.get(c.status.value, 0) + 1

        finalists = [c for c in candidates if c.status is CandidateStatus.FINALIST]
        finalists.sort(key=lambda c: (-(c.overall_score or 0.0), c.name))
        finalist_ids = [c.id for c in finalists]

        # §7: one recommended candidate = rank-1 finalist (deterministic).
        recommended_id = finalist_ids[0] if finalist_ids else None

        scored = [
            c
            for c in candidates
            if c.overall_score is not None
            and c.status in (CandidateStatus.SCORED, CandidateStatus.FINALIST)
        ]
        scored.sort(key=lambda c: (-(c.overall_score or 0.0), c.name))
        table = [
            (i, c.id, c.name, c.overall_score or 0.0)
            for i, c in enumerate(scored, start=1)
        ]

        gate = sum(
            1
            for c in candidates
            if c.has_confirmed_fatal_flaw
            and c.status is CandidateStatus.REJECTED
        )

        return LabReport(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            candidates_total=len(candidates),
            status_counts=counts,
            finalists=finalist_ids,
            recommended_id=recommended_id,
            gate_rejections=gate,
            ranking_table=table,
        )

    # -- artifact writing ----------------------------------------------------------

    def write_reports(
        self,
        reports_dir: Path,
        include_dossiers: bool = True,
    ) -> ReportOutcome:
        """Write lab report + one dossier per finalist under reports/."""
        outcome = ReportOutcome()
        finalists_dir = reports_dir / "finalists"
        if include_dossiers:
            finalists_dir.mkdir(parents=True, exist_ok=True)
            candidates = self.database.list_candidates(limit=None)
            ranked = sorted(
                [c for c in candidates if c.status is CandidateStatus.FINALIST],
                key=lambda c: (-(c.overall_score or 0.0), c.name),
            )
            for i, cand in enumerate(ranked, start=1):
                dossier = self.build_dossier(
                    cand, rank=i, recommended=(i == 1)
                )
                path = finalists_dir / f"{cand.id}.md"
                path.write_text(dossier.to_markdown(), encoding="utf-8")
                outcome.dossiers_written.append(str(path))

        lab = self.build_lab_report()
        lab_path = reports_dir / "lab-latest.md"
        lab_path.write_text(lab.to_markdown(), encoding="utf-8")
        outcome.lab_report_path = str(lab_path)
        outcome.recommended_id = lab.recommended_id
        return outcome
