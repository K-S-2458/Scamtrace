import React, { useEffect, useState } from 'react';
import { apiGetReportJson, apiGetRisk, RiskResponse } from '../api/client';

interface ReportPageProps {
  activeCaseId: string | null;
}

export const ReportPage: React.FC<ReportPageProps> = ({ activeCaseId }) => {
  const [riskData, setRiskData] = useState<RiskResponse | null>(null);
  const [reportJson, setReportJson] = useState<any | null>(null);

  const loadData = async () => {
    if (!activeCaseId) return;
    try {
      const [rData, jData] = await Promise.all([
        apiGetRisk(activeCaseId),
        apiGetReportJson(activeCaseId),
      ]);
      setRiskData(rData);
      setReportJson(jData);
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeCaseId]);

  const handleOpenHtmlReport = () => {
    if (!activeCaseId) return;
    window.open(`/api/cases/${activeCaseId}/report`, '_blank');
  };

  const handleDownloadJson = () => {
    if (!reportJson) return;
    const blob = new Blob([JSON.stringify(reportJson, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `scamtrace_report_${activeCaseId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!activeCaseId) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Please select an investigation case from the Dashboard first.
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Forensic Report & Audit</h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Tamper-evident, fully traceable case report with strict claim-to-evidence citation verification.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleOpenHtmlReport}
            style={{
              backgroundColor: 'var(--accent)',
              color: '#0f172a',
              border: 'none',
              padding: '10px 18px',
              borderRadius: '6px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            ↗ Open Audited HTML Report
          </button>
          <button
            onClick={handleDownloadJson}
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              border: 'none',
              padding: '10px 18px',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            ↓ Export Structured JSON
          </button>
        </div>
      </div>

      {/* Risk Assessment Summary Card */}
      {riskData && (
        <div
          style={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '24px',
            marginBottom: '24px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--accent)', fontWeight: 600 }}>
                CASE RISK EVALUATION
              </span>
              <h2 style={{ fontSize: '1.3rem', margin: '4px 0' }}>Multi-Factor Threat Assessment</h2>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span
                style={{
                  fontSize: '1rem',
                  fontWeight: 800,
                  padding: '6px 14px',
                  borderRadius: '4px',
                  backgroundColor:
                    riskData.risk_band === 'high'
                      ? 'rgba(239, 68, 68, 0.2)'
                      : riskData.risk_band === 'medium'
                      ? 'rgba(245, 158, 11, 0.2)'
                      : 'rgba(16, 185, 129, 0.2)',
                  color:
                    riskData.risk_band === 'high'
                      ? 'var(--danger)'
                      : riskData.risk_band === 'medium'
                      ? 'var(--warning)'
                      : 'var(--success)',
                }}
              >
                {riskData.risk_band.toUpperCase()} RISK ({(riskData.final_score).toFixed(2)} / 1.00)
              </span>
            </div>
          </div>

          {/* Breakdown Table */}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', marginTop: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '10px 8px' }}>Risk Factor</th>
                <th style={{ padding: '10px 8px' }}>Raw Value</th>
                <th style={{ padding: '10px 8px' }}>Weight</th>
                <th style={{ padding: '10px 8px' }}>Contribution</th>
                <th style={{ padding: '10px 8px' }}>Supporting Evidence</th>
                <th style={{ padding: '10px 8px' }}>Explanation</th>
              </tr>
            </thead>
            <tbody>
              {riskData.breakdown.map((f, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px 8px', fontWeight: 600 }}>{f.factor_name}</td>
                  <td style={{ padding: '10px 8px' }}>{(f.raw_value).toFixed(2)}</td>
                  <td style={{ padding: '10px 8px' }}>{(f.weight).toFixed(2)}</td>
                  <td style={{ padding: '10px 8px', color: 'var(--accent)', fontWeight: 600 }}>
                    +{(f.contribution).toFixed(2)}
                  </td>
                  <td style={{ padding: '10px 8px' }}>
                    {f.evidence_ids.length > 0
                      ? f.evidence_ids.map((id) => (
                          <span
                            key={id}
                            style={{
                              marginRight: '4px',
                              padding: '2px 6px',
                              borderRadius: '3px',
                              backgroundColor: 'var(--bg-tertiary)',
                              fontSize: '0.75rem',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            {id}
                          </span>
                        ))
                      : '-'}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {f.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Traceable Claim Summary Preview */}
      {reportJson && (
        <div
          style={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '24px',
            marginBottom: '24px',
          }}
        >
          <h2 style={{ fontSize: '1.2rem', marginBottom: '14px' }}>
            Traceable Incident Narrative Claims ({reportJson.case_summary_claims.length})
          </h2>
          <ul style={{ paddingLeft: '20px', fontSize: '0.9rem' }}>
            {reportJson.case_summary_claims.map((claim: any, idx: number) => (
              <li key={idx} style={{ marginBottom: '10px' }}>
                <span>{claim.claim_text}</span>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Rule Trigger: <code>{claim.rule_id}</code> | Citations:{' '}
                  {claim.evidence_ids.map((id: string) => (
                    <code key={id} style={{ color: 'var(--accent)', marginRight: '4px' }}>
                      {id}
                    </code>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Forensic Disclaimers & Limitations Section */}
      <div
        style={{
          backgroundColor: 'rgba(51, 65, 85, 0.3)',
          borderLeft: '4px solid var(--text-secondary)',
          borderRadius: '4px',
          padding: '16px 20px',
        }}
      >
        <h3 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '8px' }}>
          Forensic System Boundaries & Disclaimers (Section 2 & 6 Compliance)
        </h3>
        <ul style={{ margin: '0 0 0 16px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          <li>SCAMTRACE outputs are investigative decision-support aids, not definitive legal evidence.</li>
          <li>All URL features are extracted purely offline without live DNS, WHOIS queries, or HTTP redirect following.</li>
          <li>APK analysis operates strictly on static manifest and certificate structures; no bytecode is ever executed or emulated.</li>
          <li>Screenshot analysis provides cryptographic SHA-256 integrity and dimensional metadata without OCR processing.</li>
          <li>Risk scores are transparent triage ranking heuristics and are not calibrated to absolute posterior probabilities of guilt.</li>
        </ul>
      </div>
    </div>
  );
};
