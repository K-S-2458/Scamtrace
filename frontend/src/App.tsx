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
  const [searchQuery, setSearchQuery] = useState('');

  const navItems: Array<{ id: Tab; label: string; icon: string; category: string; badge?: string }> = [
    { id: 'dashboard', label: 'Executive Dashboard', icon: '📊', category: 'INVESTIGATION' },
    { id: 'evidence', label: 'Evidence Lab', icon: '🔬', category: 'INVESTIGATION' },
    { id: 'graph', label: 'Correlation Matrix', icon: '▦', category: 'INVESTIGATION' },
    { id: 'timeline', label: 'Incident Timeline', icon: '⏱️', category: 'INVESTIGATION' },
    { id: 'report', label: 'Verified Report & Audit', icon: '📑', category: 'FORENSIC AUDIT' },
  ];

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: 'var(--bg-primary)' }}>
      {/* 1. LEFT SIDEBAR NAVIGATION (Octave Reference Style) */}
      <aside
        style={{
          width: '260px',
          backgroundColor: 'var(--bg-sidebar)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          flexShrink: 0,
          zIndex: 40,
        }}
      >
        {/* Top: Brand Header & Workspace Switcher */}
        <div>
          {/* Brand Logo & Name */}
          <div
            style={{
              padding: '18px 20px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'var(--accent)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.05rem',
                fontWeight: 800,
                boxShadow: '0 2px 6px rgba(82, 54, 236, 0.35)',
              }}
            >
              ⚡
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1rem', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                SCAMTRACE <span style={{ color: 'var(--accent)' }}>AI</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                Digital Forensics Platform
              </div>
            </div>
          </div>

          {/* Workspace Pill Switcher */}
          <div style={{ padding: '14px 16px 8px' }}>
            <div
              style={{
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '8px 12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                <span style={{ fontSize: '0.9rem' }}>📂</span>
                <div style={{ overflow: 'hidden' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                    Active Case
                  </div>
                  <div
                    style={{
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      color: 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      textOverflow: 'ellipsis',
                      overflow: 'hidden',
                    }}
                  >
                    {activeCaseId ? activeCaseId : 'Select a Case...'}
                  </div>
                </div>
              </div>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>▾</span>
            </div>
          </div>

          {/* Sectioned Navigation Menu */}
          <div style={{ padding: '12px 14px' }}>
            {/* Group 1: Investigation */}
            <div style={{ marginBottom: '16px' }}>
              <div
                style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  padding: '4px 10px',
                  marginBottom: '4px',
                }}
              >
                Investigation
              </div>
              {navItems
                .filter((item) => item.category === 'INVESTIGATION')
                .map((item) => {
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id)}
                      style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: 'none',
                        marginBottom: '3px',
                        backgroundColor: isActive ? 'var(--accent-light)' : 'transparent',
                        color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                        fontWeight: isActive ? 700 : 500,
                        fontSize: '0.82rem',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '1rem' }}>{item.icon}</span>
                        <span>{item.label}</span>
                      </div>
                      {isActive && (
                        <span
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--accent)',
                          }}
                        />
                      )}
                    </button>
                  );
                })}
            </div>

            {/* Group 2: Forensic Audit */}
            <div>
              <div
                style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  padding: '4px 10px',
                  marginBottom: '4px',
                }}
              >
                Forensic Audit
              </div>
              {navItems
                .filter((item) => item.category === 'FORENSIC AUDIT')
                .map((item) => {
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id)}
                      style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: 'none',
                        marginBottom: '3px',
                        backgroundColor: isActive ? 'var(--accent-light)' : 'transparent',
                        color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                        fontWeight: isActive ? 700 : 500,
                        fontSize: '0.82rem',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '1rem' }}>{item.icon}</span>
                        <span>{item.label}</span>
                      </div>
                      {isActive && (
                        <span
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--accent)',
                          }}
                        />
                      )}
                    </button>
                  );
                })}
            </div>
          </div>
        </div>

        {/* Bottom Sidebar Status & Metadata */}
        <div style={{ padding: '16px', borderTop: '1px solid var(--border-subtle)' }}>
          <div
            style={{
              backgroundColor: 'var(--bg-primary)',
              borderRadius: '8px',
              padding: '10px 12px',
              border: '1px solid var(--border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--success)' }} />
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--success-text)' }}>
                Air-Gapped & Offline
              </span>
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              SHA-256 Tamper Verification Active
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            <span>v0.1.0 (MVP)</span>
            <span>Single-User Lab</span>
          </div>
        </div>
      </aside>

      {/* 2. MAIN APPLICATION WORKSPACE */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top Navbar (Breadcrumb, Global Search, Live Status, Profile Avatar) */}
        <header
          style={{
            height: '56px',
            backgroundColor: 'var(--bg-secondary)',
            borderBottom: '1px solid var(--border)',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
            zIndex: 30,
          }}
        >
          {/* Breadcrumb Path */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            <span>Incidents</span>
            <span>/</span>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
              {activeCaseId || 'Select Case'}
            </span>
            <span>/</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
              {navItems.find((n) => n.id === activeTab)?.label}
            </span>
          </div>

          {/* Center Search Bar */}
          <div style={{ width: '360px', position: 'relative' }}>
            <input
              type="text"
              placeholder="Search artifacts, phone numbers, domains... (Ctrl+K)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="f-input"
              style={{
                height: '34px',
                paddingLeft: '32px',
                fontSize: '0.78rem',
                backgroundColor: 'var(--bg-primary)',
                borderRadius: '8px',
              }}
            />
            <span
              style={{
                position: 'absolute',
                left: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
                fontSize: '0.85rem',
                pointerEvents: 'none',
              }}
            >
              🔍
            </span>
          </div>

          {/* Right Header Status & User Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--success)' }} />
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                System Ready
              </span>
            </div>

            <div style={{ height: '20px', width: '1px', backgroundColor: 'var(--border)' }} />

            {/* Profile Avatar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--accent-light)',
                  border: '1px solid var(--accent-border)',
                  color: 'var(--accent)',
                  fontWeight: 700,
                  fontSize: '0.78rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                KS
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.1 }}>
                  Investigator
                </span>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                  Cyber Forensics Lab
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable Main Content Canvas */}
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
    </div>
  );
};

export default App;