"""Audited forensic report generator for SCAMTRACE AI.
Strictly enforces claim-to-evidence citation rules: Every factual narrative claim
must explicitly cite one or more valid evidence IDs.
"""
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from backend.app.config import ROOT_DIR
from backend.app.correlation.engine import correlate_case
from backend.app.db.models import Analysis, Case, Edge, Entity, Evidence
from backend.app.integrity.verify import verify_case_integrity
from backend.app.risk.scoring import compute_case_risk
from backend.app.timeline.builder import build_case_timeline

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


class ClaimCitationError(ValueError):
    """Raised when a forensic report assertion violates citation traceability."""
    pass


def validate_claim_citations(claims: List[Dict[str, Any]], valid_evidence_ids: List[str]) -> None:
    """Validate that every generated narrative claim cites at least one valid evidence ID."""
    valid_id_set = set(valid_evidence_ids)
    for idx, claim in enumerate(claims):
        ev_ids = claim.get("evidence_ids")
        if not ev_ids or not isinstance(ev_ids, list) or len(ev_ids) == 0:
            raise ClaimCitationError(
                f"Claim #{idx+1} failed citation enforcement: claim lacks 'evidence_ids'. Text: '{claim.get('claim_text')}'"
            )
        for eid in ev_ids:
            if eid not in valid_id_set:
                raise ClaimCitationError(
                    f"Claim #{idx+1} cites unknown evidence ID '{eid}'. Known IDs: {valid_evidence_ids}"
                )


def generate_structured_case_summary(
    evidence_records: List[Evidence],
    edges: List[Edge],
    analyses: List[Analysis]
) -> List[Dict[str, Any]]:
    """Synthesize deterministic claim objects strictly grounded in verified evidence IDs and correlation edges."""
    claims: List[Dict[str, Any]] = []
    ev_map = {e.id: e for e in evidence_records}

    # 1. Claims derived directly from correlation edges
    for edge in edges:
        src = ev_map.get(edge.source_evidence_id)
        tgt = ev_map.get(edge.target_evidence_id)
        if src and tgt:
            claim_text = (
                f"Artifact {src.id} ({src.type.upper()}) and Artifact {tgt.id} ({tgt.type.upper()}) "
                f"are linked via {edge.link_type} (confidence {edge.confidence:.2f}): {edge.reason}"
            )
            claims.append({
                "claim_text": claim_text,
                "evidence_ids": [src.id, tgt.id],
                "rule_id": edge.link_type,
                "confidence": edge.confidence,
            })

    # 2. Claims derived from high-threat artifact analyses
    for an in analyses:
        if an.score >= 0.5:
            ev = ev_map.get(an.evidence_id)
            if ev:
                claim_text = (
                    f"Artifact {ev.id} ({ev.type.upper()}) was flagged as {an.label.upper()} "
                    f"by {an.model_name} (threat score: {an.score:.2f})."
                )
                claims.append({
                    "claim_text": claim_text,
                    "evidence_ids": [ev.id],
                    "rule_id": "ANALYZER_CLASSIFICATION",
                    "confidence": round(an.score, 2),
                })

    return claims


def build_report_data(db: Session, case_id: str) -> Dict[str, Any]:
    """Compile comprehensive forensic report model with citation verification."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case {case_id} not found")

    evidence_records = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.id)
        .all()
    )
    valid_evidence_ids = [e.id for e in evidence_records]

    edges = (
        db.query(Edge)
        .filter(Edge.case_id == case_id)
        .order_by(Edge.confidence.desc())
        .all()
    )

    analyses = (
        db.query(Analysis)
        .filter(Analysis.case_id == case_id)
        .all()
    )

    # 1. Timeline
    timeline_data = build_case_timeline(db, case_id)

    # 2. Risk Evaluation
    risk_data = compute_case_risk(db, case_id)

    # 3. Integrity Verification
    integrity_data = verify_case_integrity(db, case_id)

    # 4. Generate & Validate Claims
    claims = generate_structured_case_summary(evidence_records, edges, analyses)
    validate_claim_citations(claims, valid_evidence_ids)

    # 5. Inventory Table
    inventory = []
    for ev in evidence_records:
        inventory.append({
            "id": ev.id,
            "type": ev.type,
            "original_filename": ev.original_filename,
            "sha256": ev.sha256,
            "size_bytes": ev.size_bytes,
            "uploaded_at": ev.uploaded_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "source_timestamp": ev.source_timestamp.strftime("%Y-%m-%d %H:%M:%S") if ev.source_timestamp else "N/A",
            "timestamp_source": ev.timestamp_source,
            "analysis_status": ev.analysis_status,
        })

    # 6. Correlation Edge Details
    edge_details = []
    for edge in edges:
        edge_details.append({
            "source": edge.source_evidence_id,
            "target": edge.target_evidence_id,
            "link_type": edge.link_type,
            "confidence": edge.confidence,
            "reason": edge.reason,
            "rule_version": edge.rule_version,
        })

    # 7. Analyzer Details
    analysis_details = []
    for an in analyses:
        import json
        try:
            factors = json.loads(an.top_factors)
        except Exception:
            factors = []
        analysis_details.append({
            "evidence_id": an.evidence_id,
            "model_name": an.model_name,
            "model_version": an.model_version,
            "label": an.label,
            "score": an.score,
            "top_factors": factors,
        })

    report = {
        "case_header": {
            "case_id": case.id,
            "title": case.title,
            "description": case.description or "",
            "status": case.status,
            "created_at": case.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "notes": case.notes or "",
        },
        "case_summary_claims": claims,
        "evidence_inventory": inventory,
        "timeline": timeline_data["timeline"],
        "has_conflicts": timeline_data["has_conflicts"],
        "conflicts": timeline_data["conflicts"],
        "correlation_edges": edge_details,
        "risk_assessment": risk_data,
        "analyses": analysis_details,
        "integrity_verification": integrity_data,
        "limitations": [
            "This report is generated as an investigative decision-support aid and does not constitute definitive legal proof.",
            "URL analysis is purely lexical and conducted offline without active DNS or HTTP resolution.",
            "Android APK analysis is static and examines manifest metadata only without dynamic execution.",
            "Screenshot analysis is cryptographic and metadata-only without optical character recognition.",
            "Case risk scores represent heuristic triage rankings and are not calibrated to posterior probabilities of guilt.",
        ],
        "footer": {
            "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "tool_name": "SCAMTRACE AI",
            "tool_version": "0.1.0",
        },
    }
    return report


def render_html_report(report_data: Dict[str, Any]) -> str:
    """Render the structured report dictionary into standalone HTML using Jinja2."""
    template = jinja_env.get_template("report.html.j2")
    return template.render(report=report_data)

