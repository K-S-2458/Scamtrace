import React, { useState } from 'react';
import { Dashboard } from './pages/Dashboard';
import { EvidenceLab } from './pages/EvidenceLab';
import { RelationshipExplorer } from './pages/RelationshipExplorer';
import { IncidentTimeline } from './pages/IncidentTimeline';
import { ReportPage } from './pages/ReportPage';

type Tab = 'dashboard' | 'evidence' | 'graph' | 'timeline' | 'report';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);

  const tabs: Array<{ id: Tab; label: string; icon: string }> = [
    { id: 'dashboard', label: 'Dashboard & Triage', icon: '📊' },
    { id: 'evidence', label: 'Evidence Lab', icon: '🔬' },
    { id: 'graph', label: 'Relationship Explorer', icon: '🕸️' },
    { id: 'timeline', label: 'Incident Timeline', icon: '⏱️' },
    { id: 'report', label: 'Forensic Report & Audit', icon: '📑' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      {/* Top Application Header */}
      <header
        style={{
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--border)',
          padding: '12px 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          zIndex: 50,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 900,
                color: '#04101e',
                fontSize: '1.1rem',
                boxShadow: '0 0 16px rgba(56, 189, 248, 0.5)',
              }}
            >
              ⚡
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.15rem', letterSpacing: '0.04em', color: '#f8fafc' }}>
                SCAMTRACE <span style={{ color: 'var(--accent)' }}>AI</span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', letterSpacing: '0.02em' }}>
                Explainable Multimodal Forensics & Correlation
              </div>
            </div>
          </div>

          {activeCaseId ? (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: 'rgba(30, 41, 59, 0.9)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                padding: '4px 12px',
                borderRadius: '9999px',
                marginLeft: '12px',
              }}
            >
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent)', boxShadow: '0 0 8px var(--accent)' }}></span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Active Case:</span>
              <span style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent)' }}>
                {activeCaseId}
              </span>
            </div>
          ) : (
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginLeft: '12px' }}>
              No case selected
            </span>
          )}
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '8px' }}>
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  backgroundColor: isActive ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                  color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                  border: isActive ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid transparent',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: isActive ? '0 0 12px rgba(56, 189, 248, 0.2)' : 'none',
                }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </header>

      {/* Main Screen Content */}
      <main style={{ flex: 1, overflowY: 'auto' }}>
        {activeTab === 'dashboard' && (
          <Dashboard
            activeCaseId={activeCaseId}
            onSelectCase={(cid) => setActiveCaseId(cid)}
            onNavigateTab={(tab) => setActiveTab(tab)}
          />
        )}
        {activeTab === 'evidence' && <EvidenceLab activeCaseId={activeCaseId} />}
        {activeTab === 'graph' && <RelationshipExplorer activeCaseId={activeCaseId} />}
        {activeTab === 'timeline' && <IncidentTimeline activeCaseId={activeCaseId} />}
        {activeTab === 'report' && <ReportPage activeCaseId={activeCaseId} />}
      </main>
    </div>
  );
};

export default App;
