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
  const [showEntities, setShowEntities] = useState<boolean>(false);
  const [correlating, setCorrelating] = useState(false);
  const [activeTab, setActiveTab] = useState<'both' | 'cards' | 'map'>('both');

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

  // Correlation edges (excluding CONTAINS_ENTITY)
  const correlationEdges = graphData?.elements.edges.filter(
    (e) => e.data.link_type !== 'CONTAINS_ENTITY'
  ) || [];

  const filteredCorrelationEdges =
    linkFilter === 'ALL'
      ? correlationEdges
      : correlationEdges.filter((e) => e.data.link_type === linkFilter);

  // Initialize and update Cytoscape graph
  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Filter nodes based on showEntities toggle
    const filteredNodes = showEntities
      ? graphData.elements.nodes
      : graphData.elements.nodes.filter((n) => n.data.node_type === 'evidence');

    // Filter edges
    let activeEdges = filteredCorrelationEdges;
    if (showEntities) {
      const containsEdges = graphData.elements.edges.filter((e) => e.data.link_type === 'CONTAINS_ENTITY');
      activeEdges = [...filteredCorrelationEdges, ...containsEdges];
    }

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: filteredNodes as any,
        edges: activeEdges as any,
      },
      style: [
        {
          selector: 'node[node_type = "evidence"]',
          style: {
            'background-color': '#0ea5e9',
            label: 'data(label)',
            color: '#f8fafc',
            'font-size': '12px',
            'font-weight': 'bold',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            width: 44,
            height: 44,
            'border-width': 3,
            'border-color': '#38bdf8',
            'border-opacity': 0.8,
          },
        },
        {
          selector: 'node[node_type = "entity"]',
          style: {
            'background-color': '#6366f1',
            label: 'data(label)',
            color: '#cbd5e1',
            'font-size': '10px',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            width: 22,
            height: 22,
            'border-width': 1,
            'border-color': '#a5b4fc',
          },
        },
        {
          selector: 'edge[link_type = "CONTAINS_ENTITY"]',
          style: {
            width: 1,
            'line-color': '#334155',
            'curve-style': 'bezier',
            opacity: 0.35,
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
            'font-size': '10px',
            'font-weight': 'bold',
            color: '#fde68a',
            'text-background-opacity': 0.9,
            'text-background-color': '#090d16',
            'text-background-padding': '3px',
            'text-border-opacity': 0.5,
            'text-border-color': '#f59e0b',
            'text-border-width': 1,
          },
        },
        {
          selector: ':selected',
          style: {
            'border-width': 4,
            'border-color': '#f43f5e',
            'line-color': '#f43f5e',
            'target-arrow-color': '#f43f5e',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 50,
        nodeRepulsion: () => 8000,
        idealEdgeLength: () => 140,
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
  }, [graphData, linkFilter, showEntities]);

  const selectEdgeFromCard = (edgeData: any) => {
    setSelectedNode(null);
    setSelectedEdge(edgeData);
    if (cyRef.current) {
      cyRef.current.$(':selected').unselect();
      const edge = cyRef.current.$(`edge[id = "${edgeData.id}"]`);
      if (edge.length > 0) {
        edge.select();
        cyRef.current.center(edge);
      }
    }
  };

  const getRuleIcon = (linkType: string) => {
    switch (linkType) {
      case 'SHARED_PHONE':
        return '📞';
      case 'SHARED_DOMAIN':
        return '🌐';
      case 'SAME_BRAND_IMPERSONATION':
        return '🏦';
      case 'APK_LURE_PATTERN':
        return '📱';
      case 'URL_HOST_MATCH':
        return '🔗';
      case 'REDIRECT_CHAIN':
        return '🔀';
      case 'SIMILAR_TEXT_TEMPLATE':
        return '📝';
      default:
        return '⚡';
    }
  };

  const getSupportingHighlight = (edge: any) => {
    const supp = edge.supporting_fields || {};
    if (supp.phone) return `Shared Phone: ${supp.phone}`;
    if (supp.domain) return `Shared Domain: ${supp.domain}`;
    if (supp.brand) return `Target Brand: ${supp.brand} (${supp.unauthorized_domain || 'Mismatched Host'})`;
    if (supp.lure_words) return `Lure Keywords: ${supp.lure_words.join(', ')}`;
    if (supp.similarity) return `Text Similarity: ${(supp.similarity * 100).toFixed(1)}%`;
    if (supp.host) return `Host Match: ${supp.host}`;
    return null;
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Top Header & Action Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-accent">CORRELATION RECONSTRUCTION</span>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc' }}>
              Relationship Explorer
            </h1>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '2px' }}>
            Correlate cross-artifact connections (shared phones, spoofed domains, brand impersonations, APK lures) and prove campaign attribution.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={handleRunCorrelation}
            disabled={correlating || !activeCaseId}
            className="btn-primary"
            style={{ fontSize: '0.85rem' }}
          >
            {correlating ? 'Correlating Rules...' : '🔄 Run Correlation Engine'}
          </button>
        </div>
      </div>

      {/* Filter and View Toggle Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '12px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 700 }}>
              FILTER RULE:
            </span>
            <select
              className="form-select"
              style={{ width: 'auto', padding: '6px 12px', fontSize: '0.82rem' }}
              value={linkFilter}
              onChange={(e) => setLinkFilter(e.target.value)}
            >
              <option value="ALL">All Forensic Rules ({correlationEdges.length} links)</option>
              <option value="SHARED_PHONE">📞 Shared Phone Number</option>
              <option value="SHARED_DOMAIN">🌐 Shared Malicious Domain</option>
              <option value="SAME_BRAND_IMPERSONATION">🏦 Brand Impersonation</option>
              <option value="APK_LURE_PATTERN">📱 APK Dropper Pattern</option>
              <option value="URL_HOST_MATCH">🔗 URL Host Match</option>
              <option value="REDIRECT_CHAIN">🔀 Redirect Chain</option>
              <option value="SIMILAR_TEXT_TEMPLATE">📝 Similar Text Template</option>
            </select>
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showEntities}
              onChange={(e) => setShowEntities(e.target.checked)}
            />
            <span>Show Raw Entity Bridge Nodes</span>
          </label>
        </div>

        {/* View Mode Tabs */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setActiveTab('both')}
            className={activeTab === 'both' ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.78rem', padding: '6px 12px' }}
          >
            Dual View (Ledger + Graph)
          </button>
          <button
            onClick={() => setActiveTab('cards')}
            className={activeTab === 'cards' ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.78rem', padding: '6px 12px' }}
          >
            📋 Correlation Ledger Only
          </button>
          <button
            onClick={() => setActiveTab('map')}
            className={activeTab === 'map' ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.78rem', padding: '6px 12px' }}
          >
            🕸️ Interactive Canvas Only
          </button>
        </div>
      </div>

      {/* Main Content Layout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns:
            activeTab === 'cards'
              ? '1fr 340px'
              : activeTab === 'map'
              ? '1fr 340px'
              : 'minmax(420px, 1.1fr) minmax(480px, 1.4fr) 320px',
          gap: '20px',
          height: 'calc(100vh - 240px)',
        }}
      >
        {/* PANE 1: Forensic Correlation Ledger (Clear Reasoned Cards) */}
        {(activeTab === 'both' || activeTab === 'cards') && (
          <div
            className="glass-panel"
            style={{
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              overflowY: 'hidden',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="badge badge-accent">FORENSIC LEDGER</span>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc' }}>
                  Discovered Cross-Artifact Links ({filteredCorrelationEdges.length})
                </h3>
              </div>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', paddingRight: '4px' }}>
              {filteredCorrelationEdges.length === 0 ? (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🔍</div>
                  <div style={{ fontWeight: 600 }}>No cross-artifact correlations found.</div>
                  <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                    Click "Run Correlation Engine" above or add evidence items that share phone numbers, domains, or brand lures.
                  </div>
                </div>
              ) : (
                filteredCorrelationEdges.map((edge, idx) => {
                  const isSelected = selectedEdge?.id === edge.data.id;
                  const suppText = getSupportingHighlight(edge.data);
                  const icon = getRuleIcon(edge.data.link_type);

                  return (
                    <div
                      key={idx}
                      onClick={() => selectEdgeFromCard(edge.data)}
                      className="glass-panel-interactive"
                      style={{
                        padding: '16px',
                        cursor: 'pointer',
                        borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
                        backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'rgba(30, 41, 59, 0.6)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '1.2rem' }}>{icon}</span>
                          <div>
                            <div style={{ fontWeight: 800, fontSize: '0.92rem', color: '#f8fafc' }}>
                              {edge.data.link_type.replace(/_/g, ' ')}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '1px' }}>
                              Connects <strong style={{ color: 'var(--accent)' }}>{edge.data.source}</strong> ⟷ <strong style={{ color: 'var(--accent)' }}>{edge.data.target}</strong>
                            </div>
                          </div>
                        </div>

                        <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                          {Math.round((edge.data.confidence || 0.8) * 100)}% Confidence
                        </span>
                      </div>

                      {/* Supporting Highlight Tag (e.g. Same Phone or Domain) */}
                      {suppText && (
                        <div style={{ marginBottom: '8px' }}>
                          <span
                            className="badge badge-purple"
                            style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}
                          >
                            🔑 {suppText}
                          </span>
                        </div>
                      )}

                      {/* Plain-English Forensic Reason */}
                      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                        {edge.data.reason}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* PANE 2: Interactive Cytoscape Visual Canvas */}
        {(activeTab === 'both' || activeTab === 'map') && (
          <div
            className="glass-panel"
            style={{
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="badge badge-accent">INTERACTIVE MAP</span>
                <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  {showEntities ? 'Showing Evidence & Entities' : 'Clean Evidence Flow View'}
                </span>
              </div>

              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  onClick={() => cyRef.current?.fit(undefined, 40)}
                  className="btn-secondary"
                  style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                >
                  Fit Canvas
                </button>
                <button
                  onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
                  className="btn-secondary"
                  style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                >
                  +
                </button>
                <button
                  onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
                  className="btn-secondary"
                  style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                >
                  -
                </button>
              </div>
            </div>

            {/* Cytoscape Container */}
            <div
              ref={containerRef}
              style={{
                flex: 1,
                width: '100%',
                backgroundColor: '#090d16',
                borderRadius: '8px',
                border: '1px solid var(--border)',
              }}
            />
          </div>
        )}

        {/* PANE 3: Forensic Detail Inspector */}
        <div
          className="glass-panel"
          style={{
            padding: '20px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '14px' }}>
            <span className="badge badge-accent">INSPECTOR</span>
            <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
              Forensic Details
            </h3>
          </div>

          {selectedEdge ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.2rem' }}>{getRuleIcon(selectedEdge.link_type)}</span>
                <span style={{ fontWeight: 800, color: '#f8fafc', fontSize: '0.95rem' }}>
                  {selectedEdge.link_type}
                </span>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700 }}>LINKED ARTIFACTS</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--accent)', fontWeight: 700, marginTop: '2px' }}>
                  {selectedEdge.source} ⟷ {selectedEdge.target}
                </div>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700 }}>CONFIDENCE METRIC</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--warning)', marginTop: '2px' }}>
                  {Math.round((selectedEdge.confidence || 0.8) * 100)}%
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>
                  FORENSIC RATIONALE
                </div>
                <div
                  style={{
                    backgroundColor: 'rgba(15, 23, 42, 0.7)',
                    padding: '10px',
                    borderRadius: '6px',
                    border: '1px solid var(--border)',
                    fontSize: '0.82rem',
                    color: 'var(--text-primary)',
                    lineHeight: 1.5,
                  }}
                >
                  {selectedEdge.reason}
                </div>
              </div>

              {selectedEdge.supporting_fields && (
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>
                    SUPPORTING TELEMETRY
                  </div>
                  <pre
                    style={{
                      backgroundColor: 'rgba(15, 23, 42, 0.9)',
                      padding: '8px',
                      borderRadius: '4px',
                      fontSize: '0.72rem',
                      color: 'var(--accent)',
                      overflowX: 'auto',
                    }}
                  >
                    {JSON.stringify(selectedEdge.supporting_fields, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : selectedNode ? (
            <div>
              <div style={{ marginBottom: '12px' }}>
                <span className="badge badge-accent">{selectedNode.node_type}</span>
                <h4 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f8fafc', marginTop: '6px' }}>
                  {selectedNode.label}
                </h4>
              </div>

              {selectedNode.node_type === 'evidence' ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Evidence ID: </span>
                    <strong style={{ color: '#f8fafc' }}>{selectedNode.id}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Modality Type: </span>
                    <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}>
                      {selectedNode.evidence_type}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>SHA-256 Digest: </span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontSize: '0.75rem' }}>
                      {selectedNode.sha256}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Timestamp: </span>
                    <span style={{ color: '#f8fafc' }}>{selectedNode.time}</span>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Entity Class: </span>
                    <strong style={{ color: '#f8fafc' }}>{selectedNode.entity_type}</strong>
                  </div>
                  <div style={{ marginTop: '6px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Value: </span>
                    <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{selectedNode.value}</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '8px' }}>👆</div>
              Click any correlation card on the left or node/edge on the map to inspect full forensic telemetry.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
