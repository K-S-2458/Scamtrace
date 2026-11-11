"""NetworkX knowledge graph construction for SCAMTRACE AI."""
import json
from typing import Any, Dict, List
import networkx as nx
from sqlalchemy.orm import Session

from backend.app.db.models import Edge, Entity, Evidence


def build_case_graph(db: Session, case_id: str) -> nx.MultiDiGraph:
    """Build a NetworkX MultiDiGraph representing evidence nodes, entity nodes, and correlation edges."""
    g = nx.MultiDiGraph(case_id=case_id)

    # 1. Add Evidence Nodes
    evidence_items = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.id)
        .all()
    )

    for ev in evidence_items:
        ts_str = ev.source_timestamp.strftime("%Y-%m-%d %H:%M:%S") if ev.source_timestamp else ev.uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
        g.add_node(
            ev.id,
            node_type="evidence",
            label=f"{ev.id} ({ev.type.upper()})",
            evidence_type=ev.type,
            time=ts_str,
            sha256=ev.sha256[:12] + "...",
            analysis_status=ev.analysis_status,
        )

    # 2. Add Entity Nodes and connect to parent Evidence
    entities = (
        db.query(Entity)
        .filter(Entity.case_id == case_id)
        .all()
    )

    for ent in entities:
        ent_node_id = f"ent_{ent.entity_type}_{ent.value}"
        if not g.has_node(ent_node_id):
            g.add_node(
                ent_node_id,
                node_type="entity",
                label=f"{ent.entity_type}: {ent.value}",
                entity_type=ent.entity_type,
                value=ent.value,
            )
        # Structural edge from evidence to extracted entity
        g.add_edge(
            ev.id if False else ent.evidence_id,
            ent_node_id,
            key=f"has_{ent.entity_type}",
            link_type="CONTAINS_ENTITY",
            confidence=1.0,
            reason=f"Evidence {ent.evidence_id} contains entity {ent.value}",
        )

    # 3. Add Cross-Evidence Correlation Edges
    edges = (
        db.query(Edge)
        .filter(Edge.case_id == case_id)
        .all()
    )

    for edge in edges:
        try:
            supp_fields = json.loads(edge.supporting_fields)
        except Exception:
            supp_fields = {}

        g.add_edge(
            edge.source_evidence_id,
            edge.target_evidence_id,
            key=f"{edge.link_type}_{edge.id}",
            edge_id=edge.id,
            link_type=edge.link_type,
            confidence=edge.confidence,
            reason=edge.reason,
            supporting_fields=supp_fields,
            rule_version=edge.rule_version,
        )

    return g


def get_incident_clusters(g: nx.MultiDiGraph) -> List[Dict[str, Any]]:
    """Compute connected components of the evidence subgraph as candidate incident clusters."""
    # Build undirected evidence-only projection
    evidence_nodes = [n for n, d in g.nodes(data=True) if d.get("node_type") == "evidence"]
    sub_edges = []

    for u, v, data in g.edges(data=True):
        if data.get("link_type") != "CONTAINS_ENTITY" and u in evidence_nodes and v in evidence_nodes:
            sub_edges.append((u, v))

    proj = nx.Graph()
    proj.add_nodes_from(evidence_nodes)
    proj.add_edges_from(sub_edges)

    clusters = []
    for idx, comp in enumerate(nx.connected_components(proj), start=1):
        clusters.append({
            "cluster_id": f"Cluster-{idx}",
            "evidence_count": len(comp),
            "evidence_ids": sorted(list(comp)),
        })

    return clusters

