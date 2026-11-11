"""Case management API endpoints for SCAMTRACE AI."""
import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.schemas import (
    AuditResponse,
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    NoteCreate,
)
from backend.app.config import CASES_DIR
from backend.app.db.models import AuditEntry, Case, Evidence
from backend.app.db.session import get_db
from backend.app.integrity.audit_log import record_audit_entry
from backend.app.integrity.manifest import generate_manifest

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(case_in: CaseCreate, db: Session = Depends(get_db)):
    """Create a new forensic investigation case."""
    case_id = f"CASE-{datetime.datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    case = Case(
        id=case_id,
        title=case_in.title,
        description=case_in.description,
        notes=case_in.notes,
        status="open",
        created_at=datetime.datetime.utcnow(),
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Initialize case directory and manifest
    case_dir = CASES_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    generate_manifest(case_id, db)

    # Record audit log
    record_audit_entry(
        db=db,
        case_id=case_id,
        action="create_case",
        payload={"case_id": case_id, "title": case.title, "description": case.description},
        actor="investigator",
    )

    resp = CaseResponse.model_validate(case)
    resp.evidence_count = 0
    return resp


@router.get("", response_model=List[CaseResponse])
def list_cases(db: Session = Depends(get_db)):
    """List all investigation cases."""
    cases = db.query(Case).order_by(Case.created_at.desc()).all()
    results = []
    for c in cases:
        ev_count = db.query(Evidence).filter(Evidence.case_id == c.id).count()
        r = CaseResponse.model_validate(c)
        r.evidence_count = ev_count
        results.append(r)
    return results


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    """Get details of a specific case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    ev_count = db.query(Evidence).filter(Evidence.case_id == case.id).count()
    resp = CaseResponse.model_validate(case)
    resp.evidence_count = ev_count
    return resp


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(case_id: str, case_update: CaseUpdate, db: Session = Depends(get_db)):
    """Update case metadata or notes."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    updated_fields = {}
    if case_update.title is not None:
        case.title = case_update.title
        updated_fields["title"] = case.title
    if case_update.description is not None:
        case.description = case_update.description
        updated_fields["description"] = case.description
    if case_update.notes is not None:
        case.notes = case_update.notes
        updated_fields["notes"] = case.notes

    db.commit()
    db.refresh(case)

    record_audit_entry(
        db=db,
        case_id=case_id,
        action="edit_note" if "notes" in updated_fields else "update_case",
        payload=updated_fields,
        actor="investigator",
    )

    ev_count = db.query(Evidence).filter(Evidence.case_id == case.id).count()
    resp = CaseResponse.model_validate(case)
    resp.evidence_count = ev_count
    return resp


@router.post("/{case_id}/close", response_model=CaseResponse)
def close_case(case_id: str, db: Session = Depends(get_db)):
    """Close an investigation case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    case.status = "closed"
    db.commit()
    db.refresh(case)

    record_audit_entry(
        db=db,
        case_id=case_id,
        action="close_case",
        payload={"case_id": case_id, "status": "closed"},
        actor="investigator",
    )

    ev_count = db.query(Evidence).filter(Evidence.case_id == case.id).count()
    resp = CaseResponse.model_validate(case)
    resp.evidence_count = ev_count
    return resp


@router.post("/{case_id}/notes", response_model=CaseResponse)
def add_case_note(case_id: str, note_in: NoteCreate, db: Session = Depends(get_db)):
    """Append notes to a case and log an audit entry."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    timestamp_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    new_note_entry = f"[{timestamp_str}] ({note_in.actor}): {note_in.note}"

    if case.notes:
        case.notes = f"{case.notes}\n{new_note_entry}"
    else:
        case.notes = new_note_entry

    db.commit()
    db.refresh(case)

    record_audit_entry(
        db=db,
        case_id=case_id,
        action="edit_note",
        payload={"note_added": note_in.note, "actor": note_in.actor},
        actor=note_in.actor or "investigator",
    )

    ev_count = db.query(Evidence).filter(Evidence.case_id == case.id).count()
    resp = CaseResponse.model_validate(case)
    resp.evidence_count = ev_count
    return resp


@router.get("/{case_id}/audit", response_model=List[AuditResponse])
def get_case_audit_log(case_id: str, db: Session = Depends(get_db)):
    """Retrieve the full cryptographic audit log for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    entries = (
        db.query(AuditEntry)
        .filter(AuditEntry.case_id == case_id)
        .order_by(AuditEntry.seq.asc())
        .all()
    )
    return entries

