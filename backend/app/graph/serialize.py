"""Cytoscape.js JSON serializer for SCAMTRACE AI knowledge graphs."""
from typing import Any, Dict
import networkx as nx
from backend.app.graph.builder import get_incident_clusters


def serialize_to_cytoscape(g: nx.MultiDiGraph) -> Dict[str, Any]:
    """Serialize a NetworkX graph into Cytoscape.js compatible elements format."""
    nodes = []
    edges = []

    for node_id, attrs in g.nodes(data=True):
        node_data = {"id": str(node_id)}
        node_data.update(attrs)
        nodes.append({"data": node_data})

    edge_counter = 0
    for u, v, key, attrs in g.edges(keys=True, data=True):
        edge_counter += 1
        edge_id = attrs.get("edge_id") or f"edge_{u}_{v}_{edge_counter}"
        edge_data = {
            "id": edge_id,
            "source": str(u),
            "target": str(v),
        }
        edge_data.update(attrs)
        edges.append({"data": edge_data})

    clusters = get_incident_clusters(g)

    return {
        "case_id": g.graph.get("case_id"),
        "elements": {
            "nodes": nodes,
            "edges": edges,
        },
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cluster_count": len(clusters),
        },
        "clusters": clusters,
    }

