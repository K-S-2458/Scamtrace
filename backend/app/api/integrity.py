"""Integrity verification API router for SCAMTRACE AI."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.models import Case
from backend.app.db.session import get_db
from backend.app.integrity.audit_log import record_audit_entry
from backend.app.integrity.verify import verify_case_integrity

router = APIRouter(prefix="/cases/{case_id}", tags=["integrity"])


@router.post("/verify")
def verify_case(case_id: str, db: Session = Depends(get_db)):
    """Run cryptographic tamper detection and integrity verification on a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    report = verify_case_integrity(db=db, case_id=case_id)

    # Note: Recording the audit entry occurs after computing verification
    record_audit_entry(
        db=db,
        case_id=case_id,
        action="verify",
        payload={
            "is_valid": report["is_valid"],
            "tamper_detected": report["tamper_detected"],
            "reasons": report["tamper_reasons"],
        },
        actor="investigator",
    )

    return report

