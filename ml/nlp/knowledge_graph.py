"""Phase 33 - Traffic Network Knowledge Graph (NLP-12).

Constructs an RDF-style entity-relationship graph linking Intersections, Corridors,
Signal Policies, Incidents, and Zones, queryable via simple semantic relation filters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


class TrafficKnowledgeGraph:
    """Directed multi-relational knowledge graph for transport topologies and operational state."""

    def __init__(self):
        self.triples: List[Tuple[str, str, str]] = []  # (Subject, Predicate, Object)
        self.entities: Set[str] = set()

    def add_triple(self, subj: str, pred: str, obj: str) -> None:
        self.triples.append((subj, pred, obj))
        self.entities.add(subj)
        self.entities.add(obj)

    def populate_from_simulation(self, city: str, zone_count: int, active_policy: str) -> None:
        """Seed initial knowledge graph from simulation state."""
        self.add_triple(city, "has_policy", active_policy)
        self.add_triple(active_policy, "controls_mode", "TRAFFIC_LIGHTS")

        for z in range(min(5, zone_count)):
            z_node = f"Zone_{z}"
            self.add_triple(city, "contains_ward", z_node)
            self.add_triple(z_node, "has_priority", "STANDARD_TRANSIT")

    def query_relations(self, subject: str | None = None, predicate: str | None = None) -> List[Dict[str, str]]:
        """Query matching graph triples."""
        results = []
        for s, p, o in self.triples:
            if subject and s.lower() != subject.lower():
                continue
            if predicate and p.lower() != predicate.lower():
                continue
            results.append({"subject": s, "predicate": p, "object": o})
        return results

    def to_cytoscape_json(self) -> Dict[str, Any]:
        """Convert graph to node/edge format for dashboard visualization."""
        nodes = [{"data": {"id": e, "label": e}} for e in sorted(list(self.entities))]
        edges = [
            {"data": {"id": f"e_{i}", "source": s, "target": o, "label": p}}
            for i, (s, p, o) in enumerate(self.triples)
        ]
        return {"nodes": nodes, "edges": edges}
