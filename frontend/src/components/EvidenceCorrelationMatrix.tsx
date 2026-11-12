import React, { useState, useMemo } from 'react';
import { EvidenceItem } from '../api/client';

export interface CorrelationEdgeData {
  id: string;
  source: string;
  target: string;
  link_type: string;
  confidence?: number;
  reason?: string;
  supporting_fields?: any;
  rule_version?: string;
}

interface EvidenceCorrelationMatrixProps {
  evidenceList: EvidenceItem[];
  edges: CorrelationEdgeData[];
  onSelectPair?: (evA: EvidenceItem, evB: EvidenceItem, edges: CorrelationEdgeData[]) => void;
}

export const EvidenceCorrelationMatrix: React.FC<EvidenceCorrelationMatrixProps> = ({
  evidenceList,
  edges,
}) => {
  const [selectedPair, setSelectedPair] = useState<{
    rowEv: EvidenceItem;
    colEv: EvidenceItem;
    matchedEdges: CorrelationEdgeData[];
  } | null>(null);

  const [sortBy, setSortBy] = useState<'id' | 'type' | 'time'>('id');
  const [searchTerm, setSearchTerm] = useState('');

  // Filter and sort evidence list
  const sortedEvidence = useMemo(() => {
    let list = [...evidenceList];
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(
        (e) =>
          e.id.toLowerCase().includes(q) ||
          e.type.toLowerCase().includes(q) ||
          (e.original_filename || '').toLowerCase().includes(q) ||
          (e.raw_text || '').toLowerCase().includes(q)
      );
    }

    if (sortBy === 'id') {
      list.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
    } else if (sortBy === 'type') {
      list.sort((a, b) => a.type.localeCompare(b.type) || a.id.localeCompare(b.id));
    } else if (sortBy === 'time') {
      list.sort((a, b) => (a.source_timestamp || a.uploaded_at).localeCompare(b.source_timestamp || b.uploaded_at));
    }
    return list;
  }, [evidenceList, sortBy, searchTerm]);

  // Lookup map: (idA, idB) -> list of edges
  const edgeLookup = useMemo(() => {
    const map = new Map<string, CorrelationEdgeData[]>();
    for (const edge of edges) {
      if (edge.link_type === 'CONTAINS_ENTITY') continue;
      const key1 = `${edge.source}|${edge.target}`;
      const key2 = `${edge.target}|${edge.source}`;

      if (!map.has(key1)) map.set(key1, []);
      map.get(key1)!.push(edge);

      if (!map.has(key2)) map.set(key2, []);
      map.get(key2)!.push(edge);
    }
    return map;
  }, [edges]);

  // Get relationship evaluation for cell
  const getCellData = (rowId: string, colId: string) => {
    if (rowId === colId) {
      return { strength: 'self', label: '—', confidence: 0, edges: [] };
    }
    const key = `${rowId}|${colId}`;
    const matched = edgeLookup.get(key) || [];
    if (matched.length === 0) {
      return { strength: 'none', label: '—', confidence: 0, edges: [] };
    }

    const maxConf = Math.max(...matched.map((e) => e.confidence || 0.8));
    if (maxConf >= 0.85 || matched.length >= 2) {
      return { strength: 'strong', label: 'Strong', confidence: maxConf, edges: matched };
    }
    if (maxConf >= 0.5) {
      return { strength: 'possible', label: 'Possible', confidence: maxConf, edges: matched };
    }
    return { strength: 'weak', label: 'Weak', confidence: maxConf, edges: matched };
  };

  const handleCellClick = (rowEv: EvidenceItem, colEv: EvidenceItem) => {
    const key = `${rowEv.id}|${colEv.id}`;
    const matched = edgeLookup.get(key) || [];
    setSelectedPair({
      rowEv,
      colEv,
      matchedEdges: matched,
    });
  };

  const getModalityIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'sms':
        return '✉️';
      case 'phone_call':
      case 'call_log':
        return '📞';
      case 'chat':
        return '💬';
      case 'url':
        return '🌐';
      case 'apk':
        return '📦';
      case 'email_text':
        return '📧';
      case 'screenshot':
        return '🖼️';
      default:
        return '📄';
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: selectedPair ? '1fr 380px' : '1fr', gap: '20px' }}>
      {/* Matrix Table Area */}
      <div className="forensic-panel" style={{ overflow: 'hidden' }}>
        <div className="forensic-panel-header" style={{ flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--accent)' }}>▦</span>
            <span style={{ fontWeight: 700, fontSize: '0.88rem', letterSpacing: '0.02em', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              Evidence Correlation Matrix
            </span>
            <span className="f-badge f-badge-accent" style={{ marginLeft: '6px' }}>
              {sortedEvidence.length} Artifacts × {sortedEvidence.length}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input
              type="text"
              placeholder="Search artifacts..."
              className="f-input"
              style={{ width: '160px', padding: '4px 8px', fontSize: '0.78rem' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>SORT:</span>
              <select
                className="f-select"
                style={{ width: 'auto', padding: '4px 8px', fontSize: '0.78rem' }}
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
              >
                <option value="id">By ID (E1, E2...)</option>
                <option value="type">By Modality</option>
                <option value="time">By Timestamp</option>
              </select>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            padding: '8px 18px',
            backgroundColor: 'var(--bg-table-header)',
            borderBottom: '1px solid var(--border)',
            fontSize: '0.72rem',
            color: 'var(--text-secondary)',
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>RELATIONSHIP STRENGTH:</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#10b981' }} />
            <strong>Strong</strong> (Confidence ≥ 85% or Multi-Rule)
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#f59e0b' }} />
            <strong>Possible</strong> (Confidence 50%–84%)
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#64748b' }} />
            <strong>Weak</strong> (Temporal Proximity Only)
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ color: 'var(--text-muted)' }}>—</span>
            <span>No Identified Link</span>
          </span>
        </div>

        {/* Scrollable Matrix Grid */}
        <div style={{ maxHeight: '540px', overflow: 'auto', padding: '12px' }}>
          {sortedEvidence.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 16px', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '8px' }}>📂</div>
              <p>No evidence artifacts available to correlate in this case.</p>
            </div>
          ) : (
            <table
              style={{
                width: '100%',
                borderCollapse: 'separate',
                borderSpacing: '2px',
                fontSize: '0.8rem',
              }}
            >
              <thead>
                <tr>
                  {/* Top-left corner cell */}
                  <th
                    style={{
                      position: 'sticky',
                      top: 0,
                      left: 0,
                      zIndex: 3,
                      backgroundColor: 'var(--bg-card)',
                      padding: '8px 12px',
                      borderBottom: '2px solid var(--border)',
                      textAlign: 'left',
                      fontSize: '0.7rem',
                      color: 'var(--text-muted)',
                      minWidth: '140px',
                    }}
                  >
                    ARTIFACT
                  </th>
                  {sortedEvidence.map((colEv) => (
                    <th
                      key={colEv.id}
                      style={{
                        position: 'sticky',
                        top: 0,
                        zIndex: 2,
                        backgroundColor: 'var(--bg-card)',
                        padding: '8px 10px',
                        borderBottom: '2px solid var(--border)',
                        textAlign: 'center',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                        minWidth: '100px',
                      }}
                      title={`${colEv.id}: ${colEv.type.toUpperCase()} - ${colEv.original_filename || colEv.sha256.substring(0, 10)}`}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                        <span style={{ fontSize: '0.9rem' }}>{getModalityIcon(colEv.type)}</span>
                        <span>{colEv.id}</span>
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                          {colEv.type.replace('_', ' ')}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedEvidence.map((rowEv) => (
                  <tr key={rowEv.id}>
                    {/* Sticky row header */}
                    <td
                      style={{
                        position: 'sticky',
                        left: 0,
                        zIndex: 1,
                        backgroundColor: 'var(--bg-card)',
                        padding: '8px 12px',
                        borderRight: '2px solid var(--border)',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{getModalityIcon(rowEv.type)}</span>
                        <strong style={{ color: 'var(--accent)' }}>{rowEv.id}</strong>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                          ({rowEv.type.replace('_', ' ')})
                        </span>
                      </div>
                    </td>

                    {/* Matrix Cells */}
                    {sortedEvidence.map((colEv) => {
                      const cell = getCellData(rowEv.id, colEv.id);
                      const isSelf = cell.strength === 'self';
                      const isNone = cell.strength === 'none';
                      const isStrong = cell.strength === 'strong';
                      const isPossible = cell.strength === 'possible';
                      const isWeak = cell.strength === 'weak';

                      const isSelected =
                        selectedPair &&
                        ((selectedPair.rowEv.id === rowEv.id && selectedPair.colEv.id === colEv.id) ||
                          (selectedPair.rowEv.id === colEv.id && selectedPair.colEv.id === rowEv.id));

                      let bgColor = 'var(--bg-input)';
                      let textColor = 'var(--text-muted)';
                      let borderColor = 'transparent';

                      if (isSelf) {
                        bgColor = 'rgba(15, 23, 42, 0.4)';
                      } else if (isStrong) {
                        bgColor = 'rgba(16, 185, 129, 0.12)';
                        textColor = '#34d399';
                        borderColor = 'rgba(16, 185, 129, 0.3)';
                      } else if (isPossible) {
                        bgColor = 'rgba(245, 158, 11, 0.12)';
                        textColor = '#fbbf24';
                        borderColor = 'rgba(245, 158, 11, 0.3)';
                      } else if (isWeak) {
                        bgColor = 'rgba(100, 116, 139, 0.12)';
                        textColor = '#94a3b8';
                        borderColor = 'rgba(100, 116, 139, 0.25)';
                      }

                      if (isSelected) {
                        borderColor = 'var(--accent)';
                        bgColor = 'rgba(56, 189, 248, 0.18)';
                      }

                      return (
                        <td
                          key={colEv.id}
                          onClick={() => !isSelf && handleCellClick(rowEv, colEv)}
                          style={{
                            padding: '10px 8px',
                            textAlign: 'center',
                            backgroundColor: bgColor,
                            color: textColor,
                            border: `1px solid ${borderColor}`,
                            borderRadius: '3px',
                            cursor: isSelf ? 'default' : 'pointer',
                            transition: 'all 0.15s ease',
                            userSelect: 'none',
                          }}
                          title={
                            isSelf
                              ? 'Identical artifact (Self)'
                              : isNone
                              ? `No correlation found between ${rowEv.id} and ${colEv.id}`
                              : `${cell.label} relationship (${cell.edges.length} rule matches, ${Math.round(
                                  cell.confidence * 100
                                )}% confidence). Click to inspect.`
                          }
                        >
                          {isSelf || isNone ? (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>—</span>
                          ) : (
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                fontSize: '0.72rem',
                                fontWeight: 700,
                                textTransform: 'uppercase',
                              }}
                            >
                              <span>{isStrong ? '●' : isPossible ? '◐' : '○'}</span>
                              <span>{cell.label}</span>
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Side Detail Drawer when a relationship cell is clicked */}
      {selectedPair && (
        <div className="forensic-panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="forensic-panel-header">
            <div>
              <span className="f-badge f-badge-accent">RELATIONSHIP INSPECTOR</span>
              <div style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                {selectedPair.rowEv.id} ⟷ {selectedPair.colEv.id}
              </div>
            </div>
            <button
              onClick={() => setSelectedPair(null)}
              className="f-btn f-btn-outline"
              style={{ padding: '2px 8px', fontSize: '0.75rem' }}
            >
              ✕ Close
            </button>
          </div>

          <div className="forensic-panel-body" style={{ overflowY: 'auto', flex: 1 }}>
            {/* Connected Evidence Badges */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '8px',
                marginBottom: '14px',
              }}
            >
              <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700 }}>ARTIFACT 1</div>
                <div style={{ fontWeight: 700, color: 'var(--accent)', fontSize: '0.88rem' }}>
                  {getModalityIcon(selectedPair.rowEv.type)} {selectedPair.rowEv.id}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  {selectedPair.rowEv.type.replace('_', ' ')}
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {selectedPair.rowEv.original_filename || selectedPair.rowEv.sha256.substring(0, 16)}
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700 }}>ARTIFACT 2</div>
                <div style={{ fontWeight: 700, color: 'var(--accent)', fontSize: '0.88rem' }}>
                  {getModalityIcon(selectedPair.colEv.type)} {selectedPair.colEv.id}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  {selectedPair.colEv.type.replace('_', ' ')}
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {selectedPair.colEv.original_filename || selectedPair.colEv.sha256.substring(0, 16)}
                </div>
              </div>
            </div>

            {/* Relationship Status */}
            {selectedPair.matchedEdges.length === 0 ? (
              <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '1.4rem', marginBottom: '6px' }}>⚪</div>
                <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>No Direct Relationship Found</div>
                <p style={{ fontSize: '0.75rem', marginTop: '4px' }}>
                  The correlation engine did not find shared telephony, infrastructure, brand impersonations, or dropper sequences between these two artifacts.
                </p>
              </div>
            ) : (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700 }}>
                    IDENTIFIED CORRELATIONS ({selectedPair.matchedEdges.length})
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {selectedPair.matchedEdges.map((edge, idx) => {
                    const conf = edge.confidence || 0.8;
                    const confPct = Math.round(conf * 100);
                    const strength = conf >= 0.85 ? 'Strong' : conf >= 0.5 ? 'Possible' : 'Weak';
                    const strengthClass =
                      strength === 'Strong'
                        ? 'f-badge-success'
                        : strength === 'Possible'
                        ? 'f-badge-suspicious'
                        : 'f-badge-low';

                    const supp = edge.supporting_fields || {};

                    return (
                      <div
                        key={idx}
                        style={{
                          backgroundColor: 'var(--bg-secondary)',
                          border: '1px solid var(--border)',
                          borderRadius: '4px',
                          padding: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                            {edge.link_type.replace(/_/g, ' ')}
                          </span>
                          <span className={`f-badge ${strengthClass}`} style={{ fontSize: '0.68rem' }}>
                            {strength} ({confPct}%)
                          </span>
                        </div>

                        {/* Plain Language Explanation */}
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45, marginBottom: '8px' }}>
                          {edge.reason}
                        </p>

                        {/* Shared Entity Tags */}
                        {supp && Object.keys(supp).length > 0 && (
                          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', marginTop: '6px' }}>
                            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>
                              CORROBORATING ENTITIES:
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                              {supp.phone && (
                                <span className="f-badge f-badge-accent" style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                                  📞 {supp.phone}
                                </span>
                              )}
                              {supp.domain && (
                                <span className="f-badge f-badge-accent" style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                                  🌐 {supp.domain}
                                </span>
                              )}
                              {supp.brand && (
                                <span className="f-badge f-badge-accent" style={{ fontSize: '0.68rem' }}>
                                  🏦 {supp.brand}
                                </span>
                              )}
                              {supp.package_name && (
                                <span className="f-badge f-badge-accent" style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                                  📦 {supp.package_name}
                                </span>
                              )}
                              {supp.lure_words && (
                                <span className="f-badge f-badge-accent" style={{ fontSize: '0.68rem' }}>
                                  🔑 {supp.lure_words.join(', ')}
                                </span>
                              )}
                              {supp.similarity && (
                                <span className="f-badge f-badge-accent" style={{ fontSize: '0.68rem' }}>
                                  Sim: {(supp.similarity * 100).toFixed(1)}%
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        <div style={{ marginTop: '8px', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          Rule Version: {edge.rule_version || '1.0'} | Evidence Citing: [{selectedPair.rowEv.id}, {selectedPair.colEv.id}]
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

