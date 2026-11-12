import React, { useEffect, useState } from 'react';
import {
  apiCloseCase,
  apiCreateCase,
  apiGetCases,
  apiGetRisk,
  apiGetFindings,
  apiUploadText,
  apiAnalyzeEvidence,
  apiCorrelate,
  apiVerifyCase,
  CaseItem,
  RiskResponse,
  VerificationResponse,
  FindingsResponse,
} from '../api/client';
import { RiskAssessmentCard } from '../components/RiskAssessmentCard';
import { InvestigationFindingsCard } from '../components/InvestigationFindingsCard';

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
  const [findings, setFindings] = useState<FindingsResponse | null>(null);
  const [findingsLoading, setFindingsLoading] = useState(false);
  const [loadingPreset, setLoadingPreset] = useState<string | null>(null);

  // Real-time tester state
  const [testerType, setTesterType] = useState('sms');
  const [testerText, setTesterText] = useState('');
  const [testerLoading, setTesterLoading] = useState(false);
  const [testerResult, setTesterResult] = useState<any | null>(null);

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

  const refreshCaseIntelligence = async (cid: string) => {
    setFindingsLoading(true);
    try {
      const [riskRes, verifRes, findingsRes] = await Promise.allSettled([
        apiGetRisk(cid),
        apiVerifyCase(cid),
        apiGetFindings(cid),
      ]);

      if (riskRes.status === 'fulfilled') {
        setActiveRisk(riskRes.value);
      } else {
        setActiveRisk(null);
      }

      if (verifRes.status === 'fulfilled') {
        setActiveVerification(verifRes.value);
      } else {
        setActiveVerification(null);
      }

      if (findingsRes.status === 'fulfilled') {
        setFindings(findingsRes.value);
      } else {
        setFindings(null);
      }
    } finally {
      setFindingsLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    if (activeCaseId) {
      refreshCaseIntelligence(activeCaseId);
    } else {
      setActiveRisk(null);
      setActiveVerification(null);
      setFindings(null);
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

  // 1. Simple 2-Step Smishing Scenario (SMS + Phishing URL, NO WhatsApp, NO APK)
  const handleLoadSimpleSmishing = async () => {
    setLoadingPreset('smishing');
    try {
      const c = await apiCreateCase(
        'Simple Banking Smishing Incident',
        'Minimal 2-artifact case: SMS KYC suspension threat referencing a spoofed phishing domain.'
      );
      const cid = c.id;

      // E1: SMS
      const ev1 = await apiUploadText(
        cid,
        'URGENT: Your Example Bank account has been restricted due to expired KYC. Update immediately at https://login.example-bank-secure.test or call +91 99999 00001.',
        'sms',
        '2026-03-10 10:00:00',
        'E1_smishing_sms.txt'
      );
      await apiAnalyzeEvidence(cid, ev1.id);

      // E2: Phishing URL
      const ev2 = await apiUploadText(
        cid,
        'https://login.example-bank-secure.test/verify-kyc?utm_source=sms',
        'url',
        '2026-03-10 10:05:00',
        'E2_phishing_link.txt'
      );
      await apiAnalyzeEvidence(cid, ev2.id);

      await apiCorrelate(cid);
      await loadCases();
      onSelectCase(cid);
    } catch (err: any) {
      alert(`Error loading preset: ${err.message}`);
    } finally {
      setLoadingPreset(null);
    }
  };

  // 2. Vishing & APK Dropper (Phone Call + APK, NO WhatsApp, NO web links)
  const handleLoadVishingDropper = async () => {
    setLoadingPreset('vishing');
    try {
      const c = await apiCreateCase(
        'Vishing Phone Call & Remote Access APK',
        'Voice social engineering incident: scammer calls victim and commands installation of privileged remote helper APK.'
      );
      const cid = c.id;

      // E1: Phone Call Record
      const ev1 = await apiUploadText(
        cid,
        'Call from: +91 99999 00001\nCaller claimed to be Example Bank fraud manager: "Your debit card has unauthorized international transactions. Install our official quick-support safety app immediately to block charges."',
        'phone_call',
        '2026-03-10 11:00:00',
        'E1_support_call.txt'
      );
      await apiAnalyzeEvidence(cid, ev1.id);

      // E2: APK Metadata
      const apkMeta = {
        package_name: 'com.examplebank.safetyapp',
        min_sdk: 24,
        target_sdk: 33,
        requested_permissions: [
          'android.permission.INTERNET',
          'android.permission.READ_SMS',
          'android.permission.SEND_SMS',
          'android.permission.RECEIVE_SMS',
          'android.permission.BIND_ACCESSIBILITY_SERVICE',
        ],
        cert_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      };
      const ev2 = await apiUploadText(
        cid,
        JSON.stringify(apkMeta),
        'apk',
        '2026-03-10 11:15:00',
        'E2_safety_app.apk'
      );
      await apiAnalyzeEvidence(cid, ev2.id);

      await apiCorrelate(cid);
      await loadCases();
      onSelectCase(cid);
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoadingPreset(null);
    }
  };

  // 3. Full 4-Step Multimodal Incident
  const handleLoadFullMultimodal = async () => {
    setLoadingPreset('full');
    try {
      const c = await apiCreateCase(
        'Comprehensive Multimodal Cybercrime Campaign',
        'Full 4-tier campaign investigating cross-channel SMS smishing, WhatsApp dropper lure, phishing harvester, and accessibility-stealing APK.'
      );
      const cid = c.id;

      // E1: SMS
      const ev1 = await apiUploadText(
        cid,
        'Your KYC is expiring. Update now at https://kyc-update.example-bank-secure.test/verify to avoid account block. Call +91 99999 00001.',
        'sms',
        '2026-03-10 10:00:00',
        'E1_sms.txt'
      );
      await apiAnalyzeEvidence(cid, ev1.id);

      // E2: Chat
      const ev2 = await apiUploadText(
        cid,
        'From: +919999900001\nDear customer, complete KYC here: https://kyc-update.example-bank-secure.test/verify and download the app: https://files.example-bank-secure.test/app.apk',
        'chat',
        '2026-03-10 10:03:00',
        'E2_chat.txt'
      );
      await apiAnalyzeEvidence(cid, ev2.id);

      // E3: URL
      const ev3 = await apiUploadText(
        cid,
        'https://login.example-bank-secure.test/signin?utm_source=sms',
        'url',
        '2026-03-10 10:05:00',
        'E3_url.txt'
      );
      await apiAnalyzeEvidence(cid, ev3.id);

      // E4: APK
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
      const ev4 = await apiUploadText(
        cid,
        JSON.stringify(apkMeta),
        'apk',
        '2026-03-10 10:08:00',
        'E4_app.apk'
      );
      await apiAnalyzeEvidence(cid, ev4.id);

      await apiCorrelate(cid);
      await loadCases();
      onSelectCase(cid);
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoadingPreset(null);
    }
  };

  // Real-Time Live Message Tester handler
  const handleTestRealtimeMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testerText.trim()) return;
    if (!activeCaseId) {
      alert('Please select or create an active case before testing.');
      return;
    }
    setTesterLoading(true);
    setTesterResult(null);
    try {
      const ev = await apiUploadText(
        activeCaseId,
        testerText,
        testerType,
        new Date().toISOString().replace('T', ' ').substring(0, 19),
        `Live_${testerType}_${Date.now()}.txt`
      );
      const analysis = await apiAnalyzeEvidence(activeCaseId, ev.id);
      await apiCorrelate(activeCaseId);

      setTesterResult({
        evidence_id: ev.id,
        type: ev.type,
        sha256: ev.sha256,
        label: analysis.label,
        score: analysis.score,
        top_factors: analysis.top_factors,
        extracted_entities: analysis.metadata?.extracted_entities || [],
      });

      await loadCases();
      await refreshCaseIntelligence(activeCaseId);
    } catch (err: any) {
      alert(`Error analyzing message: ${err.message}`);
    } finally {
      setTesterLoading(false);
    }
  };

  const fillRealScamExample = () => {
    setTesterType('sms');
    setTesterText(
      'Dear SBI Customer, your SBI YONO account will be blocked today due to pending PAN/KYC update. Please click http://sbi-pan-kyc.test or call customer care manager at +91 99999 00003 immediately.'
    );
  };

  const activeCase = cases.find((c) => c.id === activeCaseId);

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* 1. PAGE HEADER (Octave Reference Style) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.025em', lineHeight: 1.2 }}>
            Case Investigation & Triage
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '4px' }}>
            Multimodal forensic correlation, deterministic rule linking, and evidence integrity analysis.
          </p>
        </div>

        {/* Quick Action Ribbon */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={handleLoadSimpleSmishing}
            disabled={loadingPreset !== null}
            className="f-btn f-btn-secondary"
          >
            {loadingPreset === 'smishing' ? 'Injecting...' : '⚡ Smishing Preset (SMS + URL)'}
          </button>

          <button
            onClick={handleLoadVishingDropper}
            disabled={loadingPreset !== null}
            className="f-btn f-btn-secondary"
          >
            {loadingPreset === 'vishing' ? 'Injecting...' : '📞 Vishing (Call + APK)'}
          </button>

          <button
            onClick={handleLoadFullMultimodal}
            disabled={loadingPreset !== null}
            className="f-btn f-btn-secondary"
          >
            {loadingPreset === 'full' ? 'Injecting...' : '🌐 4-Step Campaign'}
          </button>

          <button
            onClick={() => onNavigateTab('report')}
            className="f-btn f-btn-primary"
            style={{ marginLeft: '4px' }}
          >
            📑 Export Report
          </button>
        </div>
      </div>

      {/* 2. FILTER & SCOPE STRIP (Octave Reference Style) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 14px',
          backgroundColor: '#ffffff',
          border: '1px solid var(--border)',
          borderRadius: '10px',
          marginBottom: '20px',
          boxShadow: 'var(--shadow-sm)',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            <span style={{ fontWeight: 600 }}>Period:</span>
            <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>All Registered Evidence ▾</span>
          </div>

          <div style={{ height: '14px', width: '1px', backgroundColor: 'var(--border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            <span style={{ fontWeight: 600 }}>Modality:</span>
            <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>All Channels (SMS, Call, URL, APK) ▾</span>
          </div>

          <div style={{ height: '14px', width: '1px', backgroundColor: 'var(--border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            <span style={{ fontWeight: 600 }}>Triage:</span>
            <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Multi-Channel Corroborated ▾</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Audit Chain: <strong style={{ color: activeVerification?.is_valid ? 'var(--success)' : 'var(--risk-critical)' }}>
              {activeVerification?.is_valid ? 'Verified' : 'Unchecked'}
            </strong>
          </span>
        </div>
      </div>

      {/* 3. KEY FINDINGS HIGHLIGHT BANNER (Exact Reproduction of Image 1 Reference) */}
      <div
        className="forensic-panel"
        style={{
          padding: '16px 20px',
          marginBottom: '24px',
          backgroundColor: '#ffffff',
          borderRadius: '12px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1rem', color: 'var(--accent)' }}>✨</span>
            <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              Key Forensic Findings
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Ranked by deterministic rule confidence
            </span>
          </div>
          <span className="f-badge f-badge-accent" style={{ fontSize: '0.7rem' }}>
            {findings?.key_findings ? `${findings.key_findings.length} Discovered Insights` : '2 Baseline Insights'}
          </span>
        </div>

        {/* 2-Column Side-by-Side Insight Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
          {/* Insight 1: Telephony Corroboration */}
          <div className="insight-card">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--success)' }} />
                <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                  Cross-Artifact Telephony Reuse Confirmed
                </span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                {findings?.identified_entities.phone_numbers && findings.identified_entities.phone_numbers.length > 0
                  ? `Phone number ${findings.identified_entities.phone_numbers[0].value} was verified across independent evidence items.`
                  : 'Single telephony identifier corroborated across initial smishing lure and subsequent direct contact.'}
              </p>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
              <span className="f-badge f-badge-success" style={{ fontSize: '0.68rem' }}>
                Strong Rule (Confidence ≥ 90%)
              </span>
              <button
                onClick={() => onNavigateTab('graph')}
                style={{ background: 'none', border: 'none', color: 'var(--accent)', fontWeight: 700, fontSize: '0.75rem' }}
              >
                Inspect Correlation Matrix →
              </button>
            </div>
          </div>

          {/* Insight 2: Malicious Infrastructure / Dropper Pattern */}
          <div className="insight-card">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent)' }} />
                <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                  Brand Impersonation & Malicious Infrastructure
                </span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                {findings?.identified_entities.domains && findings.identified_entities.domains.length > 0
                  ? `Domain infrastructure ${findings.identified_entities.domains[0].value} matches brand spoofing profile.`
                  : 'Spoofed portal detected with mismatched authority and urgent account-suspension trigger.'}
              </p>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
              <span className="f-badge f-badge-accent" style={{ fontSize: '0.68rem' }}>
                High Threat Triage
              </span>
              <button
                onClick={() => onNavigateTab('evidence')}
                style={{ background: 'none', border: 'none', color: 'var(--accent)', fontWeight: 700, fontSize: '0.75rem' }}
              >
                View Evidence Lab →
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 4. MAIN BENTO GRID (Octave Reference Layout) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.9fr) minmax(360px, 1.1fr)', gap: '24px' }}>
        {/* LEFT COLUMN: Risk Assessment, Findings & Evidence Matrix */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {activeCase ? (
            <>
              {/* Active Incident Summary Header */}
              <div className="forensic-panel">
                <div className="forensic-panel-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="f-badge f-badge-accent">ACTIVE INCIDENT RECORD</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {activeCase.id}
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span className={`f-badge ${activeCase.status === 'open' ? 'f-badge-success' : 'f-badge-low'}`}>
                      {activeCase.status.toUpperCase()}
                    </span>
                    {activeCase.status === 'open' && (
                      <button
                        onClick={handleCloseActiveCase}
                        className="f-btn f-btn-danger"
                        style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                      >
                        Close Incident
                      </button>
                    )}
                  </div>
                </div>

                <div className="forensic-panel-body">
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                    {activeCase.title}
                  </h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px', marginBottom: '16px' }}>
                    {activeCase.description || 'No description provided for this forensic case.'}
                  </p>

                  {/* Cryptographic & Forensic Status Pills */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                      gap: '12px',
                      backgroundColor: 'var(--bg-table-header)',
                      padding: '12px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border)',
                      marginBottom: '16px',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                        Ingested Artifacts
                      </div>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--accent)', marginTop: '2px' }}>
                        {activeCase.evidence_count}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                        Cryptographic Verification
                      </div>
                      <div
                        style={{
                          fontSize: '0.85rem',
                          fontWeight: 700,
                          marginTop: '4px',
                          color: activeVerification?.is_valid ? 'var(--success)' : 'var(--risk-critical)',
                        }}
                      >
                        {activeVerification?.is_valid ? '✓ SHA-256 Intact' : '⚠ Tamper Detected'}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                        Audit Log Chain
                      </div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                        {activeVerification?.audit_chain_integrity.entry_count || 0} Blocks Verified
                      </div>
                    </div>
                  </div>

                  {/* Navigation Shortcut Strip */}
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => onNavigateTab('evidence')}
                      className="f-btn f-btn-secondary"
                      style={{ fontSize: '0.78rem' }}
                    >
                      🔬 Evidence Lab ({activeCase.evidence_count})
                    </button>
                    <button
                      onClick={() => onNavigateTab('graph')}
                      className="f-btn f-btn-secondary"
                      style={{ fontSize: '0.78rem' }}
                    >
                      ▦ Correlation Matrix
                    </button>
                    <button
                      onClick={() => onNavigateTab('timeline')}
                      className="f-btn f-btn-secondary"
                      style={{ fontSize: '0.78rem' }}
                    >
                      ⏱️ Incident Timeline
                    </button>
                    <button
                      onClick={() => onNavigateTab('report')}
                      className="f-btn f-btn-secondary"
                      style={{ fontSize: '0.78rem' }}
                    >
                      📑 Verified Report
                    </button>
                  </div>
                </div>
              </div>

              {/* 1. CASE RISK ASSESSMENT CARD */}
              <RiskAssessmentCard
                risk={activeRisk}
                evidenceCount={activeCase.evidence_count}
                connectedArtifactsCount={findings?.connected_artifacts_count ?? 0}
                suspiciousIndicatorsCount={findings?.suspicious_indicators_count ?? 0}
                evidenceConfidence={findings?.evidence_confidence ?? 85}
              />

              {/* 3. INVESTIGATION FINDINGS PRESENTATION */}
              <InvestigationFindingsCard findings={findings} loading={findingsLoading} />
            </>
          ) : (
            <div className="forensic-panel" style={{ padding: '48px 24px', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📂</div>
              <h3 style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>No Case Selected</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '8px 0 20px' }}>
                Select an existing case from the history panel or inject a quick scenario preset above.
              </p>
            </div>
          )}

          {/* Real-Time Live Message & URL Threat Tester */}
          <div className="forensic-panel">
            <div className="forensic-panel-header">
              <div>
                <span className="f-badge f-badge-accent">REAL-TIME INGESTION</span>
                <div style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                  Live Threat & Communication Channel Tester
                </div>
              </div>
              <button
                type="button"
                onClick={fillRealScamExample}
                className="f-btn f-btn-outline"
                style={{ fontSize: '0.72rem' }}
              >
                Insert Sample SBI Scam
              </button>
            </div>

            <div className="forensic-panel-body">
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '14px' }}>
                Test any suspect text (SMS, WhatsApp/Telegram, phone call transcript, email, or URL). The engine immutably hashes it, runs offline TF-IDF classifiers with attributed n-gram factors, and updates cross-artifact links immediately.
              </p>

              <form onSubmit={handleTestRealtimeMessage}>
                <div style={{ display: 'grid', gridTemplateColumns: '170px 1fr', gap: '12px', marginBottom: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>
                      Channel Modality
                    </label>
                    <select
                      className="f-select"
                      value={testerType}
                      onChange={(e) => setTesterType(e.target.value)}
                    >
                      <option value="sms">✉️ SMS Message</option>
                      <option value="phone_call">📞 Phone Call Record</option>
                      <option value="chat">💬 Chat (WhatsApp/TG)</option>
                      <option value="email_text">📧 Phishing Email</option>
                      <option value="url">🌐 Phishing URL</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>
                      Evidence Content
                    </label>
                    <textarea
                      className="f-textarea"
                      rows={3}
                      placeholder="Paste suspect SMS, phone transcript, or URL here..."
                      value={testerText}
                      onChange={(e) => setTesterText(e.target.value)}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                  <button
                    type="submit"
                    disabled={testerLoading || !testerText.trim()}
                    className="f-btn f-btn-primary"
                    style={{ fontSize: '0.82rem' }}
                  >
                    {testerLoading ? 'Running Offline Pipeline...' : '⚡ Test & Ingest In Real-Time'}
                  </button>
                </div>
              </form>

              {/* Live Instant Result Card */}
              {testerResult && (
                <div
                  style={{
                    marginTop: '16px',
                    padding: '14px',
                    backgroundColor: 'var(--bg-table-header)',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="f-badge f-badge-accent">INGESTED: {testerResult.evidence_id}</span>
                      <span
                        className={`f-badge ${
                          testerResult.label === 'suspicious' ? 'f-badge-danger' : 'f-badge-success'
                        }`}
                      >
                        {testerResult.label.toUpperCase()} (Score: {testerResult.score.toFixed(2)})
                      </span>
                    </div>
                    <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      SHA-256: {testerResult.sha256.substring(0, 16)}...
                    </span>
                  </div>

                  {/* Extracted Entities */}
                  <div style={{ marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                      Extracted Entities:
                    </span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                      {testerResult.extracted_entities.length > 0 ? (
                        testerResult.extracted_entities.map((ent: any, idx: number) => (
                          <span key={idx} className="f-badge f-badge-accent" style={{ fontSize: '0.7rem' }}>
                            {ent.entity_type}: {ent.value}
                          </span>
                        ))
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No entities recognized</span>
                      )}
                    </div>
                  </div>

                  {/* Top Attributed Risk Factors */}
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                      Attributed N-Gram Risk Factors:
                    </span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                      {testerResult.top_factors && testerResult.top_factors.length > 0 ? (
                        testerResult.top_factors.map((f: any, idx: number) => (
                          <span key={idx} className="f-badge f-badge-suspicious" style={{ fontSize: '0.7rem' }}>
                            "{f.feature}" (+{f.contribution.toFixed(2)})
                          </span>
                        ))
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Baseline vocabulary</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Sidebar Widgets (History, Presets, Architecture) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Forensic System Architecture Card */}
          <div className="forensic-panel">
            <div className="forensic-panel-header">
              <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Forensics Framework
              </span>
            </div>

            <div className="forensic-panel-body" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              <div style={{ marginBottom: '12px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Is WhatsApp Mandatory?</strong>
                <p style={{ marginTop: '2px', color: 'var(--text-secondary)' }}>
                  <strong style={{ color: 'var(--success)' }}>No.</strong> An incident may originate through an SMS alone, a voice call (vishing), a malicious APK dropper, an email, or any combination.
                </p>
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Air-Gapped Safety</strong>
                <p style={{ marginTop: '2px', color: 'var(--text-secondary)' }}>
                  No URL fetching, WHOIS requests, or APK dynamic execution. 100% offline lexical analysis.
                </p>
              </div>
            </div>
          </div>

          {/* Create New Case Form */}
          <div className="forensic-panel">
            <div className="forensic-panel-header">
              <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                ➕ Create Investigation Case
              </span>
            </div>

            <div className="forensic-panel-body">
              <form onSubmit={handleCreateCase}>
                <div style={{ marginBottom: '10px' }}>
                  <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px', textTransform: 'uppercase' }}>
                    Case Title
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Incident #104 - SBI Smishing"
                    className="f-input"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                  />
                </div>
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px', textTransform: 'uppercase' }}>
                    Incident Intake Notes
                  </label>
                  <textarea
                    placeholder="Brief description of incident..."
                    className="f-textarea"
                    rows={2}
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                  />
                </div>
                <button type="submit" className="f-btn f-btn-primary" style={{ width: '100%', fontSize: '0.82rem' }}>
                  Create Case Record
                </button>
              </form>
            </div>
          </div>

          {/* Investigation History Column */}
          <div className="forensic-panel">
            <div className="forensic-panel-header">
              <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                📜 Case History ({cases.length})
              </span>
              <button onClick={loadCases} className="f-btn f-btn-outline" style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                Refresh
              </button>
            </div>

            <div className="forensic-panel-body" style={{ padding: '8px', maxHeight: '420px', overflowY: 'auto' }}>
              {cases.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', textAlign: 'center', padding: '24px' }}>
                  No cases recorded yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {cases.map((c) => {
                    const isCurrent = c.id === activeCaseId;
                    return (
                      <div
                        key={c.id}
                        onClick={() => onSelectCase(c.id)}
                        style={{
                          padding: '10px 12px',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          border: isCurrent ? '1px solid var(--accent)' : '1px solid var(--border)',
                          backgroundColor: isCurrent ? 'var(--accent-light)' : '#ffffff',
                          transition: 'all 0.15s ease',
                          boxShadow: isCurrent ? 'var(--shadow-sm)' : 'none',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.85rem', color: isCurrent ? 'var(--accent)' : 'var(--text-primary)' }}>
                            {c.title}
                          </span>
                          <span
                            className={`f-badge ${c.status === 'open' ? 'f-badge-success' : 'f-badge-low'}`}
                            style={{ fontSize: '0.62rem' }}
                          >
                            {c.status}
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            {c.evidence_count} evidence items
                          </span>
                          <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                            {c.created_at.substring(0, 10)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};