import React, { useState } from 'react';
import { FindingsResponse } from '../api/client';

interface InvestigationFindingsCardProps {
  findings: FindingsResponse | null;
  loading?: boolean;
}

export const InvestigationFindingsCard: React.FC<InvestigationFindingsCardProps> = ({
  findings,
  loading,
}) => {
  const [activeEntityTab, setActiveEntityTab] = useState<
    'phones' | 'domains' | 'upi' | 'packages' | 'certs' | 'brands' | 'amounts'
  >('phones');

  if (loading) {
    return (
      <div className="forensic-panel" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
        Compiling investigation findings from evidence records...
      </div>
    );
  }

  if (!findings) {
    return (
      <div className="forensic-panel" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No investigation findings available for this case. Ingest evidence to begin.
      </div>
    );
  }

  const entities = findings.identified_entities;
  const conclusion = findings.conclusion;

  const entityTabs: Array<{
    id: typeof activeEntityTab;
    label: string;
    icon: string;
    items: Array<{ value: string; raw_value: string; evidence_ids: string[] }>;
  }> = [
    { id: 'phones', label: 'Phone Numbers', icon: '📞', items: entities.phone_numbers || [] },
    { id: 'domains', label: 'Domains', icon: '🌐', items: entities.domains || [] },
    { id: 'upi', label: 'UPI Handles', icon: '💳', items: entities.upi_handles || [] },
    { id: 'packages', label: 'Package Names', icon: '📦', items: entities.package_names || [] },
    { id: 'certs', label: 'Certificate Hashes', icon: '🔐', items: entities.certificate_hashes || [] },
    { id: 'brands', label: 'Brand Mentions', icon: '🏦', items: entities.brand_names || [] },
    { id: 'amounts', label: 'Financial Amounts', icon: '💰', items: entities.amounts || [] },
  ];

  const activeTabObj = entityTabs.find((t) => t.id === activeEntityTab)!;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* SECTION B: Key Findings (Displayed prominently) */}
      <div className="forensic-panel">
        <div className="forensic-panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--accent)' }}>📋</span>
            <span style={{ fontWeight: 700, fontSize: '0.88rem', letterSpacing: '0.02em', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              Key Investigation Findings
            </span>
          </div>
          <span className="f-badge f-badge-accent">
            {findings.key_findings.length} Automated Findings
          </span>
        </div>

        <div className="forensic-panel-body">
          {findings.key_findings.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              No correlation edges or high-threat artifacts identified yet. Add corroborating evidence to evaluate findings.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '12px' }}>
              {findings.key_findings.map((f, idx) => {
                const confPct = Math.round(f.confidence * 100);
                const isStrong = f.strength === 'Strong' || f.strength === 'High';
                const isPossible = f.strength === 'Possible' || f.strength === 'Moderate';
                const badgeClass = isStrong ? 'f-badge-success' : isPossible ? 'f-badge-suspicious' : 'f-badge-low';

                return (
                  <div
                    key={idx}
                    style={{
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border)',
                      borderRadius: '4px',
                      padding: '12px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                        <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                          {f.title}
                        </div>
                        <span className={`f-badge ${badgeClass}`} style={{ fontSize: '0.68rem', whiteSpace: 'nowrap' }}>
                          {f.strength} ({confPct}%)
                        </span>
                      </div>

                      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45, marginBottom: '8px' }}>
                        {f.explanation}
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                        CITING EVIDENCE:
                      </span>
                      {f.evidence_ids.map((eid) => (
                        <span
                          key={eid}
                          className="f-badge f-badge-accent"
                          style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}
                        >
                          {eid}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* SECTION A: Identified Entities */}
      <div className="forensic-panel">
        <div className="forensic-panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--accent)' }}>🏷️</span>
            <span style={{ fontWeight: 700, fontSize: '0.88rem', letterSpacing: '0.02em', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              Identified Entities
            </span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Automatically extracted and canonicalized across all evidence
          </span>
        </div>

        {/* Entity Tabs Navigation */}
        <div
          style={{
            display: 'flex',
            gap: '4px',
            padding: '8px 14px',
            backgroundColor: 'var(--bg-table-header)',
            borderBottom: '1px solid var(--border)',
            overflowX: 'auto',
          }}
        >
          {entityTabs.map((tab) => {
            const isActive = activeEntityTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveEntityTab(tab.id)}
                className={isActive ? 'f-btn f-btn-primary' : 'f-btn f-btn-outline'}
                style={{ fontSize: '0.75rem', padding: '4px 10px', whiteSpace: 'nowrap' }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                <span
                  style={{
                    backgroundColor: isActive ? 'rgba(255,255,255,0.2)' : 'rgba(100,116,139,0.2)',
                    padding: '1px 5px',
                    borderRadius: '9999px',
                    fontSize: '0.68rem',
                    marginLeft: '2px',
                  }}
                >
                  {tab.items.length}
                </span>
              </button>
            );
          })}
        </div>

        {/* Entity Items List Table */}
        <div className="forensic-panel-body" style={{ padding: 0 }}>
          {activeTabObj.items.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              No {activeTabObj.label.toLowerCase()} extracted from current case evidence.
            </div>
          ) : (
            <table className="f-table">
              <thead>
                <tr>
                  <th style={{ width: '40%' }}>Extracted Value</th>
                  <th style={{ width: '35%' }}>Original Raw Text</th>
                  <th style={{ width: '25%' }}>Supporting Evidence IDs</th>
                </tr>
              </thead>
              <tbody>
                {activeTabObj.items.map((ent, idx) => (
                  <tr key={idx}>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent)' }}>
                        {ent.value}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--text-secondary)' }}>
                        {ent.raw_value}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {ent.evidence_ids.map((eid) => (
                          <span
                            key={eid}
                            className="f-badge f-badge-accent"
                            style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}
                          >
                            {eid}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* SECTION C: Investigation Conclusion (Categorized) */}
      <div className="forensic-panel">
        <div className="forensic-panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--accent)' }}>⚖️</span>
            <span style={{ fontWeight: 700, fontSize: '0.88rem', letterSpacing: '0.02em', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              Investigation Conclusion
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Separating observations, inferences, and unverified possibilities
          </span>
        </div>

        <div className="forensic-panel-body">
          {/* Executive Summary */}
          <div
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              padding: '12px 14px',
              marginBottom: '16px',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '2px' }}>
              EXECUTIVE SYNTHESIS
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {conclusion.summary}
            </p>
          </div>

          {/* 3 Distinct Conclusion Columns */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {/* 1. Confirmed Observations */}
            <div
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #a7f3d0',
                borderRadius: '8px',
                padding: '14px 16px',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }} />
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#065f46', textTransform: 'uppercase' }}>
                  Confirmed Observations ({conclusion.confirmed_observations.length})
                </span>
              </div>
              <ul style={{ paddingLeft: '16px', fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {conclusion.confirmed_observations.map((obs, idx) => (
                  <li key={idx} style={{ marginBottom: '4px' }}>
                    {obs}
                  </li>
                ))}
              </ul>
            </div>

            {/* 2. System-Generated Inferences */}
            <div
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #fde68a',
                borderRadius: '8px',
                padding: '14px 16px',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#f59e0b' }} />
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#92400e', textTransform: 'uppercase' }}>
                  System-Generated Inferences ({conclusion.system_inferences.length})
                </span>
              </div>
              <ul style={{ paddingLeft: '16px', fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {conclusion.system_inferences.map((inf, idx) => (
                  <li key={idx} style={{ marginBottom: '4px' }}>
                    {inf}
                  </li>
                ))}
              </ul>
            </div>

            {/* 3. Unverified Possibilities */}
            <div
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '14px 16px',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#64748b' }} />
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase' }}>
                  Unverified Possibilities ({conclusion.unverified_possibilities.length})
                </span>
              </div>
              <ul style={{ paddingLeft: '16px', fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {conclusion.unverified_possibilities.map((unv, idx) => (
                  <li key={idx} style={{ marginBottom: '4px' }}>
                    {unv}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

