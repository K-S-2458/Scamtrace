import React, { useEffect, useState } from 'react';
import {
  apiCloseCase,
  apiCreateCase,
  apiGetCases,
  apiGetRisk,
  apiUploadText,
  apiVerifyCase,
  CaseItem,
  RiskResponse,
  VerificationResponse,
} from '../api/client';

interface DashboardProps {
  activeCaseId: string | null;
  onSelectCase: (caseId: string) => void;
  onNavigateTab: (tab: 'evidence' | 'graph' | 'timeline' | 'report') => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  activeCaseId,
  onSelectCase,
  onNavigateTab,
}) => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [activeRisk, setActiveRisk] = useState<RiskResponse | null>(null);
  const [activeVerification, setActiveVerification] = useState<VerificationResponse | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);

  const loadCases = async () => {
    try {
      const data = await apiGetCases();
      setCases(data);
      if (!activeCaseId && data.length > 0) {
        onSelectCase(data[0].id);
      }
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    if (activeCaseId) {
      apiGetRisk(activeCaseId)
        .then(setActiveRisk)
        .catch(() => setActiveRisk(null));
      apiVerifyCase(activeCaseId)
        .then(setActiveVerification)
        .catch(() => setActiveVerification(null));
    }
  }, [activeCaseId]);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      const created = await apiCreateCase(newTitle, newDesc);
      setNewTitle('');
      setNewDesc('');
      await loadCases();
      onSelectCase(created.id);
    } catch (err: any) {
      alert(`Error creating case: ${err.message}`);
    }
  };

  const handleCloseActiveCase = async () => {
    if (!activeCaseId) return;
    try {
      await apiCloseCase(activeCaseId);
      await loadCases();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleLoadDemoScenario = async () => {
    setDemoLoading(true);
    try {
      // 1. Create Demo Case
      const demoCase = await apiCreateCase(
        'Synthetic KYC Scam Incident',
        'Multimodal digital forensic case investigating bank KYC block lures, phishing URL, and privileged APK droppers.'
      );
      const cid = demoCase.id;

      // 2. Ingest 5 Evidence Items
      // E1: SMS
      await apiUploadText(
        cid,
        'Your KYC is expiring. Update now at https://kyc-update.example-bank-secure.test/verify to avoid account block. Call +91 99999 00001.',
        'sms',
        '2026-03-10 10:00:00',
        'E1_sms.txt'
      );

      // E2: Chat
      await apiUploadText(
        cid,
        'From: +919999900001\nDear customer, complete KYC here: https://kyc-update.example-bank-secure.test/verify and download the app: https://files.example-bank-secure.test/app.apk',
        'chat',
        '2026-03-10 10:03:00',
        'E2_chat.txt'
      );

      // E3: URL
      await apiUploadText(
        cid,
        'https://login.example-bank-secure.test/signin?utm_source=sms',
        'url',
        '2026-03-10 10:05:00',
        'E3_url.txt'
      );

      // E4: APK metadata
      const apkMeta = {
        package_name: 'com.fake.kycupdate',
        min_sdk: 21,
        target_sdk: 33,
        requested_permissions: [
          'android.permission.INTERNET',
          'android.permission.READ_SMS',
          'android.permission.RECEIVE_SMS',
          'android.permission.BIND_ACCESSIBILITY_SERVICE',
        ],
        cert_sha256: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01',
      };
      await apiUploadText(
        cid,
        JSON.stringify(apkMeta),
        'apk',
        '2026-03-10 10:08:00',
        'E4_app.apk'
      );

      // E5: SMS (Debit alert)
      await apiUploadText(
        cid,
        'Rs 25,000 debited from your account ending 1234 via UPI. If not you, call +91 99999 00002.',
        'sms',
        '2026-03-10 10:15:00',
        'E5_sms.txt'
      );

      await loadCases();
      onSelectCase(cid);
      alert('Section 10 Demo Scenario loaded successfully with 5 multimodal artifacts!');
    } catch (err: any) {
      alert(`Error loading demo: ${err.message}`);
    } finally {
      setDemoLoading(false);
    }
  };

  const activeCase = cases.find((c) => c.id === activeCaseId);

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Investigation Workbench</h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Digital forensics case management, cryptographic verification, and triage assessment.
          </p>
        </div>
        <button
          onClick={handleLoadDemoScenario}
          disabled={demoLoading}
          style={{
            backgroundColor: 'var(--accent)',
            color: '#0f172a',
            border: 'none',
            padding: '10px 18px',
            borderRadius: '6px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          {demoLoading ? 'Ingesting Scenario...' : '⚡ Load Section 10 Demo Incident'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
        {/* Left Column: Active Case Overview & Cases List */}
        <div>
          {/* Active Case Card */}
          {activeCase && (
            <div
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '20px',
                marginBottom: '24px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--accent)', fontWeight: 600 }}>
                    ACTIVE INVESTIGATION
                  </span>
                  <h2 style={{ fontSize: '1.3rem', margin: '4px 0' }}>{activeCase.title}</h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    {activeCase.description || 'No description provided.'}
                  </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      backgroundColor: activeCase.status === 'open' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                      color: activeCase.status === 'open' ? 'var(--accent)' : 'var(--text-secondary)',
                    }}
                  >
                    {activeCase.status.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Status Metrics Bar */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: '12px',
                  marginTop: '16px',
                  paddingTop: '16px',
                  borderTop: '1px solid var(--border)',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Evidence Items</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>{activeCase.evidence_count}</div>
                </div>

                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Risk Assessment</div>
                  <div
                    style={{
                      fontSize: '1.1rem',
                      fontWeight: 700,
                      color:
                        activeRisk?.risk_band === 'high'
                          ? 'var(--danger)'
                          : activeRisk?.risk_band === 'medium'
                          ? 'var(--warning)'
                          : 'var(--success)',
                    }}
                  >
                    {activeRisk ? `${activeRisk.risk_band.toUpperCase()} (${(activeRisk.final_score).toFixed(2)})` : 'Calculating...'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Cryptographic Integrity</div>
                  <div
                    style={{
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      color: activeVerification?.is_valid ? 'var(--success)' : 'var(--danger)',
                    }}
                  >
                    {activeVerification?.is_valid ? '✓ Verified (Unbroken)' : '⚠ Tamper Detected'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Audit Chain</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {activeVerification?.audit_chain_integrity.entry_count || 0} Blocks
                  </div>
                </div>
              </div>

              {/* Quick Navigation Actions */}
              <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
                <button
                  onClick={() => onNavigateTab('evidence')}
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                    border: 'none',
                    padding: '8px 14px',
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                  }}
                >
                  Manage Evidence & Analyzers →
                </button>
                <button
                  onClick={() => onNavigateTab('graph')}
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                    border: 'none',
                    padding: '8px 14px',
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                  }}
                >
                  Explore Knowledge Graph →
                </button>
                <button
                  onClick={() => onNavigateTab('report')}
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                    border: 'none',
                    padding: '8px 14px',
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                  }}
                >
                  View Audited Report →
                </button>
                {activeCase.status === 'open' && (
                  <button
                    onClick={handleCloseActiveCase}
                    style={{
                      marginLeft: 'auto',
                      backgroundColor: 'transparent',
                      color: 'var(--danger)',
                      border: '1px solid var(--danger)',
                      padding: '8px 14px',
                      borderRadius: '4px',
                      fontSize: '0.85rem',
                    }}
                  >
                    Close Case
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Cases Table */}
          <div
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '20px',
            }}
          >
            <h2 style={{ fontSize: '1.15rem', marginBottom: '16px' }}>All Investigation Cases ({cases.length})</h2>
            {cases.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No cases found. Create a new case or load the demo scenario.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '8px' }}>Case ID</th>
                    <th style={{ padding: '8px' }}>Title</th>
                    <th style={{ padding: '8px' }}>Evidence</th>
                    <th style={{ padding: '8px' }}>Status</th>
                    <th style={{ padding: '8px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c) => (
                    <tr
                      key={c.id}
                      style={{
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        backgroundColor: c.id === activeCaseId ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>{c.id}</td>
                      <td style={{ padding: '10px 8px', fontWeight: 600 }}>{c.title}</td>
                      <td style={{ padding: '10px 8px' }}>{c.evidence_count} items</td>
                      <td style={{ padding: '10px 8px' }}>
                        <span
                          style={{
                            fontSize: '0.75rem',
                            padding: '2px 6px',
                            borderRadius: '3px',
                            backgroundColor: c.status === 'open' ? 'rgba(56,189,248,0.15)' : 'rgba(148,163,184,0.15)',
                            color: c.status === 'open' ? 'var(--accent)' : 'var(--text-secondary)',
                          }}
                        >
                          {c.status.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '10px 8px' }}>
                        <button
                          onClick={() => onSelectCase(c.id)}
                          style={{
                            backgroundColor: c.id === activeCaseId ? 'var(--accent)' : 'var(--bg-tertiary)',
                            color: c.id === activeCaseId ? '#0f172a' : 'var(--text-primary)',
                            border: 'none',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                          }}
                        >
                          {c.id === activeCaseId ? 'Active' : 'Select'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right Column: Create Case Form */}
        <div>
          <div
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '20px',
            }}
          >
            <h2 style={{ fontSize: '1.15rem', marginBottom: '12px' }}>Open New Case</h2>
            <form onSubmit={handleCreateCase}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Case Title *
                </label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Bank Impersonation Campaign"
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    border: '1px solid var(--border)',
                    backgroundColor: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Incident Description
                </label>
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  rows={4}
                  placeholder="Summary of received complaints or reports..."
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    border: '1px solid var(--border)',
                    backgroundColor: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    resize: 'vertical',
                  }}
                />
              </div>

              <button
                type="submit"
                style={{
                  width: '100%',
                  backgroundColor: 'var(--accent)',
                  color: '#0f172a',
                  border: 'none',
                  padding: '10px',
                  borderRadius: '4px',
                  fontWeight: 600,
                }}
              >
                Create Investigation Case
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
