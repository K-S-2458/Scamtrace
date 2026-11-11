import React, { useEffect, useState } from 'react';
import {
  apiCloseCase,
  apiCreateCase,
  apiGetCases,
  apiGetRisk,
  apiUploadText,
  apiAnalyzeEvidence,
  apiCorrelate,
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

      // Correlate automatically
      await apiCorrelate(cid);

      await loadCases();
      onSelectCase(cid);
      alert('✓ Simple 2-Step Smishing loaded! (1 SMS + 1 URL). Notice how the SMS directly correlates to the URL via SHARED_DOMAIN and BRAND_IMPERSONATION without WhatsApp or APK.');
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
      alert('✓ Vishing & APK incident loaded! (1 Phone Call + 1 APK). Shows voice lure triggering APK_LURE_PATTERN without WhatsApp.');
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoadingPreset(null);
    }
  };

  // 3. Full 4-Step Multimodal Incident (Section 10 Standard)
  const handleLoadFullMultimodal = async () => {
    setLoadingPreset('full');
    try {
      const c = await apiCreateCase(
        'Comprehensive Multimodal Cybercrime Campaign',
        'Full 4-tier campaign investigating cross-channel SMS smishing, WhatsApp dropper lure, phishing credential harvester, and accessibility-stealing APK.'
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
      alert('✓ Comprehensive 4-artifact campaign loaded with cross-channel correlation graph!');
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
      alert('Please create or select a case first.');
      return;
    }
    setTesterLoading(true);
    setTesterResult(null);
    try {
      // Ingest into active case
      const ev = await apiUploadText(
        activeCaseId,
        testerText,
        testerType,
        new Date().toISOString().replace('T', ' ').substring(0, 19),
        `Live_${testerType}_${Date.now()}.txt`
      );
      // Run analyzer
      const analysis = await apiAnalyzeEvidence(activeCaseId, ev.id);
      // Run correlation update
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
      // Refresh risk and integrity
      apiGetRisk(activeCaseId).then(setActiveRisk).catch(() => {});
      apiVerifyCase(activeCaseId).then(setActiveVerification).catch(() => {});
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
    <div style={{ padding: '24px 32px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Forensic Investigation Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '2px' }}>
            Single-user digital forensics workbench for multimodal scam correlation, timeline analysis, and tamper-proof audit verification.
          </p>
        </div>

        {/* Quick Scenario Injection Presets */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleLoadSimpleSmishing}
            disabled={loadingPreset !== null}
            className="btn-primary"
            style={{ fontSize: '0.85rem' }}
          >
            {loadingPreset === 'smishing' ? 'Injecting...' : '⚡ Load Simple Smishing (SMS + URL)'}
          </button>

          <button
            onClick={handleLoadVishingDropper}
            disabled={loadingPreset !== null}
            className="btn-secondary"
            style={{ fontSize: '0.85rem' }}
          >
            {loadingPreset === 'vishing' ? 'Injecting...' : '📞 Vishing (Call + APK)'}
          </button>

          <button
            onClick={handleLoadFullMultimodal}
            disabled={loadingPreset !== null}
            className="btn-secondary"
            style={{ fontSize: '0.85rem' }}
          >
            {loadingPreset === 'full' ? 'Injecting...' : '🌐 Full 4-Step Campaign'}
          </button>
        </div>
      </div>

      {/* Main 2-Column Responsive Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.8fr) minmax(360px, 1.2fr)', gap: '24px' }}>
        {/* LEFT COLUMN: Active Case Intelligence & Live Message Tester */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Active Case Intelligence Card */}
          {activeCase ? (
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span className="badge badge-accent">ACTIVE CASE</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      ID: {activeCase.id}
                    </span>
                  </div>
                  <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc' }}>{activeCase.title}</h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '4px' }}>
                    {activeCase.description || 'No description provided for this forensic case.'}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span
                    className={`badge ${activeCase.status === 'open' ? 'badge-success' : 'badge-muted'}`}
                  >
                    {activeCase.status.toUpperCase()}
                  </span>
                  {activeCase.status === 'open' && (
                    <button
                      onClick={handleCloseActiveCase}
                      className="btn-danger"
                      style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                    >
                      Close Case
                    </button>
                  )}
                </div>
              </div>

              {/* Status Metrics Bar */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: '16px',
                  backgroundColor: 'rgba(15, 23, 42, 0.6)',
                  padding: '16px',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                    Evidence Items
                  </div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent)', marginTop: '2px' }}>
                    {activeCase.evidence_count}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                    Risk Triage Score
                  </div>
                  <div
                    style={{
                      fontSize: '1.2rem',
                      fontWeight: 800,
                      marginTop: '4px',
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
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                    Cryptographic Integrity
                  </div>
                  <div
                    style={{
                      fontSize: '0.9rem',
                      fontWeight: 700,
                      marginTop: '6px',
                      color: activeVerification?.is_valid ? 'var(--success)' : 'var(--danger)',
                    }}
                  >
                    {activeVerification?.is_valid ? '✓ SHA-256 Unbroken' : '⚠ Tamper Detected'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                    Audit Chain Blocks
                  </div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f8fafc', marginTop: '2px' }}>
                    {activeVerification?.audit_chain_integrity.entry_count || 0}
                  </div>
                </div>
              </div>

              {/* Quick Navigation Buttons */}
              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button
                  onClick={() => onNavigateTab('evidence')}
                  className="btn-secondary"
                  style={{ fontSize: '0.85rem' }}
                >
                  🔬 View Evidence Lab →
                </button>
                <button
                  onClick={() => onNavigateTab('graph')}
                  className="btn-secondary"
                  style={{ fontSize: '0.85rem' }}
                >
                  🕸️ Explore Relationships →
                </button>
                <button
                  onClick={() => onNavigateTab('timeline')}
                  className="btn-secondary"
                  style={{ fontSize: '0.85rem' }}
                >
                  ⏱️ Incident Timeline →
                </button>
                <button
                  onClick={() => onNavigateTab('report')}
                  className="btn-secondary"
                  style={{ fontSize: '0.85rem' }}
                >
                  📑 Verified Report →
                </button>
              </div>
            </div>
          ) : (
            <div className="glass-panel" style={{ padding: '32px', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📂</div>
              <h3 style={{ fontSize: '1.2rem', color: '#f8fafc' }}>No Case Selected</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: '8px 0 16px' }}>
                Create a new case below or click one of the quick injection presets above to begin.
              </p>
            </div>
          )}

          {/* Real-Time Live Message & URL Threat Tester */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <span className="badge badge-accent">LIVE THREAT TESTER</span>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
                  ⚡ Test Any Real-World Message, Call, or URL in Real-Time
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  Paste an actual SMS, WhatsApp text, phone call record, or URL. The system will immutably hash it, evaluate offline classifiers, and extract entities instantly.
                </p>
              </div>
              <button
                type="button"
                onClick={fillRealScamExample}
                className="btn-secondary"
                style={{ fontSize: '0.78rem', whiteSpace: 'nowrap' }}
              >
                Sample SBI Scam Message
              </button>
            </div>

            <form onSubmit={handleTestRealtimeMessage}>
              <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    COMMUNICATION CHANNEL
                  </label>
                  <select
                    className="form-select"
                    value={testerType}
                    onChange={(e) => setTesterType(e.target.value)}
                  >
                    <option value="sms">✉️ SMS Smishing</option>
                    <option value="phone_call">📞 Phone Call Record</option>
                    <option value="chat">💬 WhatsApp / Telegram</option>
                    <option value="email_text">📧 Phishing Email</option>
                    <option value="url">🌐 Phishing URL</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    EVIDENCE TEXT CONTENT
                  </label>
                  <textarea
                    className="form-textarea"
                    rows={3}
                    placeholder="Paste real SMS, chat text, phone call transcript, or URL here..."
                    value={testerText}
                    onChange={(e) => setTesterText(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="submit"
                  disabled={testerLoading || !testerText.trim()}
                  className="btn-primary"
                  style={{ fontSize: '0.88rem' }}
                >
                  {testerLoading ? 'Running Forensic Pipeline...' : '⚡ Test & Ingest In Real-Time'}
                </button>
              </div>
            </form>

            {/* Live Instant Result Card */}
            {testerResult && (
              <div
                style={{
                  marginTop: '16px',
                  padding: '16px',
                  backgroundColor: 'rgba(15, 23, 42, 0.8)',
                  borderRadius: '8px',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="badge badge-accent">LIVE RESULT: {testerResult.evidence_id}</span>
                    <span
                      className={`badge ${
                        testerResult.label === 'suspicious' ? 'badge-danger' : 'badge-success'
                      }`}
                    >
                      {testerResult.label.toUpperCase()} (Score: {testerResult.score.toFixed(2)})
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    SHA-256: {testerResult.sha256.substring(0, 16)}...
                  </span>
                </div>

                {/* Extracted Entities */}
                <div style={{ marginBottom: '10px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700 }}>
                    EXTRACTED ENTITIES DETECTED:
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                    {testerResult.extracted_entities.length > 0 ? (
                      testerResult.extracted_entities.map((ent: any, idx: number) => (
                        <span key={idx} className="badge badge-purple" style={{ fontSize: '0.72rem' }}>
                          {ent.entity_type}: {ent.value}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>No entities recognized</span>
                    )}
                  </div>
                </div>

                {/* Top Contributing Factors */}
                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700 }}>
                    TOP ATTRIBUTED RISK N-GRAMS:
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                    {testerResult.top_factors && testerResult.top_factors.length > 0 ? (
                      testerResult.top_factors.map((f: any, idx: number) => (
                        <span key={idx} className="badge badge-warning" style={{ fontSize: '0.72rem' }}>
                          "{f.feature}" (+{f.contribution.toFixed(2)})
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Standard baseline language</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Test Sample Explained & Investigation History */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Test Sample Explained Card */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <span className="badge badge-warning">INCIDENT INTELLIGENCE</span>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f8fafc' }}>
                Test Sample Explained
              </h3>
            </div>

            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              <p style={{ marginBottom: '10px' }}>
                <strong style={{ color: '#f8fafc' }}>How It Works:</strong> Modern cybercriminals operate across multiple channels (SMS, phone calls, WhatsApp, web domains, and APK apps). SCAMTRACE ingests heterogeneous evidence and proves attribution using explicit deterministic rules.
              </p>

              <div style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border)', marginBottom: '12px' }}>
                <div style={{ fontWeight: 700, color: 'var(--accent)', marginBottom: '4px' }}>
                  Frequently Asked: Is WhatsApp Mandatory?
                </div>
                <div>
                  <strong style={{ color: '#f8fafc' }}>No, absolutely not!</strong> A case can be a single SMS, a phone call transcript, an email, or any combination. WhatsApp is merely one optional communication channel among many.
                </div>
              </div>

              <div style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border)' }}>
                <div style={{ fontWeight: 700, color: 'var(--accent)', marginBottom: '4px' }}>
                  Real-Time Messages Supported
                </div>
                <div>
                  Yes! Any live message or URL entered above is instantly evaluated using trained scikit-learn models, 100% offline with zero live network calls or privacy leakage.
                </div>
              </div>
            </div>
          </div>

          {/* Create New Case Form */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc', marginBottom: '12px' }}>
              ➕ Create New Investigation Case
            </h3>
            <form onSubmit={handleCreateCase}>
              <div style={{ marginBottom: '10px' }}>
                <input
                  type="text"
                  placeholder="Case Title (e.g. Incident #482 - SBI Smishing)"
                  className="form-input"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                />
              </div>
              <div style={{ marginBottom: '12px' }}>
                <textarea
                  placeholder="Case Description or Victim Statement..."
                  className="form-textarea"
                  rows={2}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>
              <button type="submit" className="btn-primary" style={{ width: '100%', fontSize: '0.85rem' }}>
                Create Blank Case
              </button>
            </form>
          </div>

          {/* Investigation History Column */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc' }}>
                📜 Investigation History ({cases.length})
              </h3>
              <button onClick={loadCases} className="btn-secondary" style={{ fontSize: '0.72rem', padding: '3px 8px' }}>
                Refresh
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '360px', overflowY: 'auto' }}>
              {cases.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '16px' }}>
                  No cases recorded yet.
                </div>
              ) : (
                cases.map((c) => {
                  const isCurrent = c.id === activeCaseId;
                  return (
                    <div
                      key={c.id}
                      onClick={() => onSelectCase(c.id)}
                      className="glass-panel-interactive"
                      style={{
                        padding: '12px',
                        cursor: 'pointer',
                        borderColor: isCurrent ? 'var(--accent)' : 'var(--border)',
                        backgroundColor: isCurrent ? 'rgba(56, 189, 248, 0.08)' : 'rgba(30, 41, 59, 0.5)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.9rem', color: isCurrent ? 'var(--accent)' : '#f8fafc' }}>
                          {c.title}
                        </span>
                        <span
                          className={`badge ${c.status === 'open' ? 'badge-success' : 'badge-muted'}`}
                          style={{ fontSize: '0.65rem' }}
                        >
                          {c.status}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {c.evidence_count} evidence items
                        </span>
                        <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {c.created_at.substring(0, 10)}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
