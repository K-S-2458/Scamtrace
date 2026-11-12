import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import {
  apiCorrelate,
  apiGetEvidenceList,
  apiGetGraph,
  EvidenceItem,
  GraphResponse,
} from '../api/client';
import {
  CorrelationEdgeData,
  EvidenceCorrelationMatrix,
} from '../components/EvidenceCorrelationMatrix';

interface RelationshipExplorerProps {
  activeCaseId: string | null;
}

export const RelationshipExplorer: React.FC<RelationshipExplorerProps> = ({ activeCaseId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<any | null>(null);
  const [linkFilter, setLinkFilter] = useState<string>('ALL');
  const [showEntities, setShowEntities] = useState<boolean>(false);
  const [correlating, setCorrelating] = useState(false);
  const [viewMode, setViewMode] = useState<'matrix' | 'graph' | 'ledger'>('matrix');

  const loadData = async () => {
    if (!activeCaseId) {
      setGraphData(null);
      setEvidenceList([]);
      return;
    }
    try {
      const [gData, evData] = await Promise.all([
        apiGetGraph(activeCaseId),
        apiGetEvidenceList(activeCaseId),
      ]);
      setGraphData(gData);
      setEvidenceList(evData);
    } catch (e: any) {
      console.error('Failed to load relationship data', e);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeCaseId]);

  const handleRunCorrelation = async () => {
    if (!activeCaseId) return;
    setCorrelating(true);
    try {
      await apiCorrelate(activeCaseId);
      await loadData();
    } catch (err: any) {
      alert(`Correlation error: ${err.message}`);
    } finally {
      setCorrelating(false);
    }
  };

  // Correlation edges (excluding raw CONTAINS_ENTITY bridge links)
  const correlationEdges =
    graphData?.elements.edges
      .filter((e) => e.data.link_type !== 'CONTAINS_ENTITY')
      .map((e) => e.data as CorrelationEdgeData) || [];

  const filteredCorrelationEdges =
    linkFilter === 'ALL'
      ? correlationEdges
      : correlationEdges.filter((e) => e.link_type === linkFilter);

  // Initialize and update Cytoscape graph (when graph view is active)
  useEffect(() => {
    if (viewMode !== 'graph' || !containerRef.current || !graphData) return;

    const filteredNodes = showEntities
      ? graphData.elements.nodes
      : graphData.elements.nodes.filter((n) => n.data.node_type === 'evidence');

    let activeEdges = graphData.elements.edges.filter(
      (e) => e.data.link_type !== 'CONTAINS_ENTITY' && (linkFilter === 'ALL' || e.data.link_type === linkFilter)
    );

    if (showEntities) {
      const containsEdges = graphData.elements.edges.filter((e) => e.data.link_type === 'CONTAINS_ENTITY');
      activeEdges = [...activeEdges, ...containsEdges];
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
            'background-color': '#5236ec',
            label: 'data(label)',
            color: '#0f172a',
            'font-size': '11px',
            'font-weight': 'bold',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            width: 36,
            height: 36,
            'border-width': 2,
            'border-color': '#c7d2fe',
          },
        },
        {
          selector: 'node[node_type = "entity"]',
          style: {
            'background-color': '#94a3b8',
            label: 'data(label)',
            color: '#64748b',
            'font-size': '9px',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            width: 18,
            height: 18,
            'border-width': 1,
            'border-color': '#cbd5e1',
          },
        },
        {
          selector: 'edge[link_type = "CONTAINS_ENTITY"]',
          style: {
            width: 1,
            'line-color': '#cbd5e1',
            'curve-style': 'bezier',
            opacity: 0.5,
          },
        },
        {
          selector: 'edge[link_type != "CONTAINS_ENTITY"]',
          style: {
            width: 2.5,
            'line-color': '#5236ec',
            'target-arrow-color': '#5236ec',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(link_type)',
            'font-size': '9px',
            'font-weight': 'bold',
            color: '#5236ec',
            'text-background-opacity': 0.95,
            'text-background-color': '#ffffff',
            'text-background-padding': '3px',
            'text-border-opacity': 0.5,
            'text-border-color': '#ddd6fe',
            'text-border-width': 1,
          },
        },
        {
          selector: ':selected',
          style: {
            'border-width': 3,
            'border-color': '#e11d48',
            'line-color': '#e11d48',
            'target-arrow-color': '#e11d48',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 40,
        nodeRepulsion: () => 7000,
        idealEdgeLength: () => 120,
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
  }, [graphData, linkFilter, showEntities, viewMode]);

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

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Top Header & Action Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="f-badge f-badge-accent">EVIDENCE RELATIONSHIP ENGINE</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Deterministic Rule Matching</span>
          </div>
          <h1 style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginTop: '2px' }}>
            Evidence Relationships & Correlation
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '2px' }}>
            Interactive artifact-by-artifact correlation matrix identifying cross-channel telephony, spoofed domains, and malware sequences.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleRunCorrelation}
            disabled={correlating || !activeCaseId}
            className="f-btn f-btn-primary"
            style={{ fontSize: '0.82rem' }}
          >
            {correlating ? 'Evaluating Rules...' : '🔄 Run Correlation Engine'}
          </button>
        </div>
      </div>

      {/* View Mode Switcher and Options Bar */}
      <div
        className="forensic-panel"
        style={{
          padding: '10px 18px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        {/* Left: View Mode Selectors */}
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            onClick={() => setViewMode('matrix')}
            className={viewMode === 'matrix' ? 'f-btn f-btn-primary' : 'f-btn f-btn-outline'}
            style={{ fontSize: '0.78rem', padding: '6px 14px' }}
          >
            ▦ Correlation Matrix (Primary)
          </button>
          <button
            onClick={() => setViewMode('ledger')}
            className={viewMode === 'ledger' ? 'f-btn f-btn-primary' : 'f-btn f-btn-outline'}
            style={{ fontSize: '0.78rem', padding: '6px 14px' }}
          >
            📋 Discovered Links Ledger ({correlationEdges.length})
          </button>
          <button
            onClick={() => setViewMode('graph')}
            className={viewMode === 'graph' ? 'f-btn f-btn-primary' : 'f-btn f-btn-outline'}
            style={{ fontSize: '0.78rem', padding: '6px 14px' }}
          >
            🕸️ Network Topology Graph
          </button>
        </div>

        {/* Right: Quick Stats & Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>FILTER:</span>
            <select
              className="f-select"
              style={{ width: 'auto', padding: '4px 8px', fontSize: '0.78rem' }}
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

          {viewMode === 'graph' && (
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={showEntities}
                onChange={(e) => setShowEntities(e.target.checked)}
              />
              <span>Show Entity Bridge Nodes</span>
            </label>
          )}
        </div>
      </div>

      {/* PRIMARY INTERFACE: Interactive Evidence Correlation Matrix */}
      {viewMode === 'matrix' && (
        <EvidenceCorrelationMatrix
          evidenceList={evidenceList}
          edges={filteredCorrelationEdges}
        />
      )}

      {/* SECONDARY INTERFACE: Forensic Link Ledger */}
      {viewMode === 'ledger' && (
        <div style={{ display: 'grid', gridTemplateColumns: selectedEdge ? '1fr 380px' : '1fr', gap: '20px' }}>
          <div className="forensic-panel">
            <div className="forensic-panel-header">
              <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)', textTransform: 'uppercase' }}>
                Correlated Artifact Connections ({filteredCorrelationEdges.length})
              </span>
            </div>

            <div className="forensic-panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {filteredCorrelationEdges.length === 0 ? (
                <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '1.8rem', marginBottom: '8px' }}>🔍</div>
                  <div style={{ fontWeight: 600 }}>No cross-artifact correlations found.</div>
                  <div style={{ fontSize: '0.78rem', marginTop: '4px' }}>
                    Click "Run Correlation Engine" above or ingest evidence sharing phone numbers, domains, or brand lures.
                  </div>
                </div>
              ) : (
                filteredCorrelationEdges.map((edge, idx) => {
                  const isSelected = selectedEdge?.id === edge.id;
                  const conf = edge.confidence || 0.8;
                  const confPct = Math.round(conf * 100);
                  const strength = conf >= 0.85 ? 'Strong' : conf >= 0.5 ? 'Possible' : 'Weak';
                  const strengthClass =
                    strength === 'Strong'
                      ? 'f-badge-success'
                      : strength === 'Possible'
                      ? 'f-badge-suspicious'
                      : 'f-badge-low';
                  const icon = getRuleIcon(edge.link_type);

                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedEdge(edge)}
                      style={{
                        padding: '12px 14px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        border: isSelected ? '1px solid var(--accent)' : '1px solid var(--border)',
                        backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'var(--bg-table-header)',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '1.1rem' }}>{icon}</span>
                          <div>
                            <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                              {edge.link_type.replace(/_/g, ' ')}
                            </strong>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                              Artifact <strong style={{ color: 'var(--accent)' }}>{edge.source}</strong> ⟷ Artifact <strong style={{ color: 'var(--accent)' }}>{edge.target}</strong>
                            </div>
                          </div>
                        </div>

                        <span className={`f-badge ${strengthClass}`} style={{ fontSize: '0.68rem' }}>
                          {strength} ({confPct}%)
                        </span>
                      </div>

                      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45, margin: '6px 0 0' }}>
                        {edge.reason}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Ledger Inspector Side Drawer */}
          {selectedEdge && (
            <div className="forensic-panel" style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="forensic-panel-header">
                <div>
                  <span className="f-badge f-badge-accent">LINK DETAILS</span>
                  <div style={{ fontWeight: 800, fontSize: '0.92rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                    {selectedEdge.source} ⟷ {selectedEdge.target}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedEdge(null)}
                  className="f-btn f-btn-outline"
                  style={{ padding: '2px 8px', fontSize: '0.72rem' }}
                >
                  ✕ Close
                </button>
              </div>

              <div className="forensic-panel-body" style={{ fontSize: '0.8rem' }}>
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700 }}>RULE IDENTIFIER</div>
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                    {selectedEdge.link_type}
                  </div>
                </div>

                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700 }}>CONFIDENCE</div>
                  <div style={{ fontWeight: 700, color: 'var(--accent)', marginTop: '2px' }}>
                    {Math.round((selectedEdge.confidence || 0.8) * 100)}%
                  </div>
                </div>

                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700 }}>EXPLANATION</div>
                  <p style={{ color: 'var(--text-secondary)', marginTop: '2px', lineHeight: 1.45 }}>
                    {selectedEdge.reason}
                  </p>
                </div>

                {selectedEdge.supporting_fields && (
                  <div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>
                      TELEMETRY DATA
                    </div>
                    <pre
                      style={{
                        backgroundColor: 'var(--bg-table-header)',
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
            </div>
          )}
        </div>
      )}

      {/* SECONDARY INTERFACE: Network Topology Canvas */}
      {viewMode === 'graph' && (
        <div style={{ display: 'grid', gridTemplateColumns: (selectedNode || selectedEdge) ? '1fr 340px' : '1fr', gap: '20px' }}>
          <div
            className="forensic-panel"
            style={{
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              height: '600px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                {showEntities ? 'Displaying Evidence Nodes & Entity Bridges' : 'Displaying Direct Artifact Connections'}
              </span>

              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  onClick={() => cyRef.current?.fit(undefined, 30)}
                  className="f-btn f-btn-outline"
                  style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                >
                  Fit View
                </button>
                <button
                  onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
                  className="f-btn f-btn-outline"
                  style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                >
                  +
                </button>
                <button
                  onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
                  className="f-btn f-btn-outline"
                  style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                >
                  -
                </button>
              </div>
            </div>

            <div
              ref={containerRef}
              style={{
                flex: 1,
                width: '100%',
                backgroundColor: 'var(--bg-table-header)',
                borderRadius: '4px',
                border: '1px solid var(--border)',
              }}
            />
          </div>

          {/* Graph Inspector Side Panel */}
          {(selectedNode || selectedEdge) && (
            <div className="forensic-panel" style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="forensic-panel-header">
                <div>
                  <span className="f-badge f-badge-accent">GRAPH INSPECTOR</span>
                  <div style={{ fontWeight: 800, fontSize: '0.92rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                    {selectedEdge ? `${selectedEdge.source} ⟷ ${selectedEdge.target}` : selectedNode?.label}
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedNode(null);
                    setSelectedEdge(null);
                  }}
                  className="f-btn f-btn-outline"
                  style={{ padding: '2px 8px', fontSize: '0.72rem' }}
                >
                  ✕ Close
                </button>
              </div>

              <div className="forensic-panel-body" style={{ fontSize: '0.8rem' }}>
                {selectedEdge ? (
                  <div>
                    <div style={{ marginBottom: '8px' }}>
                      <span className="f-badge f-badge-suspicious">{selectedEdge.link_type}</span>
                    </div>
                    <div style={{ color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: 1.45 }}>
                      {selectedEdge.reason}
                    </div>
                    <div style={{ color: 'var(--accent)', fontWeight: 700 }}>
                      Confidence: {Math.round((selectedEdge.confidence || 0.8) * 100)}%
                    </div>
                  </div>
                ) : selectedNode ? (
                  <div>
                    <div style={{ marginBottom: '8px' }}>
                      <span className="f-badge f-badge-accent">{selectedNode.node_type}</span>
                    </div>
                    {selectedNode.node_type === 'evidence' ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div>ID: <strong>{selectedNode.id}</strong></div>
                        <div>Type: <strong>{selectedNode.evidence_type}</strong></div>
                        <div style={{ wordBreak: 'break-all', fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
                          SHA-256: {selectedNode.sha256}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div>Type: <strong>{selectedNode.entity_type}</strong></div>
                        <div style={{ color: 'var(--accent)', fontWeight: 700, marginTop: '4px' }}>
                          {selectedNode.value}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};