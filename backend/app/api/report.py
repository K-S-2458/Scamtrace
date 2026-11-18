"""Forensic report API endpoints for SCAMTRACE AI."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.app.db.models import Case
from backend.app.db.session import get_db
from backend.app.integrity.audit_log import record_audit_entry
from backend.app.reporting.generator import build_report_data, render_html_report

router = APIRouter(prefix="/cases/{case_id}", tags=["reporting"])


def _ensure_case(db: Session, case_id: str) -> Case:
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
    return case


@router.get("/report", response_class=HTMLResponse)
def get_html_report(case_id: str, db: Session = Depends(get_db)):
    """Generate and return standalone HTML forensic report."""
    _ensure_case(db, case_id)

    report_data = build_report_data(db, case_id)
    html_content = render_html_report(report_data)

    # Log audit entry
    record_audit_entry(
        db=db,
        case_id=case_id,
        action="generate_report",
        payload={"format": "html", "case_id": case_id},
        actor="investigator",
    )

    return HTMLResponse(content=html_content, status_code=200)


@router.get("/report.json")
def get_json_report(case_id: str, db: Session = Depends(get_db)):
    """Generate and return structured JSON forensic report with verified citations."""
    _ensure_case(db, case_id)

    report_data = build_report_data(db, case_id)

    record_audit_entry(
        db=db,
        case_id=case_id,
        action="generate_report",
        payload={"format": "json", "case_id": case_id},
        actor="investigator",
    )

    return report_data

