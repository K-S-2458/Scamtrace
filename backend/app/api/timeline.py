"""Incident timeline API router for SCAMTRACE AI."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.models import Case
from backend.app.db.session import get_db
from backend.app.timeline.builder import build_case_timeline

router = APIRouter(prefix="/cases/{case_id}", tags=["timeline"])


@router.get("/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db)):
    """Retrieve chronological incident timeline with conflict annotations."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    return build_case_timeline(db, case_id)

