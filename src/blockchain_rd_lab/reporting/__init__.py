"""Phase 7 schemas: research reports (§23).

Reports are ASSEMBLED BY CODE from stored validated evidence — scores,
math models, §21 simulation records, adversarial verdicts, ranking. No
report-writer LLM exists: the human-facing artifact is deterministic and
reproducible from the database alone (§2 taken to its conclusion).

§23 finalist dossier sections are fixed; sections with no stored evidence
render as honest "not yet researched" notes rather than being dropped
(§29: never hide missing work).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReportSection(BaseModel):
    """One §23 dossier section: title + markdown body."""

    model_config = ConfigDict(frozen=True)

    title: str
    body: str = ""


class CandidateDossier(BaseModel):
    """Full §23 report for one candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str
    name: str
    category: str
    status: str
    overall_score: float | None = None
    rank: int | None = None
    recommended: bool = False
    fatal_flaws: list[str] = Field(default_factory=list)
    sections: list[ReportSection] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Render the dossier as a §23 Markdown research report."""
        lines: list[str] = [f"# Research Dossier: {self.name}", ""]
        meta = [f"- **Candidate ID:** {self.candidate_id}", f"- **Category:** {self.category}"]
        if self.overall_score is not None:
            meta.append(f"- **Overall score:** {self.overall_score:.4f}")
        if self.rank is not None:
            suffix = " (recommended)" if self.recommended else ""
            meta.append(f"- **Rank:** {self.rank}{suffix}")
        meta.append(f"- **Status:** {self.status}")
        if self.fatal_flaws:
            meta.append(f"- **Confirmed fatal flaws:** {len(self.fatal_flaws)}")
        lines.extend(meta)
        lines.append("")
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.body or "_(no recorded evidence yet)_")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


class LabReport(BaseModel):
    """Lab-wide funnel summary report (§7, §23 reports/ structure)."""

    model_config = ConfigDict(frozen=True)

    generated_at: str
    candidates_total: int = 0
    status_counts: dict[str, int] = Field(default_factory=dict)
    finalists: list[str] = Field(default_factory=list)  # candidate ids
    recommended_id: str | None = None
    gate_rejections: int = 0
    ranking_table: list[tuple[int, str, str, float]] = Field(default_factory=list)

    def to_markdown(self) -> str:
        counts = "\n".join(
            f"- **{status}:** {n}" for status, n in sorted(self.status_counts.items())
        )
        ranking = "\n".join(
            f"| {rank} | {cid} | {name} | {score:.4f} |"
            for rank, cid, name, score in self.ranking_table
        )
        recommended = self.recommended_id or "_(none yet — run `lab rank`)_"
        finalist_list = ", ".join(self.finalists) or "_(none)_"
        return (
            "# Lab Research Report\n\n"
            f"Generated: {self.generated_at}\n\n"
            "## Funnel Status (§7)\n\n"
            f"- **Total candidates:** {self.candidates_total}\n"
            f"{counts}\n\n"
            "## Finalists\n\n"
            f"{finalist_list}\n\n"
            "## Recommended Candidate (§7)\n\n"
            f"{recommended}\n\n"
            "## Ranking\n\n"
            "| # | Candidate | Name | Score |\n"
            "|---|-----------|------|-------|\n"
            f"{ranking}\n"
        )


class ReportOutcome(BaseModel):
    """Result of a report run (CLI table + artifact provenance)."""

    model_config = ConfigDict(validate_assignment=True)

    dossiers_written: list[str] = Field(default_factory=list)  # file paths
    lab_report_path: str | None = None
    recommended_id: str | None = None
