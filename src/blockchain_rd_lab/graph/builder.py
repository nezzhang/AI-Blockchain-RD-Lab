"""GraphBuilder: extract the §33 knowledge graph from stored evidence.

Deterministic extraction (§2): every node and edge comes from a stored,
validated row — candidates, prior-art findings + sources, math model
versions, §21 experiment records, adversarial reports, and §34
improvement rationales. The builder invents nothing; if the evidence is
missing, the node is missing.
"""

from __future__ import annotations

import json
import re
from typing import Any

from blockchain_rd_lab.database import LabDatabase
from blockchain_rd_lab.graph import (
    AttackFix,
    EdgeKind,
    GraphEdge,
    GraphNode,
    GraphSummary,
    KnowledgeGraph,
    NodeKind,
)


def _slug(text: str) -> str:
    """Stable short id fragment from free text."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


class GraphBuilder:
    """Builds the §33 graph over a lab database."""

    def __init__(self, database: LabDatabase) -> None:
        self.database = database

    # -- node factories ---------------------------------------------------------

    @staticmethod
    def _idea_node(cand: Any) -> GraphNode:
        return GraphNode(
            id=cand.id,
            kind=NodeKind.IDEA,
            label=cand.name,
            meta={
                "category": cand.category,
                "status": cand.status.value,
                "novelty_class": cand.novelty_class.value,
            },
        )

    @staticmethod
    def _mechanism_node(candidate_id: str, version: int) -> GraphNode:
        return GraphNode(
            id=f"{candidate_id}-model-v{version}",
            kind=NodeKind.MECHANISM,
            label=f"{candidate_id} model v{version}",
            meta={"version": version},
        )

    @staticmethod
    def _attack_node(candidate_id: str, agent: str, vector: str, detail: str) -> GraphNode:
        # Label carries the vector NAME (specific: "stale-data exploit");
        # meta keeps the full description for context.
        return GraphNode(
            id=f"{candidate_id}-attack-{agent}-{_slug(vector)}",
            kind=NodeKind.ATTACK,
            label=vector[:80] or detail[:80],
            meta={"agent": agent, "detail": detail[:300]},
        )

    # -- build -------------------------------------------------------------------

    def build(self) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        def add(node: GraphNode) -> None:
            nodes.setdefault(node.id, node)

        # 1) Idea nodes: every stored candidate.
        for cand in self.database.list_candidates(limit=None):
            add(self._idea_node(cand))

        # 2) Source nodes + CITES edges from prior-art findings.
        sources = {s["id"]: s for s in self.database.list_sources(limit=None)}
        for s in sources.values():
            add(
                GraphNode(
                    id=f"source-{s['id']}",
                    kind=NodeKind.SOURCE,
                    label=str(s.get("title") or s.get("url") or "source")[:80],
                    meta={
                        "url": s.get("url", ""),
                        "source_type": s.get("source_type", ""),
                    },
                )
            )
        for row in self.database.list_prior_art():
            if row["candidate_id"] not in nodes:
                continue
            sid = row.get("source_id")
            if sid and f"source-{sid}" in nodes:
                edges.append(
                    GraphEdge(
                        source=row["candidate_id"],
                        target=f"source-{sid}",
                        kind=EdgeKind.CITES,
                        meta={"query": str(row.get("query", ""))[:120]},
                    )
                )

        # 3) Mechanism nodes (one per stored model version) + FORMALIZES.
        model_rows = self.database.list_math_models()
        for m in model_rows:
            cid = m["candidate_id"]
            if cid not in nodes:
                continue
            version = int(m["version"])
            mech = self._mechanism_node(cid, version)
            add(mech)
            edges.append(
                GraphEdge(source=cid, target=mech.id, kind=EdgeKind.FORMALIZES)
            )
            # PATCHES: consecutive versions of the same candidate.
            if version > 1:
                prev = self._mechanism_node(cid, version - 1)
                edges.append(
                    GraphEdge(source=prev.id, target=mech.id, kind=EdgeKind.PATCHES)
                )

        # 4) Simulation nodes + SIMULATES edges from §21 experiment records.
        for exp in self.database.iter_experiments():
            if exp.candidate_id not in nodes:
                continue
            sim_id = f"sim-{exp.experiment_id}"
            add(
                GraphNode(
                    id=sim_id,
                    kind=NodeKind.SIMULATION,
                    label=exp.experiment_id,
                    meta={
                        "seed": exp.seed,
                        "model": exp.model,
                        "dataset": exp.dataset,
                        "simulation_version": exp.simulation_version,
                    },
                )
            )
            # Attach the run to the model version it exercised.
            version_match = re.search(r"-v(\d+)$", exp.model or "")
            version = int(version_match.group(1)) if version_match else 1
            mech_id = f"{exp.candidate_id}-model-v{version}"
            target = mech_id if mech_id in nodes else exp.candidate_id
            edges.append(
                GraphEdge(source=target, target=sim_id, kind=EdgeKind.SIMULATES)
            )

        # 5) Attack nodes + ATTACKS edges from adversarial reports; and
        #    IMPROVEMENT nodes with ADDRESSES/DERIVED_FROM from §34 loop.
        improvement_attacks: dict[str, list[str]] = {}
        for row in self.database.list_redteam_results():
            cid = row.get("candidate_id", "")
            agent = row.get("agent_name", "")
            if cid not in nodes:
                continue
            raw = row.get("report_json")
            report = json.loads(raw) if isinstance(raw, str) else (raw or {})
            vectors = report.get("attack_vectors") or report.get("manipulation_vectors") or []
            for v in vectors:
                vector_name = str(v.get("vector") or "")
                detail = str(v.get("description") or "")
                if not vector_name and not detail:
                    continue
                attack = self._attack_node(cid, agent, vector_name, detail)
                add(attack)
                edges.append(
                    GraphEdge(
                        source=attack.id,
                        target=cid,
                        kind=EdgeKind.ATTACKS,
                        meta={"profitable": bool(v.get("profitable_for_attacker"))},
                    )
                )

        for m in model_rows:
            if int(m["version"]) <= 1:
                continue
            cid = m["candidate_id"]
            imp = GraphNode(
                id=f"{cid}-improvement-v{m['version']}",
                kind=NodeKind.IMPROVEMENT,
                label=f"{cid} improvement v{m['version']}",
                meta={"rationale": str(m.get("rationale", ""))[:400]},
            )
            add(imp)
            mech = self._mechanism_node(cid, int(m["version"]))
            edges.append(
                GraphEdge(source=imp.id, target=mech.id, kind=EdgeKind.DERIVED_FROM)
            )
            # ADDRESSES: profitable attacks on this idea that the fix targets.
            for e in list(edges):
                if (
                    e.kind is EdgeKind.ATTACKS
                    and e.target == cid
                    and e.meta.get("profitable")
                    and e.source in nodes
                ):
                    edges.append(
                        GraphEdge(source=imp.id, target=e.source, kind=EdgeKind.ADDRESSES)
                    )
                    improvement_attacks.setdefault(imp.id, []).append(e.source)

        graph.nodes = sorted(nodes.values(), key=lambda n: (n.kind.value, n.id))
        graph.edges = sorted(edges, key=lambda e: (e.kind.value, e.source, e.target))
        _ = improvement_attacks
        return graph

    # -- summary + §32 reuse queries ----------------------------------------------

    def summary(self, graph: KnowledgeGraph) -> GraphSummary:
        by_kind: dict[str, int] = {}
        for n in graph.nodes:
            by_kind[n.kind.value] = by_kind.get(n.kind.value, 0) + 1
        ideas = by_kind.get(NodeKind.IDEA.value, 0)
        fixes = self.attack_fixes(graph)
        with_fix = sum(1 for f in fixes if f.fixed_by)
        return GraphSummary(
            nodes=graph.node_count,
            edges=graph.edge_count,
            by_kind=by_kind,
            ideas=ideas,
            attacks_with_fixes=with_fix,
        )

    def attack_fixes(self, graph: KnowledgeGraph) -> list[AttackFix]:
        """All attacks with their fix status — §32 reuse catalog.

        Future agents consult this: 'has a similar attack been fixed
        before, and how?' Deterministic; empty fix means unresolved.
        """
        out: list[AttackFix] = []
        for n in graph.nodes:
            if n.kind is not NodeKind.ATTACK:
                continue
            idea_id = next(
                (e.target for e in graph.edges if e.source == n.id and e.kind is EdgeKind.ATTACKS),
                "",
            )
            fixed_by = next(
                (
                    e.source
                    for e in graph.edges
                    if e.target == n.id and e.kind is EdgeKind.ADDRESSES
                ),
                None,
            )
            fix_node = graph.node_by_id(fixed_by) if fixed_by else None
            attack_node = graph.node_by_id(n.id)
            out.append(
                AttackFix(
                    attack_id=n.id,
                    attack_label=n.label,
                    attacked_idea=idea_id,
                    fixed_by=fixed_by,
                    fix_summary=(
                        str(fix_node.meta.get("rationale", ""))[:200] if fix_node else None
                    ),
                    attack_text=str(attack_node.meta.get("detail", "")) if attack_node else "",
                )
            )
        out.sort(key=lambda f: (f.attacked_idea, f.attack_id))
        return out

    def similar_attacks(self, graph: KnowledgeGraph, text: str, limit: int = 5) -> list[AttackFix]:
        """Token-overlap lookup of historically similar attacks (§32)."""
        from blockchain_rd_lab.discovery.normalize import _STOPWORDS, _TOKEN_RE

        tokens = {
            t for t in _TOKEN_RE.findall(text.lower())
            if t not in _STOPWORDS and len(t) >= 3
        }
        if not tokens:
            return []
        scored: list[tuple[float, AttackFix]] = []
        for fix in self.attack_fixes(graph):
            node = graph.node_by_id(fix.attack_id)
            corpus = fix.attack_label + " " + fix.attack_text
            if node is not None:
                corpus += " " + str(node.meta.get("detail", ""))
            other = {
                t for t in _TOKEN_RE.findall(corpus.lower())
                if t not in _STOPWORDS and len(t) >= 3
            }
            if not other:
                continue
            overlap = len(tokens & other) / len(tokens | other)
            if overlap > 0:
                scored.append((overlap, fix))
        scored.sort(key=lambda p: (-p[0], p[1].attack_id))
        return [f for _, f in scored[:limit]]
