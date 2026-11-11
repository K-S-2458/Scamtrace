import React, { useEffect, useState } from 'react';
import { apiGetTimeline, TimelineItem, TimelineResponse } from '../api/client';

interface IncidentTimelineProps {
  activeCaseId: string | null;
}

export const IncidentTimeline: React.FC<IncidentTimelineProps> = ({ activeCaseId }) => {
  const [timelineData, setTimelineData] = useState<TimelineResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<TimelineItem | null>(null);

  const loadTimeline = async () => {
    if (!activeCaseId) return;
    try {
      const data = await apiGetTimeline(activeCaseId);
      setTimelineData(data);
      if (data.timeline.length > 0) {
        setSelectedItem(data.timeline[0]);
      }
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadTimeline();
  }, [activeCaseId]);

  if (!activeCaseId) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Please select an investigation case from the Dashboard first.
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Incident Timeline</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Chronological multi-artifact event reconstruction, inter-event latency gaps, and causal ordering conflict analysis.
        </p>
      </div>

      {/* Conflict Alert Banner */}
      {timelineData?.has_conflicts && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid var(--danger)',
            borderRadius: '6px',
            padding: '16px',
            marginBottom: '24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--danger)', fontWeight: 700 }}>
            <span>⚠ CAUSAL ORDERING CONFLICTS DETECTED</span>
          </div>
          <ul style={{ margin: '8px 0 0 20px', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
            {timelineData.conflicts.map((c, i) => (
              <li key={i}>{c.description}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '24px' }}>
        {/* Left Column: Vertical Timeline */}
        <div
          style={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '24px',
          }}
        >
          {timelineData?.timeline.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No timeline events found for this case.</p>
          ) : (
            <div style={{ position: 'relative', paddingLeft: '32px' }}>
              {/* Vertical Line */}
              <div
                style={{
                  position: 'absolute',
                  top: '12px',
                  bottom: '12px',
                  left: '11px',
                  width: '2px',
                  backgroundColor: 'var(--border)',
                }}
              />

              {timelineData?.timeline.map((item, idx) => {
                const isSelected = selectedItem?.evidence_id === item.evidence_id;
                const hasConflict = item.conflicts && item.conflicts.length > 0;

                return (
                  <div key={item.evidence_id} style={{ marginBottom: '24px', position: 'relative' }}>
                    {/* Circle Node */}
                    <div
                      style={{
                        position: 'absolute',
                        left: '-32px',
                        top: '4px',
                        width: '22px',
                        height: '22px',
                        borderRadius: '50%',
                        backgroundColor: hasConflict ? 'var(--danger)' : isSelected ? 'var(--accent)' : 'var(--bg-tertiary)',
                        border: '2px solid var(--bg-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        color: isSelected ? '#0f172a' : '#ffffff',
                      }}
                    >
                      {idx + 1}
                    </div>

                    {/* Time Gap Pill */}
                    {item.time_gap_from_prev && (
                      <div
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--text-secondary)',
                          marginBottom: '6px',
                          display: 'inline-block',
                          backgroundColor: 'var(--bg-primary)',
                          padding: '2px 8px',
                          borderRadius: '10px',
                          border: '1px solid var(--border)',
                        }}
                      >
                        +{item.time_gap_from_prev} latency
                      </div>
                    )}

                    {/* Timeline Event Card */}
                    <div
                      onClick={() => setSelectedItem(item)}
                      style={{
                        cursor: 'pointer',
                        padding: '14px 16px',
                        borderRadius: '6px',
                        border: isSelected ? '1px solid var(--accent)' : '1px solid var(--border)',
                        backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'var(--bg-primary)',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 800, color: 'var(--accent)' }}>{item.evidence_id}</span>
                          <span
                            style={{
                              fontSize: '0.75rem',
                              padding: '2px 6px',
                              borderRadius: '3px',
                              backgroundColor: 'var(--bg-tertiary)',
                              textTransform: 'uppercase',
                            }}
                          >
                            {item.type}
                          </span>
                        </div>

                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {item.timestamp || 'Time Uncertain'}
                          {item.time_uncertain && (
                            <span style={{ color: 'var(--warning)', marginLeft: '6px', fontWeight: 600 }}>
                              (Time Uncertain)
                            </span>
                          )}
                        </div>
                      </div>

                      <p style={{ margin: '8px 0 0 0', fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                        {item.summary}
                      </p>

                      {hasConflict && (
                        <div
                          style={{
                            marginTop: '8px',
                            color: 'var(--danger)',
                            fontSize: '0.8rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          ⚠ {item.conflicts[0]}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Event Inspector */}
        <div>
          <div
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '20px',
            }}
          >
            <h2 style={{ fontSize: '1.15rem', marginBottom: '14px' }}>Event Inspector</h2>
            {selectedItem ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                <div>Evidence ID: <strong>{selectedItem.evidence_id}</strong></div>
                <div>Modality: <strong>{selectedItem.type.toUpperCase()}</strong></div>
                <div>Timestamp: {selectedItem.timestamp || 'Uncertain'}</div>
                <div>Source of Time: <code>{selectedItem.timestamp_source}</code></div>
                <div>Filename: {selectedItem.original_filename || '-'}</div>

                <div style={{ marginTop: '10px' }}>
                  <div style={{ color: 'var(--text-secondary)', marginBottom: '4px' }}>Event Summary:</div>
                  <div
                    style={{
                      padding: '10px',
                      backgroundColor: 'var(--bg-primary)',
                      borderRadius: '4px',
                      borderLeft: '3px solid var(--accent)',
                    }}
                  >
                    {selectedItem.summary}
                  </div>
                </div>

                {selectedItem.conflicts.length > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    <div style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: '4px' }}>
                      Causal Ordering Flags:
                    </div>
                    {selectedItem.conflicts.map((c, i) => (
                      <div
                        key={i}
                        style={{
                          padding: '8px',
                          backgroundColor: 'rgba(239, 68, 68, 0.1)',
                          color: 'var(--danger)',
                          borderRadius: '4px',
                          marginBottom: '4px',
                        }}
                      >
                        {c}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Select any timeline event to view chronological details.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
