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
        try:
            from backend.app.db.seed import seed_default_cases
            seed_default_cases(db)
            case = db.query(Case).filter(Case.id == case_id).first()
        except Exception:
            pass
    if not case:
        import datetime
        case = Case(
            id=case_id,
            title=f"Investigation ({case_id})",
            description="Active investigation scenario",
            status="open",
            created_at=datetime.datetime.utcnow(),
        )
        db.add(case)
        db.commit()

    return build_case_timeline(db, case_id)

