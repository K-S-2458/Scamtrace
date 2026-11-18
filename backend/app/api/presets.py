"""Preset injection API router for SCAMTRACE AI.
Atomically creates and initializes entire multi-artifact investigation presets.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.models import Case
from backend.app.db.session import get_db
from backend.app.db.seed import _seed_smishing_case, _seed_vishing_case, _seed_multimodal_campaign

router = APIRouter(prefix="/presets", tags=["presets"])


@router.post("/{preset_name}", status_code=status.HTTP_200_OK)
def load_preset(preset_name: str, db: Session = Depends(get_db)):
    """Atomically create and return pre-configured investigation scenario preset."""
    name = preset_name.lower().strip()

    if name in ("smishing", "sms"):
        case = db.query(Case).filter(Case.id == "CASE-SMISHING-01").first()
        if not case:
            case = _seed_smishing_case(db)
        return {
            "case_id": case.id,
            "title": case.title,
            "description": case.description,
            "status": "ready"
        }

    elif name in ("vishing", "call", "apk"):
        case = db.query(Case).filter(Case.id == "CASE-VISHING-02").first()
        if not case:
            case = _seed_vishing_case(db)
        return {
            "case_id": case.id,
            "title": case.title,
            "description": case.description,
            "status": "ready"
        }

    elif name in ("full", "multimodal", "campaign"):
        case = db.query(Case).filter(Case.id == "CASE-CAMPAIGN-03").first()
        if not case:
            case = _seed_multimodal_campaign(db)
        return {
            "case_id": case.id,
            "title": case.title,
            "description": case.description,
            "status": "ready"
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown preset '{preset_name}'. Supported: 'smishing', 'vishing', 'full'"
        )
