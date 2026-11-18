"""Knowledge graph and correlation API endpoints for SCAMTRACE AI."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.correlation.engine import correlate_case
from backend.app.db.models import Case
from backend.app.db.session import get_db
from backend.app.graph.builder import build_case_graph
from backend.app.graph.serialize import serialize_to_cytoscape

router = APIRouter(prefix="/cases/{case_id}", tags=["graph"])


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


@router.post("/correlate")
def run_correlation(
    case_id: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """Run correlation rules and generate cross-artifact edges for a case."""
    _ensure_case(db, case_id)

    rule_switches = payload.get("rule_switches") if payload else None
    redirect_mappings = payload.get("redirect_mappings") if payload else None

    proposals = correlate_case(
        db=db,
        case_id=case_id,
        rule_switches=rule_switches,
        redirect_mappings=redirect_mappings,
        persist=True,
    )

    return {
        "case_id": case_id,
        "edges_count": len(proposals),
        "edges": [
            {
                "source": p.source_evidence_id,
                "target": p.target_evidence_id,
                "link_type": p.link_type,
                "confidence": p.confidence,
                "reason": p.reason,
                "supporting_fields": p.supporting_fields,
            }
            for p in proposals
        ],
    }


@router.get("/graph")
def get_graph(case_id: str, db: Session = Depends(get_db)):
    """Retrieve Cytoscape.js formatted knowledge graph for a case."""
    _ensure_case(db, case_id)

    g = build_case_graph(db, case_id)
    return serialize_to_cytoscape(g)


