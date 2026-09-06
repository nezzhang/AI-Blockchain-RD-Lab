"""§33 knowledge graph tests: extraction, determinism, reuse queries.

The graph is a DERIVED, deterministic view of stored evidence (§2):
rebuilding over the same database yields the identical graph.
"""

from __future__ import annotations

import json

from blockchain_rd_lab.graph import (
    AttackFix,
    EdgeKind,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeKind,
)
from blockchain_rd_lab.graph.builder import GraphBuilder

# ---------------------------------------------------------------------------
# Test-corpus helpers: store one full §33 chain in a scratch DB
# ---------------------------------------------------------------------------


def store_chain(db, cid: str = "cand-graph") -> str:
    """One idea with: source citation, model v1+v2 (improvement),
    experiment records, and adversarial reports with a profitable attack."""
    from blockchain_rd_lab.schemas import Candidate, CandidateStatus

    cand = Candidate(
        id=cid,
        name="Graph Test Mechanism",
        category="monetary",
        description="Supply follows an anchor with caps.",
        core_mechanism="S_t1 = S_t * (1 + clip(alpha * dX_t / X_t, f, c)).",
    )
    db.save_candidate(cand)
    for target in (
        CandidateStatus.RESEARCHING,
        CandidateStatus.PRIOR_ART_CHECKED,
        CandidateStatus.FORMALIZED,
        CandidateStatus.SIMULATING,
        CandidateStatus.RED_TEAM,
    ):
        cand.transition(target)
        db.save_candidate(cand)

    # source + prior-art citation
    from blockchain_rd_lab.schemas import ExperimentRecord

    src_id = db.save_source(title="Graph Source", url=f"fixture://{cid}", source_type="paper")
    db.save_prior_art(
        candidate_id=cid,
        query=f"{cid} prior art",
        finding='{"conclusion": "Insufficient evidence."}',
        similarity_class="insufficient_evidence",
        source_id=src_id,
    )

    # model v1 + v2 (the §34 improvement)
    from blockchain_rd_lab.formalization.agents import build_math_model_fixture
    from blockchain_rd_lab.research import CandidateBrief

    brief = CandidateBrief.from_candidate(cand)
    v1 = build_math_model_fixture(brief)
    db.save_math_model(cid, json.dumps(v1), "initial model", version=1)
    v2 = dict(v1)
    v2["version"] = 2
    db.save_math_model(cid, json.dumps(v2), "hard cap + smoothing fix", version=2)

    # The improver's run record (as the real improve stage persists): §33
    # ADDRESSES edges derive from the proposal's OWN claims — never a
    # blanket claim over every profitable attack on the idea.
    from blockchain_rd_lab.redteam.agents import build_redteam_fixture

    _reports = build_redteam_fixture(brief, verdict="vulnerable")
    _claimed = [
        {
            "agent_name": agent,
            "vector_description": str(
                (_reports[agent].get("attack_vectors") or [{}])[0].get("vector", "")
            ),
            "fix_strategy": "hard single-step cap c_max + EMA anchor smoothing",
            "fixes_attack": True,
        }
        for agent in ("game_theory", "security", "oracle", "red_team")
        if _reports[agent].get("attack_vectors")
    ]
    from blockchain_rd_lab.schemas import AgentRunRecord, utcnow

    db.save_agent_run(
        AgentRunRecord(
            agent_name="improver",
            candidate_id=cid,
            status="success",
            finished_at=utcnow(),
            output={
                "summary": "Harden with hard cap + EMA smoothing.",
                "addressed_attacks": _claimed,
                "model": {"candidate_id": cid, "version": 2},
            },
        )
    )

    # experiment records (v1 + v2 style ids)
    for suffix, model in (("", "mathmodel-latest"), ("-v2", "mathmodel-v2")):
        db.save_experiment(
            ExperimentRecord(
                experiment_id=f"{cid}-scenarios{suffix}",
                candidate_id=cid,
                parameters={"steps": 10},
                dataset="synthetic-anchor-v1",
                model=model,
                seed=7,
                results={"ok": True},
            )
        )

    # adversarial reports with one profitable attack
    from blockchain_rd_lab.redteam.agents import build_redteam_fixture

    reports = build_redteam_fixture(
        CandidateBrief.from_candidate(cand), verdict="vulnerable"
    )
    for agent in ("game_theory", "security", "oracle", "red_team"):
        db.save_redteam_result(
            candidate_id=cid,
            agent_name=agent,
            report_json=json.dumps(reports[agent]),
            verdict="vulnerable",
        )
    return cid


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


class TestExtraction:
    def test_full_chain_extracted(self, memory_db):
        cid = store_chain(memory_db)
        g = GraphBuilder(memory_db).build()

        idea = g.node_by_id(cid)
        assert idea is not None and idea.kind is NodeKind.IDEA
        assert idea.meta["status"] == "red_team"

        # source cited
        assert any(
            e.kind is EdgeKind.CITES and e.source == cid for e in g.edges
        )
        # model v1 + v2 nodes with formalizes edges
        assert g.node_by_id(f"{cid}-model-v1") is not None
        assert g.node_by_id(f"{cid}-model-v2") is not None
        assert any(
            e.kind is EdgeKind.FORMALIZES and e.target == f"{cid}-model-v1"
            for e in g.edges
        )
        # patches edge v1 -> v2
        assert any(
            e.kind is EdgeKind.PATCHES
            and e.source == f"{cid}-model-v1"
            and e.target == f"{cid}-model-v2"
            for e in g.edges
        )
        # simulations attached (v1 run -> v1 model, v2 run -> v2 model)
        assert g.node_by_id(f"sim-{cid}-scenarios") is not None
        assert g.node_by_id(f"sim-{cid}-scenarios-v2") is not None
        assert any(
            e.kind is EdgeKind.SIMULATES and e.target == f"sim-{cid}-scenarios-v2"
            and e.source == f"{cid}-model-v2"
            for e in g.edges
        )
        # attack nodes exist and attack the idea
        attack_edges = [e for e in g.edges if e.kind is EdgeKind.ATTACKS and e.target == cid]
        assert attack_edges
        # improvement node derived from the patched model + addresses attacks
        imp_id = f"{cid}-improvement-v2"
        assert g.node_by_id(imp_id) is not None
        assert any(
            e.kind is EdgeKind.DERIVED_FROM and e.source == imp_id
            for e in g.edges
        )
        addressed = [
            e for e in g.edges if e.kind is EdgeKind.ADDRESSES and e.source == imp_id
        ]
        assert addressed  # the profitable attack is addressed

    def test_empty_database_is_empty_graph(self, memory_db):
        g = GraphBuilder(memory_db).build()
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_deterministic_rebuild(self, memory_db):
        store_chain(memory_db, "cand-det")
        b = GraphBuilder(memory_db)
        g1 = b.build()
        g2 = b.build()
        assert [n.id for n in g1.nodes] == [n.id for n in g2.nodes]
        assert [(e.source, e.target, e.kind) for e in g1.edges] == [
            (e.source, e.target, e.kind) for e in g2.edges
        ]


# ---------------------------------------------------------------------------
# Graph model queries
# ---------------------------------------------------------------------------


class TestGraphModel:
    def _mini_graph(self) -> KnowledgeGraph:
        nodes = [
            GraphNode(id="a", kind=NodeKind.IDEA, label="A"),
            GraphNode(id="m", kind=NodeKind.MECHANISM, label="M"),
            GraphNode(id="atk", kind=NodeKind.ATTACK, label="atk"),
        ]
        edges = [
            GraphEdge(source="a", target="m", kind=EdgeKind.FORMALIZES),
            GraphEdge(source="atk", target="a", kind=EdgeKind.ATTACKS),
        ]
        return KnowledgeGraph(nodes=nodes, edges=edges)

    def test_neighbors_both_directions(self):
        g = self._mini_graph()
        ids = {n.id for n in g.neighbors("a")}
        assert ids == {"m", "atk"}

    def test_neighbors_directional(self):
        g = self._mini_graph()
        assert {n.id for n in g.neighbors("a", incoming=False)} == {"m"}
        assert {n.id for n in g.neighbors("a", outgoing=False)} == {"atk"}

    def test_edges_of(self):
        g = self._mini_graph()
        assert len(g.edges_of("a")) == 2

    def test_subgraph_for_idea(self):
        g = self._mini_graph()
        sub = g.subgraph_for_idea("atk")
        assert {n.id for n in sub.nodes} == {"atk", "a"}

    def test_missing_node_queries(self):
        g = self._mini_graph()
        assert g.node_by_id("nope") is None
        assert g.neighbors("nope") == []
        assert g.edges_of("nope") == []


# ---------------------------------------------------------------------------
# §32 reuse: attack-fix catalog + similarity lookup
# ---------------------------------------------------------------------------


class TestReuse:
    def test_attack_fix_catalog(self, memory_db):
        cid = store_chain(memory_db)
        b = GraphBuilder(memory_db)
        g = b.build()
        fixes = b.attack_fixes(g)
        assert fixes
        fixed = [f for f in fixes if f.fixed_by]
        assert fixed, "the profitable attack should record its fixer"
        f = fixed[0]
        assert f.attacked_idea == cid
        assert f.fix_summary and "hard cap" in f.fix_summary

    def test_similar_attacks_lookup(self, memory_db):
        store_chain(memory_db)
        b = GraphBuilder(memory_db)
        g = b.build()
        hits = b.similar_attacks(g, "stale-data exploit oracle timing")
        assert hits
        # token overlap finds the oracle-flavored fixture vectors
        assert all(isinstance(h, AttackFix) for h in hits)

    def test_similar_attacks_no_overlap(self, memory_db):
        store_chain(memory_db)
        b = GraphBuilder(memory_db)
        g = b.build()
        assert b.similar_attacks(g, "zzz qqq xxx") == []

    def test_summary_counts(self, memory_db):
        store_chain(memory_db, "cand-sum")
        b = GraphBuilder(memory_db)
        g = b.build()
        s = b.summary(g)
        assert s.ideas == 1
        assert s.by_kind.get("attack", 0) > 0
        assert s.by_kind.get("simulation", 0) >= 2
        assert s.attacks_with_fixes >= 1
        assert s.nodes == g.node_count and s.edges == g.edge_count
