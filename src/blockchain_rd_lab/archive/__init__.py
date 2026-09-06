"""§26 public research archive: rejected-mechanisms index and archive tree.

Do not hide failed experiments — the rejected/ directory is a research
asset. The archive builder writes a deterministic Markdown index of every
rejected candidate with its rejection evidence (novelty class or §20
fatal flaw), plus a machine-readable JSON index for tooling.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.schemas import Candidate, CandidateStatus


class RejectedEntry(BaseModel):
    """One rejected mechanism with its rejection evidence."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str
    name: str
    category: str
    status: str
    rejected_because: str
    fatal_flaws: list[str] = Field(default_factory=list)
    novelty_class: str = ""


class ArchiveSummary(BaseModel):
    """Outcome of an archive build."""

    model_config = ConfigDict(validate_assignment=True)

    rejected_indexed: int = 0
    archive_path: str | None = None


def _rejection_reason(cand: Candidate) -> str:
    confirmed = [f for f in cand.fatal_flaws if f.confirmed]
    if confirmed:
        labels = ", ".join(sorted({f.category for f in confirmed}))
        return f"confirmed fatal flaw(s) ({labels}); §20 gate"
    if cand.novelty_class.value in ("clearly_existing", "very_similar_existing"):
        return (
            f"prior-art filter cut (novelty class {cand.novelty_class.value}); §7/§12"
        )
    # Not individually researched past class E, or a §7 funnel-overflow cut —
    # per-run details live in the filter outcome records (`lab filter`).
    return "research-funnel cut (class A/B or §7 overflow); see filter records"


def _supersede_reason(cand: Candidate) -> str:
    """Honest reason a SUPERSEDED candidate left the ranked corpus."""
    reasons: list[str] = []
    for flaw in cand.fatal_flaws:
        if flaw.confirmed and "evidence" in flaw.description.lower():
            reasons.append(flaw.description)
    if cand.innovation_claim and "successor" in cand.innovation_claim.lower():
        reasons.append(cand.innovation_claim)
    if reasons:
        return "; ".join(reasons[:2])
    return (
        "superseded by successor with corrected evidence "
        "(see innovation_claim lineage); §11"
    )


class ArchiveBuilder:
    """Builds the §26 public research archive from lab state."""

    def __init__(self, database: LabDatabase) -> None:
        self.database = database

    def rejected_entries(self) -> list[RejectedEntry]:
        out: list[RejectedEntry] = []
        for cand in self.database.list_candidates(limit=None):
            if cand.status is CandidateStatus.REJECTED:
                out.append(
                    RejectedEntry(
                        candidate_id=cand.id,
                        name=cand.name,
                        category=cand.category,
                        status=cand.status.value,
                        rejected_because=_rejection_reason(cand),
                        fatal_flaws=[
                            f.description
                            for f in cand.fatal_flaws
                            if f.confirmed
                        ],
                        novelty_class=cand.novelty_class.value,
                    )
                )
            elif cand.status is CandidateStatus.SUPERSEDED:
                out.append(
                    RejectedEntry(
                        candidate_id=cand.id,
                        name=cand.name,
                        category=cand.category,
                        status=cand.status.value,
                        rejected_because=_supersede_reason(cand),
                        fatal_flaws=[
                            f.description
                            for f in cand.fatal_flaws
                            if f.confirmed
                        ],
                        novelty_class=cand.novelty_class.value,
                    )
                )
        out.sort(key=lambda e: (e.category, e.name))
        return out

    def build(self, ideas_dir: Path) -> ArchiveSummary:
        """Write ideas/rejected/index.md + index.json (§26 research asset)."""
        entries = self.rejected_entries()
        rejected_dir = ideas_dir / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Rejected Mechanisms",
            "",
            "Failed experiments are a research asset (§26): they record what was "
            "considered and why it did not survive. Nothing here is hidden or "
            "deleted.",
            "",
            "| Candidate | Name | Category | Rejected because |",
            "|-----------|------|----------|------------------|",
        ]
        for e in entries:
            lines.append(
                f"| {e.candidate_id} | {e.name} | {e.category} | {e.rejected_because} |"
            )
        lines.append("")
        if any(e.fatal_flaws for e in entries):
            lines.append("## Confirmed Fatal Flaws (§20)")
            lines.append("")
            for e in entries:
                for flaw in e.fatal_flaws:
                    lines.append(f"- **{e.name}** ({e.candidate_id}): {flaw}")
            lines.append("")

        (rejected_dir / "index.md").write_text(
            "\n".join(lines).rstrip() + "\n", encoding="utf-8"
        )
        (rejected_dir / "index.json").write_text(
            json.dumps([e.model_dump(mode="json") for e in entries], indent=2),
            encoding="utf-8",
        )
        return ArchiveSummary(
            rejected_indexed=len(entries),
            archive_path=str(rejected_dir / "index.md"),
        )
