import React, { useEffect, useState } from 'react';
import {
  AnalysisResponse,
  apiAnalyzeEvidence,
  apiGetEvidenceList,
  apiUploadFile,
  apiUploadText,
  EvidenceItem,
} from '../api/client';

interface EvidenceLabProps {
  activeCaseId: string | null;
}

export const EvidenceLab: React.FC<EvidenceLabProps> = ({ activeCaseId }) => {
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [uploadTab, setUploadTab] = useState<'paste' | 'file'>('paste');

  // Form states
  const [pasteText, setPasteText] = useState('');
  const [evidenceType, setEvidenceType] = useState('sms');
  const [sourceTimestamp, setSourceTimestamp] = useState('');
  const [originalFilename, setOriginalFilename] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Analysis result modal / drawer
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisResponse | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const loadEvidence = async () => {
    if (!activeCaseId) return;
    try {
      const items = await apiGetEvidenceList(activeCaseId);
      setEvidenceList(items);
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadEvidence();
  }, [activeCaseId]);

  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCaseId || !pasteText.trim()) return;

    try {
      await apiUploadText(
        activeCaseId,
        pasteText,
        evidenceType,
        sourceTimestamp || undefined,
        originalFilename || undefined
      );
      setPasteText('');
      setSourceTimestamp('');
      setOriginalFilename('');
      await loadEvidence();
    } catch (err: any) {
      alert(`Error uploading text: ${err.message}`);
    }
  };

  const handleFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCaseId || !selectedFile) return;

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (evidenceType) formData.append('type', evidenceType);
      if (sourceTimestamp) formData.append('source_timestamp', sourceTimestamp);

      await apiUploadFile(activeCaseId, formData);
      setSelectedFile(null);
      setSourceTimestamp('');
      await loadEvidence();
    } catch (err: any) {
      alert(`Error uploading file: ${err.message}`);
    }
  };

  const handleAnalyze = async (evidenceId: string) => {
    if (!activeCaseId) return;
    setAnalyzingId(evidenceId);
    try {
      const res = await apiAnalyzeEvidence(activeCaseId, evidenceId);
      setActiveAnalysis(res);
      await loadEvidence();
    } catch (err: any) {
      alert(`Analysis failed: ${err.message}`);
    } finally {
      setAnalyzingId(null);
    }
  };

  const copyToClipboard = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  if (!activeCaseId) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Please select or create an investigation case from the Dashboard first.
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Evidence Lab</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Ingest raw multimodal digital evidence with write-once immutable storage and run explainable ML triage classifiers.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: '24px' }}>
        {/* Left Column: Ingestion Controls */}
        <div>
          <div
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '20px',
            }}
          >
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button
                type="button"
                onClick={() => setUploadTab('paste')}
                style={{
                  flex: 1,
                  padding: '8px',
                  backgroundColor: uploadTab === 'paste' ? 'var(--accent)' : 'var(--bg-tertiary)',
                  color: uploadTab === 'paste' ? '#0f172a' : 'var(--text-primary)',
                  border: 'none',
                  borderRadius: '4px',
                  fontWeight: 600,
                }}
              >
                Paste Text / Content
              </button>
              <button
                type="button"
                onClick={() => setUploadTab('file')}
                style={{
                  flex: 1,
                  padding: '8px',
                  backgroundColor: uploadTab === 'file' ? 'var(--accent)' : 'var(--bg-tertiary)',
                  color: uploadTab === 'file' ? '#0f172a' : 'var(--text-primary)',
                  border: 'none',
                  borderRadius: '4px',
                  fontWeight: 600,
                }}
              >
                Upload File
              </button>
            </div>

            {uploadTab === 'paste' ? (
              <form onSubmit={handlePasteSubmit}>
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    Evidence Content *
                  </label>
                  <textarea
                    rows={5}
                    value={pasteText}
                    onChange={(e) => setPasteText(e.target.value)}
                    placeholder="Paste SMS message, chat log, URL, or JSON manifest metadata..."
                    required
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '4px',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.85rem',
                    }}
                  />
                </div>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    Artifact Modality Type
                  </label>
                  <select
                    value={evidenceType}
                    onChange={(e) => setEvidenceType(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '4px',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <option value="sms">SMS Message</option>
                    <option value="chat">Chat Transcript</option>
                    <option value="url">URL Endpoint</option>
                    <option value="apk">Android APK (Manifest Metadata)</option>
                    <option value="email_text">Email Message Text</option>
                  </select>
                </div>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    Source Timestamp (Optional)
                  </label>
                  <input
                    type="text"
                    value={sourceTimestamp}
                    onChange={(e) => setSourceTimestamp(e.target.value)}
                    placeholder="YYYY-MM-DD HH:MM:SS or DD/MM/YYYY HH:MM"
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
                    Original Filename (Optional)
                  </label>
                  <input
                    type="text"
                    value={originalFilename}
                    onChange={(e) => setOriginalFilename(e.target.value)}
                    placeholder="e.g. sms_dump_1001.txt"
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
                  Ingest & Hash Evidence (Write-Once)
                </button>
              </form>
            ) : (
              <form onSubmit={handleFileSubmit}>
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    Select Evidence File *
                  </label>
                  <input
                    type="file"
                    onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                    required
                    style={{
                      width: '100%',
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                    }}
                  />
                </div>

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    Artifact Modality Type
                  </label>
                  <select
                    value={evidenceType}
                    onChange={(e) => setEvidenceType(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '4px',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <option value="screenshot">Screenshot / Image</option>
                    <option value="apk">Android APK Package</option>
                    <option value="sms">SMS Text Dump</option>
                    <option value="chat">Chat Export</option>
                    <option value="url">URL Text</option>
                  </select>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    Source Timestamp (Optional)
                  </label>
                  <input
                    type="text"
                    value={sourceTimestamp}
                    onChange={(e) => setSourceTimestamp(e.target.value)}
                    placeholder="YYYY-MM-DD HH:MM:SS"
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
                  Upload & Hash File (Write-Once)
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Right Column: Evidence List Table & Analysis Drawer */}
        <div>
          <div
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '20px',
            }}
          >
            <h2 style={{ fontSize: '1.15rem', marginBottom: '16px' }}>
              Ingested Evidence Artifacts ({evidenceList.length})
            </h2>

            {evidenceList.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No evidence ingested for this case yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {evidenceList.map((ev) => (
                  <div
                    key={ev.id}
                    style={{
                      border: '1px solid var(--border)',
                      borderRadius: '6px',
                      padding: '14px',
                      backgroundColor: 'var(--bg-primary)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--accent)' }}>
                          {ev.id}
                        </span>
                        <span
                          style={{
                            fontSize: '0.75rem',
                            padding: '2px 6px',
                            borderRadius: '3px',
                            backgroundColor: 'var(--bg-tertiary)',
                            textTransform: 'uppercase',
                          }}
                        >
                          {ev.type}
                        </span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          {ev.original_filename}
                        </span>
                      </div>

                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          onClick={() => handleAnalyze(ev.id)}
                          disabled={analyzingId === ev.id}
                          style={{
                            backgroundColor: ev.analysis_status === 'analyzed' ? 'var(--bg-tertiary)' : 'var(--accent)',
                            color: ev.analysis_status === 'analyzed' ? 'var(--text-primary)' : '#0f172a',
                            border: 'none',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                          }}
                        >
                          {analyzingId === ev.id ? 'Analyzing...' : ev.analysis_status === 'analyzed' ? 'Re-Analyze' : 'Analyze'}
                        </button>
                      </div>
                    </div>

                    {/* Content Preview */}
                    {ev.raw_text && (
                      <p
                        style={{
                          margin: '8px 0',
                          fontSize: '0.85rem',
                          color: 'var(--text-primary)',
                          fontFamily: ev.type === 'apk' || ev.type === 'url' ? 'var(--font-mono)' : 'inherit',
                          maxHeight: '60px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {ev.raw_text}
                      </p>
                    )}

                    {/* Metadata & Cryptographic Hash */}
                    <div
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '12px',
                        alignItems: 'center',
                        fontSize: '0.78rem',
                        color: 'var(--text-secondary)',
                        marginTop: '8px',
                        paddingTop: '8px',
                        borderTop: '1px solid rgba(255,255,255,0.06)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span>SHA-256:</span>
                        <code style={{ fontSize: '0.75rem' }}>{ev.sha256.substring(0, 16)}...</code>
                        <button
                          onClick={() => copyToClipboard(ev.sha256)}
                          style={{
                            backgroundColor: 'transparent',
                            border: 'none',
                            color: copiedHash === ev.sha256 ? 'var(--success)' : 'var(--accent)',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                          }}
                        >
                          {copiedHash === ev.sha256 ? '✓ Copied' : 'Copy'}
                        </button>
                      </div>

                      <div>Size: {ev.size_bytes} B</div>
                      <div>Time: {ev.source_timestamp || 'None'}</div>
                      {ev.type_conflict && (
                        <div style={{ color: 'var(--warning)' }}>⚠ {ev.type_conflict}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Analysis Explanation Inspection Card */}
          {activeAnalysis && (
            <div
              style={{
                marginTop: '20px',
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--accent)',
                borderRadius: '8px',
                padding: '20px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '1.1rem', color: 'var(--accent)' }}>
                  Analysis Explanation for Artifact {activeAnalysis.evidence_id}
                </h3>
                <span
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    backgroundColor: activeAnalysis.label === 'suspicious' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                    color: activeAnalysis.label === 'suspicious' ? 'var(--danger)' : 'var(--success)',
                  }}
                >
                  {activeAnalysis.label.toUpperCase()} (Score: {(activeAnalysis.score).toFixed(2)})
                </span>
              </div>

              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Model: <strong>{activeAnalysis.model_name}</strong> (v{activeAnalysis.model_version})
              </p>

              <h4 style={{ fontSize: '0.9rem', marginBottom: '6px' }}>Top Contributing Forensic Features:</h4>
              <ul style={{ paddingLeft: '20px', fontSize: '0.85rem' }}>
                {activeAnalysis.top_factors.map((f, i) => (
                  <li key={i} style={{ marginBottom: '4px' }}>
                    <code style={{ color: 'var(--accent)' }}>{f.feature}</code> — Contribution: +{f.contribution}
                    {f.value !== undefined && f.value !== null && ` (Value: ${f.value})`}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
