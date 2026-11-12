/**
 * SCAMTRACE API Client
 */

export const API_BASE = '/api';

export interface CaseItem {
  id: string;
  title: string;
  description?: string;
  created_at: string;
  status: string;
  notes?: string;
  evidence_count: number;
}

export interface EvidenceItem {
  id: string;
  case_id: string;
  type: string;
  original_filename?: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  stored_path: string;
  uploaded_at: string;
  source_timestamp?: string;
  timestamp_source: string;
  uploader: string;
  raw_text?: string;
  analysis_status: string;
  type_conflict?: string;
}

export interface AnalysisResponse {
  id: string;
  case_id: string;
  evidence_id: string;
  model_name: string;
  model_version: string;
  label: string;
  score: number;
  top_factors: Array<{
    feature: string;
    contribution: number;
    direction: string;
    value?: any;
  }>;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface GraphResponse {
  case_id: string;
  elements: {
    nodes: Array<{ data: { id: string; label?: string; [key: string]: any } }>;
    edges: Array<{ data: { id: string; source: string; target: string; [key: string]: any } }>;
  };
  stats: {
    node_count: number;
    edge_count: number;
    cluster_count: number;
  };
  clusters: Array<{
    cluster_id: string;
    evidence_count: number;
    evidence_ids: string[];
  }>;
}

export interface TimelineItem {
  evidence_id: string;
  type: string;
  original_filename?: string;
  timestamp?: string;
  source_timestamp?: string;
  timestamp_source: string;
  time_uncertain: boolean;
  time_gap_from_prev?: string;
  time_gap_seconds?: number;
  summary: string;
  conflicts: string[];
}

export interface TimelineResponse {
  case_id: string;
  total_items: number;
  has_conflicts: boolean;
  conflicts: Array<{
    type: string;
    evidence_a: string;
    evidence_b: string;
    description: string;
  }>;
  timeline: TimelineItem[];
}

export interface RiskFactor {
  factor_name: string;
  factor_type: string;
  raw_value: number;
  weight: number;
  contribution: number;
  evidence_ids: string[];
  description: string;
}

export interface RiskResponse {
  case_id: string;
  final_score: number;
  risk_band: 'low' | 'medium' | 'high';
  disclaimer: string;
  breakdown: RiskFactor[];
  components: {
    artifact_score: number;
    correlation_score: number;
    pattern_score: number;
  };
  confirmed_link_types: string[];
}

export interface VerificationResponse {
  case_id: string;
  is_valid: boolean;
  tamper_detected: boolean;
  tamper_reasons: string[];
  evidence_integrity: Array<{
    evidence_id: string;
    status: string;
    recorded_sha256: string;
    actual_sha256?: string;
  }>;
  manifest_integrity: {
    status: string;
    stored_hash?: string;
    computed_hash?: string;
  };
  audit_chain_integrity: {
    status: string;
    entry_count: number;
    details: string;
  };
}

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error ${res.status}: ${errorText}`);
  }
  return res.json();
}

// Cases
export const apiGetCases = () => fetchJson<CaseItem[]>('/cases');
export const apiGetCase = (caseId: string) => fetchJson<CaseItem>(`/cases/${caseId}`);
export const apiCreateCase = (title: string, description?: string) =>
  fetchJson<CaseItem>('/cases', {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  });
export const apiCloseCase = (caseId: string) =>
  fetchJson<CaseItem>(`/cases/${caseId}/close`, { method: 'POST' });
export const apiAddNote = (caseId: string, note: string) =>
  fetchJson<CaseItem>(`/cases/${caseId}/notes`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  });

// Evidence
export const apiGetEvidenceList = (caseId: string) =>
  fetchJson<EvidenceItem[]>(`/cases/${caseId}/evidence`);
export const apiGetEvidence = (caseId: string, evidenceId: string) =>
  fetchJson<EvidenceItem>(`/cases/${caseId}/evidence/${evidenceId}`);
export const apiUploadText = (
  caseId: string,
  text: string,
  type?: string,
  sourceTimestamp?: string,
  filename?: string
) =>
  fetchJson<EvidenceItem>(`/cases/${caseId}/evidence`, {
    method: 'POST',
    body: JSON.stringify({
      text,
      type,
      source_timestamp: sourceTimestamp,
      timestamp_source: sourceTimestamp ? 'user_entered' : 'none',
      original_filename: filename,
    }),
  });

export const apiUploadFile = async (caseId: string, formData: FormData) => {
  const res = await fetch(`${API_BASE}/cases/${caseId}/evidence`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Upload Error ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<EvidenceItem>;
};

export const apiAnalyzeEvidence = (caseId: string, evidenceId: string) =>
  fetchJson<AnalysisResponse>(`/cases/${caseId}/evidence/${evidenceId}/analyze`, {
    method: 'POST',
  });

// Correlation & Graph
export const apiCorrelate = (caseId: string) =>
  fetchJson<{ case_id: string; edges_count: number; edges: any[] }>(
    `/cases/${caseId}/correlate`,
    { method: 'POST', body: JSON.stringify({}) }
  );
export const apiGetGraph = (caseId: string) =>
  fetchJson<GraphResponse>(`/cases/${caseId}/graph`);

// Timeline
export const apiGetTimeline = (caseId: string) =>
  fetchJson<TimelineResponse>(`/cases/${caseId}/timeline`);

// Risk
export const apiGetRisk = (caseId: string) =>
  fetchJson<RiskResponse>(`/cases/${caseId}/risk`);

// Integrity
export const apiVerifyCase = (caseId: string) =>
  fetchJson<VerificationResponse>(`/cases/${caseId}/verify`, { method: 'POST' });

// Report
export const apiGetReportJson = (caseId: string) =>
  fetchJson<any>(`/cases/${caseId}/report.json`);

// Findings
export interface IdentifiedEntityItem {
  value: string;
  raw_value: string;
  evidence_ids: string[];
}

export interface KeyFindingItem {
  id: string;
  title: string;
  explanation: string;
  evidence_ids: string[];
  confidence: number;
  strength: string;
  rule_id: string;
}

export interface FindingsResponse {
  case_id: string;
  title: string;
  evidence_count: number;
  connected_artifacts_count?: number;
  suspicious_indicators_count?: number;
  evidence_confidence?: number;
  risk_score: number;
  risk_band: string;
  identified_entities: {
    phone_numbers: IdentifiedEntityItem[];
    domains: IdentifiedEntityItem[];
    upi_handles: IdentifiedEntityItem[];
    package_names: IdentifiedEntityItem[];
    certificate_hashes: IdentifiedEntityItem[];
    brand_names: IdentifiedEntityItem[];
    amounts: IdentifiedEntityItem[];
  };
  key_findings: KeyFindingItem[];
  conclusion: {
    summary: string;
    confirmed_observations: string[];
    system_inferences: string[];
    unverified_possibilities: string[];
  };
}

export const apiGetFindings = (caseId: string) =>
  fetchJson<FindingsResponse>(`/cases/${caseId}/findings`);
