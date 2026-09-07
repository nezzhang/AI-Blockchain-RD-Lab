"""Regression: sourceless PriorArtReports still persist evidence rows.

The r8 combination round discovered `_persist_prior_art` saved rows only
inside the `for source in report.sources` loop — reports citing zero
sources silently persisted nothing, leaving ranked candidates with prior
art scores but no §12 evidence trail. The fix decouples row persistence
from source count (one row per source; sourceless reports still record
queries/findings/similar mechanisms/conclusion).
"""

from __future__ import annotations

from blockchain_rd_lab.agents.providers import MockLLMProvider
from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.research import PriorArtReport
from blockchain_rd_lab.research.service import ResearchService


class _Cid:
    """Bare provider shim: research_candidate needs no real agent here."""

    def __init__(self, report: PriorArtReport) -> None:
        self.report = report

    name = "shim"
    model_tier = None  # type: ignore[assignment]
    temperature = 0.0


class _ReplayAgent:
    """Mimics PriorArtAgent.execute returning the canned report."""

    name = "prior_art"
    role = "test"
    model_tier = None  # type: ignore[assignment]
    temperature = 0.0

    def __init__(self, report: PriorArtReport) -> None:
        self.report = report

    def build_prompt(self, payload):
        return []

    def execute(self, payload):
        return self.report, None


def _sourceless_report() -> PriorArtReport:
    return PriorArtReport.model_validate(
        {
            "novelty_class": "adjacent_mechanism",
            "similar_mechanisms": [],
            "search_queries": ["oracle fee fallback", "prediction market rails"],
            "sources": [],
            "findings": ["no substantially similar implementation found"],
            "confidence": 0.6,
            "conclusion": "No substantially similar implementation was "
            "identified in the searched sources.",
        }
    )


def test_sourceless_report_persists_evidence(tmp_path) -> None:
    db = LabDatabase(tmp_path / "lab.db")
    db.create_all()

    from blockchain_rd_lab.schemas import Candidate

    cand = Candidate(
        name="Sourceless Research Candidate",
        category="test",
        description="sourceless report persistence regression",
        core_mechanism="none",
        problem="none",
        innovation_claim="none",
        inputs=[],
        outputs=[],
    )
    db.save_candidate(cand)

    provider = MockLLMProvider()
    service = ResearchService(provider, db)
    # Directly exercise the persistence contract, bypassing agent plumbing.
    service._persist_prior_art(cand.id, _sourceless_report())

    rows = db.list_prior_art(cand.id)
    assert rows, "sourceless PriorArtReport must still record its evidence"
    assert len(rows) == 1
    assert rows[0]["similarity_class"] == "adjacent_mechanism"
    assert "oracle fee fallback" in rows[0]["query"]
    assert "no substantially similar" in rows[0]["finding"]


def test_report_with_sources_persists_one_row_per_source(tmp_path) -> None:
    db = LabDatabase(tmp_path / "lab.db")
    db.create_all()

    from blockchain_rd_lab.schemas import Candidate

    cand = Candidate(
        name="Sourced Research Candidate",
        category="test",
        description="per-source persistence",
        core_mechanism="none",
        problem="none",
        innovation_claim="none",
        inputs=[],
        outputs=[],
    )
    db.save_candidate(cand)

    report = PriorArtReport.model_validate(
        {
            "novelty_class": "adjacent_mechanism",
            "similar_mechanisms": [],
            "search_queries": ["oracle fee fallback", "prediction market rails"],
            "sources": [
                {
                    "title": "Chainlink docs",
                    "url": "https://docs.chain.link",
                    "source_type": "protocol_doc",
                },
                {
                    "title": "UMA optimistic oracle",
                    "url": "https://uma.xyz",
                    "source_type": "protocol_doc",
                },
            ],
            "findings": ["no substantially similar implementation found"],
            "confidence": 0.6,
            "conclusion": "No substantially similar implementation was "
            "identified in the searched sources.",
        }
    )
    provider = MockLLMProvider()
    service = ResearchService(provider, db)
    service._persist_prior_art(cand.id, report)

    rows = db.list_prior_art(cand.id)
    assert len(rows) == 2
    assert all(r["query"].startswith("oracle fee fallback") for r in rows)
    assert {r["source_id"] for r in rows} != {None}
