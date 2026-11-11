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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      {/* Top Application Header */}
      <header
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border)',
          padding: '12px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <span style={{ fontWeight: 800, fontSize: '1.25rem', letterSpacing: '0.05em', color: 'var(--accent)' }}>
            SCAMTRACE AI
          </span>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Explainable Multimodal Digital Forensics
          </span>

          {activeCaseId && (
            <span
              style={{
                marginLeft: '12px',
                fontSize: '0.75rem',
                backgroundColor: 'rgba(56, 189, 248, 0.15)',
                color: 'var(--accent)',
                padding: '3px 8px',
                borderRadius: '4px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              Case: {activeCaseId}
            </span>
          )}
        </div>

        <nav style={{ display: 'flex', gap: '6px' }}>
          {(['dashboard', 'evidence', 'graph', 'timeline', 'report'] as Tab[]).map((tab) => {
            const labels: Record<Tab, string> = {
              dashboard: 'Dashboard',
              evidence: 'Evidence Lab',
              graph: 'Relationships',
              timeline: 'Timeline',
              report: 'Report & Audit',
            };
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  backgroundColor: isActive ? 'var(--accent)' : 'transparent',
                  color: isActive ? '#0f172a' : 'var(--text-primary)',
                  border: 'none',
                  padding: '7px 14px',
                  borderRadius: '5px',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.88rem',
                  cursor: 'pointer',
                  transition: 'background 0.15s ease',
                }}
              >
                {labels[tab]}
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
