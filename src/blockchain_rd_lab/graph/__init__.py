"""§33 Research Knowledge Graph: reusable relationships between discoveries.

The lab stores all evidence in disconnected tables. The knowledge graph
links it into the §33 shape so future agents can REUSE previous
discoveries instead of re-deriving them:

    Idea ↔ Source (paper/protocol) ↔ Mechanism(model vN) ↔
    Simulation(experiment) ↔ Attack(vector) ↔ Improvement(model vN+1)

Everything here is DETERMINISTIC CODE (§2): nodes and edges are extracted
from stored, validated evidence — never invented. The graph is a derived
view; the database remains the source of truth (rebuildable at will).
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NodeKind(enum.StrEnum):
    """§33 node types (plus the lab's candidate-idea root)."""

    IDEA = "idea"                  # a stored candidate (mechanism idea)
    SOURCE = "source"              # a paper / protocol / dataset referenced
    MECHANISM = "mechanism"        # a formalized MathModel version
    SIMULATION = "simulation"      # a persisted experiment record (§21)
    ATTACK = "attack"              # an adversarial attack vector (§9)
    IMPROVEMENT = "improvement"    # a patched model version (§34 loop)


class EdgeKind(enum.StrEnum):
    """Typed relationships between nodes (§33 arrows)."""

    CITES = "cites"                # idea → source (prior-art reference)
    FORMALIZES = "formalizes"      # idea → mechanism (model vN)
    SIMULATES = "simulates"        # mechanism → simulation (experiment record)
    ATTACKS = "attacks"            # attack → idea (adversarial finding)
    ADDRESSES = "addresses"        # improvement → attack (the fix claim)
    PATCHES = "patches"            # mechanism(vN) → mechanism(vN+1)
    DERIVED_FROM = "derived_from"  # improvement → mechanism (base model)


class GraphNode(BaseModel):
    """One node in the knowledge graph."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: NodeKind
    label: str
    meta: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """One typed, directed relationship."""

    model_config = ConfigDict(frozen=True)

    source: str
    target: str
    kind: EdgeKind
    meta: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    """The derived §33 graph over one lab database."""

    model_config = ConfigDict(validate_assignment=True)

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def node_by_id(self, node_id: str) -> GraphNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def neighbors(
        self, node_id: str, *, incoming: bool = True, outgoing: bool = True
    ) -> list[GraphNode]:
        """All nodes directly connected to `node_id` (either direction)."""
        out: dict[str, GraphNode] = {}
        for e in self.edges:
            if outgoing and e.source == node_id:
                n = self.node_by_id(e.target)
                if n:
                    out[n.id] = n
            if incoming and e.target == node_id:
                n = self.node_by_id(e.source)
                if n:
                    out[n.id] = n
        return list(out.values())

    def edges_of(self, node_id: str) -> list[GraphEdge]:
        """All edges touching `node_id`."""
        return [e for e in self.edges if e.source == node_id or e.target == node_id]

    def subgraph_for_idea(self, idea_id: str) -> KnowledgeGraph:
        """The full §33 chain for one idea: sources, models, runs, attacks, fixes."""
        keep_nodes: set[str] = {idea_id}
        keep_edges: list[GraphEdge] = []
        for e in self.edges:
            if e.source in keep_nodes or e.target in keep_nodes:
                keep_edges.append(e)
                keep_nodes.update((e.source, e.target))
        nodes = [n for n in self.nodes if n.id in keep_nodes]
        return KnowledgeGraph(nodes=nodes, edges=keep_edges)


class AttackFix(BaseModel):
    """§32 reuse: how an attack was answered, for similar future attacks."""

    model_config = ConfigDict(frozen=True)

    attack_id: str
    attack_label: str
    attacked_idea: str
    fixed_by: str | None = None
    fix_summary: str | None = None
    attack_text: str = ""


class GraphSummary(BaseModel):
    """Build outcome for the CLI."""

    model_config = ConfigDict(validate_assignment=True)

    nodes: int = 0
    edges: int = 0
    by_kind: dict[str, int] = Field(default_factory=dict)
    ideas: int = 0
    attacks_with_fixes: int = 0
