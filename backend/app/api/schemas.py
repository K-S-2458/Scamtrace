"""Pydantic request and response schemas for SCAMTRACE AI API."""
import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    notes: Optional[str] = None


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    notes: Optional[str] = None


class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    created_at: datetime.datetime
    status: str
    notes: Optional[str] = None
    evidence_count: int = 0

    class Config:
        from_attributes = True


class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    type: str
    original_filename: Optional[str] = None
    mime_type: str
    size_bytes: int
    sha256: str
    stored_path: str
    uploaded_at: datetime.datetime
    source_timestamp: Optional[datetime.datetime] = None
    timestamp_source: str
    uploader: str
    raw_text: Optional[str] = None
    analysis_status: str
    type_conflict: Optional[str] = None

    class Config:
        from_attributes = True


class EvidenceTextCreate(BaseModel):
    text: str = Field(..., min_length=1)
    type: Optional[str] = None
    source_timestamp: Optional[str] = None
    timestamp_source: Optional[str] = None
    uploader: Optional[str] = "investigator"
    original_filename: Optional[str] = None


class BulkEvidenceItem(BaseModel):
    text: str = Field(..., min_length=1)
    type: Optional[str] = None
    timestamp: Optional[str] = None
    original_filename: Optional[str] = None
    uploader: Optional[str] = "investigator"


class BulkEvidenceCreate(BaseModel):
    items: List[BulkEvidenceItem]


class NoteCreate(BaseModel):
    note: str = Field(..., min_length=1)
    actor: Optional[str] = "investigator"


class AuditResponse(BaseModel):
    id: str
    case_id: str
    seq: int
    timestamp_utc: datetime.datetime
    actor: str
    action: str
    payload_json: str
    prev_hash: str
    entry_hash: str

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    id: str
    case_id: str
    evidence_id: str
    model_name: str
    model_version: str
    label: str
    score: float
    top_factors: List[Dict[str, Any]]
    created_at: datetime.datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
