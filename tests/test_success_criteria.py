"""§42 definition-of-success tests: `lab pipeline --count 100` offline.

The spec's success criterion, executed for real: 100 generated →
prior-art → 20 serious candidates → models → simulations → attacks →
5 finalists → 1 recommended, with reproducible reports. The corpus
generator (§24's 20 domains) makes this runnable offline.
"""

from __future__ import annotations

import json

import pytest

from blockchain_rd_lab.testing.corpus import domain_names, generate_corpus

# ---------------------------------------------------------------------------
# §24 corpus generator
# ---------------------------------------------------------------------------


class TestCorpusGenerator:
    def test_generates_requested_count(self):
        batches = list(generate_corpus(100))
        total = sum(len(b.ideas) for b in batches)
        assert total == 100

    def test_covers_all_20_domains(self):
        assert len(domain_names()) == 20
        batches = list(generate_corpus(100))
        cats = {i.category for b in batches for i in b.ideas}
        # §24: the first research cycle spans all 20 source domains
        assert cats == set(domain_names())

    def test_names_are_unique(self):
        # 100 draws must not collide (dedup would eat the funnel otherwise)
        batches = list(generate_corpus(100))
        names = [i.name for b in batches for i in b.ideas]
        assert len(set(names)) == 100

    def test_deterministic(self):
        a = [i.name for b in generate_corpus(50) for i in b.ideas]
        b = [i.name for b in generate_corpus(50) for i in b.ideas]
        assert a == b

    def test_drafts_validate_against_schema(self):
        # §2: generated ideas pass the same IdeaDraft validation the LLM
        # route enforces (no schema bypass).
        for batch in generate_corpus(30):
            for idea in batch.ideas:
                assert len(idea.name) >= 3
                assert idea.description
                assert idea.core_mechanism
                assert (
                    "No substantially similar implementation was identified"
                    in idea.innovation_claim
                )  # §12 wording

    def test_batches_are_sized_for_the_pipeline(self):
        for batch in generate_corpus(37):
            assert 1 <= len(batch.ideas) <= 5


# ---------------------------------------------------------------------------
# §42 success test: the full funnel at count=100, offline
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestDefinitionOfSuccess:
    def test_count_100_full_funnel(self, tmp_path):
        """§42: one person runs count=100 and obtains the whole funnel."""
        from blockchain_rd_lab.database import LabDatabase
        from blockchain_rd_lab.pipeline import PipelineService
        from blockchain_rd_lab.testing.pipeline_fixtures import (
            build_pipeline_provider,
        )

        db = LabDatabase(tmp_path / "lab.db")
        db.create_all()
        service = PipelineService(
            build_pipeline_provider(),
            db,
            repo_root=tmp_path,
            token_budget=10_000_000,
        )
        summary = service.run(count=100, target=20, finalists=5)

        # All §34 stages ran
        stage_names = [s.stage for s in summary.stages]
        assert stage_names == [
            "discover", "research", "filter", "formalize", "simulate",
            "redteam", "improve", "retest", "score", "report",
        ]

        by_stage = {s.stage: s for s in summary.stages}

        # 100 mechanisms generated across §24's 20 domains
        assert by_stage["discover"].processed >= 100
        stored = by_stage["discover"].advanced
        assert stored >= 80, "dedup must not eat the corpus"

        # Prior-art research ran on every stored candidate
        assert by_stage["research"].processed == stored

        # §7 funnel cut: 20 serious candidates
        assert by_stage["filter"].advanced == 20

        # Formalized → simulated → attacked → improved → retested
        for stage in ("formalize", "simulate", "redteam", "improve", "retest"):
            assert by_stage[stage].advanced == 20, stage

        # 5 finalists → 1 recommended
        assert by_stage["score"].advanced == 5
        assert len(summary.finalists) == 5
        assert summary.recommended_id is not None

        # Every finalist is a real, promoted candidate
        rec = db.get_candidate(summary.recommended_id)
        assert rec is not None
        assert rec.overall_score > 0

        # Reproducible research reports (§42)
        assert (tmp_path / "reports" / "lab-latest.md").exists()
        dossiers = list((tmp_path / "reports" / "finalists").glob("*.md"))
        assert len(dossiers) == 5

        # §21 usage ledger + §26 rejected archive
        usage = json.loads((tmp_path / "reports" / "usage-latest.json").read_text())
        assert usage["calls"] > 0
        assert (tmp_path / "ideas" / "rejected" / "index.md").exists()

        # §24: the funnel spans many domains
        categories = {c.category for c in db.list_candidates(limit=None)}
        assert len(categories) >= 15
