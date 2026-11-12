import React, { useState } from 'react';
import { RiskResponse } from '../api/client';

interface RiskAssessmentCardProps {
  risk: RiskResponse | null;
  evidenceCount: number;
  connectedArtifactsCount: number;
  suspiciousIndicatorsCount: number;
  evidenceConfidence: number; // 0 to 100
}

export const RiskAssessmentCard: React.FC<RiskAssessmentCardProps> = ({
  risk,
  evidenceCount,
  connectedArtifactsCount,
  suspiciousIndicatorsCount,
  evidenceConfidence,
}) => {
  const [breakdownOpen, setBreakdownOpen] = useState(false);

  // Raw score is 0.0 to 1.0; overall score is 0–100
  const score = risk ? Math.min(100, Math.max(0, Math.round(risk.final_score * 100))) : 0;

  // 5-Level Classification
  const getRiskTier = (val: number) => {
    if (val <= 19) return { label: 'LOW', color: 'var(--risk-low)', badgeClass: 'f-badge-low' };
    if (val <= 39) return { label: 'GUARDED', color: 'var(--risk-guarded)', badgeClass: 'f-badge-guarded' };
    if (val <= 59) return { label: 'SUSPICIOUS', color: 'var(--risk-suspicious)', badgeClass: 'f-badge-suspicious' };
    if (val <= 79) return { label: 'HIGH', color: 'var(--risk-high)', badgeClass: 'f-badge-high' };
    return { label: 'CRITICAL', color: 'var(--risk-critical)', badgeClass: 'f-badge-critical' };
  };

  const tier = getRiskTier(score);
  const displayConfidence = evidenceConfidence > 1 ? Math.round(evidenceConfidence) : Math.round(evidenceConfidence * 100);

  return (
    <div className="forensic-panel" style={{ overflow: 'hidden' }}>
      <div className="forensic-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.9rem', color: 'var(--accent)' }}>🛡️</span>
          <span style={{ fontWeight: 700, fontSize: '0.88rem', letterSpacing: '0.02em', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
            Case Risk Assessment
          </span>
        </div>
        <span className={`f-badge ${tier.badgeClass}`}>
          {tier.label} ({score}/100)
        </span>
      </div>

      <div className="forensic-panel-body">
        {/* Top Score & Scale Display */}
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
              Overall Incident Risk Score
            </div>
            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: tier.color, lineHeight: 1.1 }}>
              {score}
              <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 500, marginLeft: '4px' }}>
                / 100
              </span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Triage Classification: <strong style={{ color: tier.color }}>{tier.label}</strong>
            </span>
          </div>
        </div>

        {/* 5-Level Segmented Horizontal Risk Scale */}
        <div style={{ position: 'relative', marginTop: '14px', marginBottom: '22px' }}>
          {/* Segmented Track */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '4px',
              height: '10px',
              borderRadius: '6px',
              overflow: 'hidden',
              backgroundColor: '#f1f5f9',
            }}
          >
            <div style={{ backgroundColor: 'var(--risk-low)', opacity: score >= 0 && score <= 19 ? 1 : 0.25 }} title="Low: 0–19" />
            <div style={{ backgroundColor: 'var(--risk-guarded)', opacity: score >= 20 && score <= 39 ? 1 : 0.25 }} title="Guarded: 20–39" />
            <div style={{ backgroundColor: 'var(--risk-suspicious)', opacity: score >= 40 && score <= 59 ? 1 : 0.25 }} title="Suspicious: 40–59" />
            <div style={{ backgroundColor: 'var(--risk-high)', opacity: score >= 60 && score <= 79 ? 1 : 0.25 }} title="High: 60–79" />
            <div style={{ backgroundColor: 'var(--risk-critical)', opacity: score >= 80 ? 1 : 0.25 }} title="Critical: 80–100" />
          </div>

          {/* Marker Needle / Pin */}
          <div
            style={{
              position: 'absolute',
              top: '-6px',
              left: `${Math.min(98, Math.max(2, score))}%`,
              transform: 'translateX(-50%)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              pointerEvents: 'none',
              transition: 'left 0.3s ease',
            }}
          >
            <div
              style={{
                width: '14px',
                height: '14px',
                backgroundColor: '#ffffff',
                border: `3px solid ${tier.color}`,
                borderRadius: '50%',
                boxShadow: '0 1px 4px rgba(0,0,0,0.25)',
              }}
            />
            <div style={{ width: '2px', height: '10px', backgroundColor: tier.color }} />
          </div>

          {/* Scale Labels */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              marginTop: '8px',
              fontSize: '0.68rem',
              color: 'var(--text-muted)',
              textAlign: 'center',
              fontWeight: 600,
            }}
          >
            <span style={{ color: score <= 19 ? 'var(--text-primary)' : 'inherit' }}>LOW (0–19)</span>
            <span style={{ color: score >= 20 && score <= 39 ? 'var(--text-primary)' : 'inherit' }}>GUARDED (20–39)</span>
            <span style={{ color: score >= 40 && score <= 59 ? 'var(--text-primary)' : 'inherit' }}>SUSPICIOUS (40–59)</span>
            <span style={{ color: score >= 60 && score <= 79 ? 'var(--text-primary)' : 'inherit' }}>HIGH (60–79)</span>
            <span style={{ color: score >= 80 ? 'var(--text-primary)' : 'inherit' }}>CRITICAL (80–100)</span>
          </div>
        </div>

        {/* 4-Item Indicator Grid Below Scale */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: '12px',
            backgroundColor: 'var(--bg-table-header)',
            padding: '12px 14px',
            borderRadius: '4px',
            border: '1px solid var(--border)',
            marginBottom: '14px',
          }}
        >
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              Risk Classification
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: tier.color, marginTop: '2px' }}>
              {tier.label}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              Evidence Confidence
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
              {displayConfidence}%
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400, marginLeft: '4px' }}>
                (Certitude)
              </span>
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              Suspicious Indicators
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
              {suspiciousIndicatorsCount} Detected
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              Connected Artifacts
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
              {connectedArtifactsCount} of {evidenceCount} Linked
            </div>
          </div>
        </div>

        {/* Collapsible Factor Breakdown */}
        {risk?.breakdown && risk.breakdown.length > 0 && (
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
            <button
              type="button"
              onClick={() => setBreakdownOpen(!breakdownOpen)}
              className="f-btn f-btn-outline"
              style={{
                width: '100%',
                justifyContent: 'space-between',
                padding: '6px 10px',
                fontSize: '0.78rem',
              }}
            >
              <span>
                {breakdownOpen ? '▲ Hide Risk Factor Breakdown' : '▼ View Contributing Factor Breakdown (' + risk.breakdown.length + ' Factors)'}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Weights: Artifact 40% | Correlation 40% | Pattern 20%
              </span>
            </button>

            {breakdownOpen && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
                {risk.breakdown.map((f, idx) => {
                  const contribPts = Math.round(f.contribution * 100 * 10) / 10;
                  return (
                    <div
                      key={idx}
                      style={{
                        backgroundColor: 'var(--bg-secondary)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '4px',
                        padding: '10px 12px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                          {f.factor_name}
                        </span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent)' }}>
                          +{contribPts} pts (wt: {f.weight})
                        </span>
                      </div>

                      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '2px 0 6px' }}>
                        {f.description}
                      </p>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                          SUPPORTING EVIDENCE:
                        </span>
                        {f.evidence_ids && f.evidence_ids.length > 0 ? (
                          f.evidence_ids.map((eid) => (
                            <span
                              key={eid}
                              className="f-badge f-badge-accent"
                              style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}
                            >
                              {eid}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>None triggered</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Disclaimer Note */}
        <div style={{ marginTop: '10px', fontSize: '0.7rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
          * {risk?.disclaimer || 'SCAMTRACE risk score is an investigative triage aid, not legal proof of guilt, and is not calibrated to posterior probabilities.'} Evidence confidence reflects classifier certainty, distinct from threat severity.
        </div>
      </div>
    </div>
  );
};
