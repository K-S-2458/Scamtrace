import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { apiCorrelate, apiGetGraph, GraphResponse } from '../api/client';

interface RelationshipExplorerProps {
  activeCaseId: string | null;
}

export const RelationshipExplorer: React.FC<RelationshipExplorerProps> = ({ activeCaseId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<any | null>(null);
  const [linkFilter, setLinkFilter] = useState<string>('ALL');
  const [highlightCluster, setHighlightCluster] = useState<string | null>(null);
  const [correlating, setCorrelating] = useState(false);

  const loadGraph = async () => {
    if (!activeCaseId) return;
    try {
      const data = await apiGetGraph(activeCaseId);
      setGraphData(data);
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [activeCaseId]);

  const handleRunCorrelation = async () => {
    if (!activeCaseId) return;
    setCorrelating(true);
    try {
      await apiCorrelate(activeCaseId);
      await loadGraph();
    } catch (err: any) {
      alert(`Correlation error: ${err.message}`);
    } finally {
      setCorrelating(false);
    }
  };

  // Initialize and update Cytoscape graph
  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Filter edges if filter selected
    const filteredEdges =
      linkFilter === 'ALL'
        ? graphData.elements.edges
        : graphData.elements.edges.filter((e) => e.data.link_type === linkFilter || e.data.link_type === 'CONTAINS_ENTITY');

    // Destroy existing instance
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: graphData.elements.nodes as any,
        edges: filteredEdges as any,
      },
      style: [
        {
          selector: 'node[node_type = "evidence"]',
          style: {
            'background-color': '#38bdf8',
            label: 'data(label)',
            color: '#ffffff',
            'font-size': '11px',
            'font-weight': 'bold',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            width: 38,
            height: 38,
            'border-width': 2,
            'border-color': '#0284c7',
          },
        },
        {
          selector: 'node[node_type = "entity"]',
          style: {
            'background-color': '#64748b',
            label: 'data(label)',
            color: '#94a3b8',
            'font-size': '9px',
            'text-valign': 'bottom',
            'text-margin-y': 3,
            width: 20,
            height: 20,
          },
        },
        {
          selector: 'edge[link_type = "CONTAINS_ENTITY"]',
          style: {
            width: 1,
            'line-color': '#334155',
            'curve-style': 'bezier',
            opacity: 0.4,
          },
        },
        {
          selector: 'edge[link_type != "CONTAINS_ENTITY"]',
          style: {
            width: 3,
            'line-color': '#f59e0b',
            'target-arrow-color': '#f59e0b',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(link_type)',
            'font-size': '9px',
            color: '#cbd5e1',
            'text-background-opacity': 0.8,
            'text-background-color': '#0f172a',
            'text-background-padding': '2px',
          },
        },
        {
          selector: ':selected',
          style: {
            'border-width': 4,
            'border-color': '#ec4899',
            'line-color': '#ec4899',
            'target-arrow-color': '#ec4899',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 40,
        nodeRepulsion: () => 4500,
      },
    });

    cy.on('tap', 'node', (evt) => {
      setSelectedEdge(null);
      setSelectedNode(evt.target.data());
    });

    cy.on('tap', 'edge', (evt) => {
      setSelectedNode(null);
      setSelectedEdge(evt.target.data());
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
        setSelectedEdge(null);
      }
    });

    cyRef.current = cy;
  }, [graphData, linkFilter]);

  // Handle cluster highlighting
  useEffect(() => {
    if (!cyRef.current || !graphData) return;
    const cy = cyRef.current;

    if (!highlightCluster) {
      cy.elements().removeClass('highlighted-cluster');
      cy.elements().style('opacity', 1.0);
      return;
    }

    const cluster = graphData.clusters.find((c) => c.cluster_id === highlightCluster);
    if (cluster) {
      cy.elements().style('opacity', 0.2);
      cluster.evidence_ids.forEach((id) => {
        const node = cy.getElementById(id);
        node.style('opacity', 1.0);
        node.connectedEdges().style('opacity', 1.0);
      });
    }
  }, [highlightCluster, graphData]);

  if (!activeCaseId) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Please select an investigation case from the Dashboard first.
      </div>
    );
  }

  const allLinkTypes = graphData
    ? Array.from(new Set(graphData.elements.edges.map((e) => e.data.link_type))).filter(
        (lt) => lt !== 'CONTAINS_ENTITY'
      )
    : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 65px)' }}>
      {/* Top Toolbar */}
      <div
        style={{
          padding: '12px 24px',
          backgroundColor: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
        }}
      >
        <button
          onClick={handleRunCorrelation}
          disabled={correlating}
          style={{
            backgroundColor: 'var(--accent)',
            color: '#0f172a',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '4px',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          {correlating ? 'Correlating Rules...' : '⚡ Run Correlation Engine'}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
          <span>Filter Link Type:</span>
          <select
            value={linkFilter}
            onChange={(e) => setLinkFilter(e.target.value)}
            style={{
              padding: '6px 10px',
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
            }}
          >
            <option value="ALL">All Link Types</option>
            {allLinkTypes.map((lt) => (
              <option key={lt} value={lt}>
                {lt}
              </option>
            ))}
          </select>
        </div>

        {/* Cluster Highlights */}
        {graphData && graphData.clusters.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', marginLeft: 'auto' }}>
            <span>Incident Clusters:</span>
            {graphData.clusters.map((c) => (
              <button
                key={c.cluster_id}
                onClick={() => setHighlightCluster(highlightCluster === c.cluster_id ? null : c.cluster_id)}
                style={{
                  backgroundColor: highlightCluster === c.cluster_id ? '#ec4899' : 'var(--bg-tertiary)',
                  color: '#ffffff',
                  border: 'none',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {c.cluster_id} ({c.evidence_count} items)
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Workspace Area: Graph Canvas + Inspector Pane */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 340px', overflow: 'hidden' }}>
        {/* Cytoscape Container */}
        <div ref={containerRef} style={{ width: '100%', height: '100%', backgroundColor: '#090d16' }} />

        {/* Inspector Panel */}
        <div
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderLeft: '1px solid var(--border)',
            padding: '20px',
            overflowY: 'auto',
          }}
        >
          <h2 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Forensic Inspector</h2>

          {selectedNode && (
            <div>
              <span
                style={{
                  fontSize: '0.75rem',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  backgroundColor: 'var(--accent)',
                  color: '#0f172a',
                  fontWeight: 700,
                }}
              >
                {selectedNode.node_type?.toUpperCase()} NODE
              </span>
              <h3 style={{ fontSize: '1.15rem', margin: '8px 0' }}>{selectedNode.label}</h3>

              <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>ID: <code>{selectedNode.id}</code></div>
                {selectedNode.evidence_type && <div>Modality: <strong>{selectedNode.evidence_type.toUpperCase()}</strong></div>}
                {selectedNode.time && <div>Timestamp: {selectedNode.time}</div>}
                {selectedNode.sha256 && <div>SHA-256: <code>{selectedNode.sha256}</code></div>}
                {selectedNode.entity_type && <div>Entity Type: <code>{selectedNode.entity_type}</code></div>}
                {selectedNode.value && <div>Normalized Value: <code>{selectedNode.value}</code></div>}
              </div>
            </div>
          )}

          {selectedEdge && (
            <div>
              <span
                style={{
                  fontSize: '0.75rem',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  backgroundColor: '#f59e0b',
                  color: '#0f172a',
                  fontWeight: 700,
                }}
              >
                CORRELATION EDGE
              </span>
              <h3 style={{ fontSize: '1.05rem', margin: '8px 0', color: '#f59e0b' }}>
                {selectedEdge.link_type}
              </h3>

              <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>From: <strong>{selectedEdge.source}</strong> → To: <strong>{selectedEdge.target}</strong></div>
                <div>Confidence Score: <strong>{(selectedEdge.confidence || 0).toFixed(2)}</strong></div>
                <div style={{ marginTop: '8px' }}>
                  <div style={{ color: 'var(--text-secondary)', marginBottom: '2px' }}>Explanatory Rationale:</div>
                  <div
                    style={{
                      padding: '10px',
                      backgroundColor: 'var(--bg-primary)',
                      borderRadius: '4px',
                      borderLeft: '3px solid #f59e0b',
                    }}
                  >
                    {selectedEdge.reason || 'No reason specified'}
                  </div>
                </div>

                {selectedEdge.supporting_fields && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ color: 'var(--text-secondary)', marginBottom: '2px' }}>Supporting Trigger Entities:</div>
                    <pre
                      style={{
                        padding: '8px',
                        backgroundColor: 'var(--bg-primary)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        overflowX: 'auto',
                      }}
                    >
                      {JSON.stringify(selectedEdge.supporting_fields, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {!selectedNode && !selectedEdge && (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '30px', textAlign: 'center' }}>
              Click any evidence node, entity node, or relationship edge in the graph to inspect forensic attributes and rule triggers.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
