"""Evidence ingestion and retrieval API endpoints for SCAMTRACE AI."""
import csv
import datetime
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.schemas import (
    AnalysisResponse,
    BulkEvidenceCreate,
    EvidenceResponse,
    EvidenceTextCreate,
)
from backend.app.config import MAX_UPLOAD_SIZE_BYTES
from backend.app.db.models import Analysis, Case, Evidence
from backend.app.db.session import get_db
from backend.app.analyzers import get_analyzer
import uuid
from backend.app.ingestion.storage import (
    compute_sha256,
    detect_evidence_type,
    parse_timestamp,
    store_evidence_file,
)
from backend.app.integrity.audit_log import record_audit_entry
from backend.app.integrity.manifest import generate_manifest

router = APIRouter(prefix="/cases/{case_id}/evidence", tags=["evidence"])


def get_next_evidence_id(db: Session, case_id: str) -> str:
    """Generate sequential evidence ID (e.g. E1, E2, E3)."""
    existing_items = db.query(Evidence.id).filter(Evidence.case_id == case_id).all()
    existing_ids = {row[0] for row in existing_items}
    idx = 1
    while f"E{idx}" in existing_ids:
        idx += 1
    return f"E{idx}"


def ingest_single_evidence(
    db: Session,
    case_id: str,
    raw_bytes: bytes,
    original_filename: Optional[str],
    user_type: Optional[str] = None,
    source_timestamp_str: Optional[str] = None,
    timestamp_source: Optional[str] = None,
    uploader: str = "investigator",
    raw_text: Optional[str] = None,
) -> Evidence:
    """Core evidence ingestion pipeline."""
    if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Evidence exceeds maximum allowed size ({MAX_UPLOAD_SIZE_BYTES} bytes)"
        )

    # Detect type and check conflict
    detected_type = detect_evidence_type(original_filename, raw_bytes, hint_text=raw_text)
    type_conflict = None
    if user_type and user_type.strip():
        final_type = user_type.strip().lower()
        if final_type != detected_type:
            type_conflict = f"User selected '{final_type}' but analyzer detected '{detected_type}'"
    else:
        final_type = detected_type

    # Determine extension
    ext = "bin"
    if original_filename and "." in original_filename:
        ext = original_filename.rsplit(".", 1)[-1].lower()
    elif final_type in {"sms", "chat", "email_text"}:
        ext = "txt"
    elif final_type == "url":
        ext = "url.txt"
    elif final_type == "apk":
        ext = "apk"
    elif final_type == "screenshot":
        ext = "png"

    # Assign sequential ID
    evidence_id = get_next_evidence_id(db, case_id)

    # Store file immutably
    try:
        stored_path, sha256_hash, size_bytes = store_evidence_file(
            case_id=case_id,
            evidence_id=evidence_id,
            file_bytes=raw_bytes,
            extension=ext,
        )
    except FileExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Evidence write conflict: {str(e)}"
        )

    # Determine mime-type
    mime_type = "text/plain" if final_type in {"sms", "chat", "url", "email_text"} else "application/octet-stream"
    if final_type == "apk":
        mime_type = "application/vnd.android.package-archive"
    elif final_type == "screenshot":
        mime_type = "image/png"

    # Source timestamp parsing
    parsed_source_ts = None
    final_ts_source = "none"
    if source_timestamp_str:
        parsed_source_ts = parse_timestamp(source_timestamp_str)
        if parsed_source_ts:
            final_ts_source = timestamp_source or "user_entered"

    # If raw_text is text type and not provided, decode from raw_bytes
    if raw_text is None and final_type in {"sms", "chat", "url", "email_text"}:
        try:
            raw_text = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            raw_text = None

    evidence = Evidence(
        id=evidence_id,
        case_id=case_id,
        type=final_type,
        original_filename=original_filename or f"{evidence_id}.{ext}",
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256=sha256_hash,
        stored_path=str(stored_path),
        uploaded_at=datetime.datetime.utcnow(),
        source_timestamp=parsed_source_ts,
        timestamp_source=final_ts_source,
        uploader=uploader or "investigator",
        raw_text=raw_text,
        analysis_status="pending",
        type_conflict=type_conflict,
    )

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # Regenerate manifest
    manifest_data = generate_manifest(case_id, db)

    # Append audit entry
    record_audit_entry(
        db=db,
        case_id=case_id,
        action="ingest",
        payload={
            "evidence_id": evidence_id,
            "type": final_type,
            "sha256": sha256_hash,
            "size_bytes": size_bytes,
            "manifest_hash": manifest_data["manifest_hash"],
        },
        actor=uploader or "investigator",
    )

    return evidence


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Ingest evidence via multipart file upload or pasted text JSON."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body_bytes = await request.body()
        try:
            payload = json.loads(body_bytes)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        text = payload.get("text", "")
        if not text.strip():
            raise HTTPException(status_code=400, detail="Pasted text cannot be empty")
        raw_bytes = text.encode("utf-8")
        evidence = ingest_single_evidence(
            db=db,
            case_id=case_id,
            raw_bytes=raw_bytes,
            original_filename=payload.get("original_filename"),
            user_type=payload.get("type"),
            source_timestamp_str=payload.get("source_timestamp"),
            timestamp_source=payload.get("timestamp_source"),
            uploader=payload.get("uploader", "investigator"),
            raw_text=text,
        )
        return evidence

    elif "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        text_content = form.get("text")
        user_type = form.get("type")
        source_timestamp = form.get("source_timestamp")
        timestamp_source = form.get("timestamp_source")
        uploader = form.get("uploader", "investigator")

        if file and hasattr(file, "read"):
            content_bytes = await file.read()
            filename = file.filename
            evidence = ingest_single_evidence(
                db=db,
                case_id=case_id,
                raw_bytes=content_bytes,
                original_filename=filename,
                user_type=str(user_type) if user_type else None,
                source_timestamp_str=str(source_timestamp) if source_timestamp else None,
                timestamp_source=str(timestamp_source) if timestamp_source else None,
                uploader=str(uploader) if uploader else "investigator",
            )
            return evidence
        elif text_content:
            text = str(text_content)
            raw_bytes = text.encode("utf-8")
            evidence = ingest_single_evidence(
                db=db,
                case_id=case_id,
                raw_bytes=raw_bytes,
                original_filename=f"pasted_{datetime.datetime.utcnow().strftime('%H%M%S')}.txt",
                user_type=str(user_type) if user_type else None,
                source_timestamp_str=str(source_timestamp) if source_timestamp else None,
                timestamp_source=str(timestamp_source) if timestamp_source else None,
                uploader=str(uploader) if uploader else "investigator",
                raw_text=text,
            )
            return evidence
        else:
            raise HTTPException(status_code=400, detail="Either 'file' or 'text' must be provided")
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported Media Type. Send application/json or multipart/form-data"
        )


@router.post("/bulk", response_model=List[EvidenceResponse], status_code=status.HTTP_201_CREATED)
async def upload_bulk_evidence(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Bulk ingest evidence items from CSV file or JSON list."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    content_type = request.headers.get("content-type", "")
    items_to_ingest = []

    if "application/json" in content_type:
        body = await request.json()
        raw_items = body.get("items", []) if isinstance(body, dict) else body
        for itm in raw_items:
            items_to_ingest.append({
                "text": itm.get("text", ""),
                "type": itm.get("type"),
                "timestamp": itm.get("timestamp"),
                "original_filename": itm.get("original_filename"),
                "uploader": itm.get("uploader", "investigator"),
            })

    elif "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if not file or not hasattr(file, "read"):
            raise HTTPException(status_code=400, detail="CSV file required in 'file' form field")
        content = (await file.read()).decode("utf-8", errors="replace")
        csv_reader = csv.DictReader(io.StringIO(content))
        for row in csv_reader:
            # Look for text column (text, message, content, body)
            text_val = row.get("text") or row.get("message") or row.get("content") or row.get("body") or ""
            ts_val = row.get("timestamp") or row.get("source_timestamp") or row.get("date") or row.get("time")
            type_val = row.get("type")
            fn_val = row.get("filename") or row.get("original_filename")
            items_to_ingest.append({
                "text": text_val,
                "type": type_val,
                "timestamp": ts_val,
                "original_filename": fn_val,
                "uploader": "investigator",
            })
    else:
        raise HTTPException(status_code=400, detail="Content-Type must be application/json or multipart/form-data")

    results = []
    for item in items_to_ingest:
        text = item["text"]
        if not text.strip():
            continue
        raw_bytes = text.encode("utf-8")
        ev = ingest_single_evidence(
            db=db,
            case_id=case_id,
            raw_bytes=raw_bytes,
            original_filename=item.get("original_filename"),
            user_type=item.get("type"),
            source_timestamp_str=item.get("timestamp"),
            timestamp_source="user_entered" if item.get("timestamp") else "none",
            uploader=item.get("uploader", "investigator"),
            raw_text=text,
        )
        results.append(ev)

    return results


@router.get("", response_model=List[EvidenceResponse])
def list_case_evidence(case_id: str, db: Session = Depends(get_db)):
    """List all evidence items registered in a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    items = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.uploaded_at.asc())
        .all()
    )
    return items


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(case_id: str, evidence_id: str, db: Session = Depends(get_db)):
    """Retrieve details of a specific evidence item."""
    ev = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id, Evidence.id == evidence_id)
        .first()
    )
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found in case {case_id}")
    return ev


@router.post("/{evidence_id}/analyze", response_model=AnalysisResponse)
def analyze_evidence(case_id: str, evidence_id: str, db: Session = Depends(get_db)):
    """Execute multimodal analysis on an evidence item and return explained factors."""
    ev = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id, Evidence.id == evidence_id)
        .first()
    )
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found in case {case_id}")

    # Read stored bytes
    stored_path = Path(ev.stored_path)
    file_bytes = b""
    if stored_path.exists():
        with open(stored_path, "rb") as f:
            file_bytes = f.read()

    analyzer = get_analyzer(ev.type)
    result = analyzer.analyze(
        raw_bytes=file_bytes,
        raw_text=ev.raw_text,
    )

    # Persist analysis
    analysis_record = (
        db.query(Analysis)
        .filter(Analysis.case_id == case_id, Analysis.evidence_id == evidence_id)
        .first()
    )
    if not analysis_record:
        analysis_record = Analysis(
            id=str(uuid.uuid4()),
            case_id=case_id,
            evidence_id=evidence_id,
            model_name=result.model_name,
            model_version=result.model_version,
            label=result.label,
            score=result.score,
            top_factors=json.dumps(result.top_factors),
            created_at=datetime.datetime.utcnow(),
        )
        db.add(analysis_record)
    else:
        analysis_record.model_name = result.model_name
        analysis_record.model_version = result.model_version
        analysis_record.label = result.label
        analysis_record.score = result.score
        analysis_record.top_factors = json.dumps(result.top_factors)
        analysis_record.created_at = datetime.datetime.utcnow()

    ev.analysis_status = "analyzed"
    db.commit()
    db.refresh(analysis_record)

    # Record audit log
    record_audit_entry(
        db=db,
        case_id=case_id,
        action="analyze",
        payload={
            "evidence_id": evidence_id,
            "model_name": result.model_name,
            "label": result.label,
            "score": result.score,
        },
        actor="investigator",
    )

    return AnalysisResponse(
        id=analysis_record.id,
        case_id=case_id,
        evidence_id=evidence_id,
        model_name=result.model_name,
        model_version=result.model_version,
        label=result.label,
        score=result.score,
        top_factors=result.top_factors,
        created_at=analysis_record.created_at,
        metadata=result.metadata,
    )

