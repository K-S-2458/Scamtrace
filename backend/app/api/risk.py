"""Risk scoring API router for SCAMTRACE AI."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.models import Case
from backend.app.db.session import get_db
from backend.app.risk.scoring import compute_case_risk

router = APIRouter(prefix="/cases/{case_id}", tags=["risk"])


@router.get("/risk")
def get_case_risk_assessment(case_id: str, db: Session = Depends(get_db)):
    """Retrieve multi-factor transparent risk score and factor breakdown for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    return compute_case_risk(db, case_id)

