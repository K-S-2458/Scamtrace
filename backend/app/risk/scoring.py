"""Explainable Factor-based Risk Scoring Engine for SCAMTRACE AI."""
import json
from typing import Any, Dict, List, Set, Tuple
from sqlalchemy.orm import Session

from backend.app.config import (
    ARTIFACT_TYPE_WEIGHTS,
    WEIGHT_ARTIFACT,
    WEIGHT_CORRELATION,
    WEIGHT_PATTERN,
)
from backend.app.db.models import Analysis, Case, Edge, Entity, Evidence


CONFIRMED_LINK_WEIGHTS = {
    "SHARED_PHONE": 0.25,
    "SHARED_DOMAIN": 0.20,
    "URL_HOST_MATCH": 0.20,
    "SAME_BRAND_IMPERSONATION": 0.20,
    "APK_LURE_PATTERN": 0.25,
    "SAME_CERT_HASH": 0.25,
    "SAME_UPI_HANDLE": 0.20,
    "REDIRECT_CHAIN": 0.15,
    "SIMILAR_TEXT_TEMPLATE": 0.15,
}


def compute_case_risk(db: Session, case_id: str) -> Dict[str, Any]:
    """Compute transparent multi-factor risk score for an investigation case.

    Components:
    1. Artifact Component: Threat scores from individual artifact classifiers.
    2. Correlation Component: Confirmed topological graph links (TEMPORAL_PROXIMITY strictly excluded).
    3. Pattern Component: Infrastructure attack campaign signatures (e.g. KYC lure + Privileged APK + Debit).

    Returns:
        Structured risk breakdown where factor contributions sum exactly to final_score.
    """
    evidence_records = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .all()
    )
    if not evidence_records:
        return {
            "case_id": case_id,
            "final_score": 0.0,
            "risk_band": "low",
            "disclaimer": "Investigative triage aid only. Not calibrated to legal guilt.",
            "breakdown": [],
            "components": {"artifact": 0.0, "correlation": 0.0, "pattern": 0.0},
        }

    # 1. Artifact Component
    analyses = (
        db.query(Analysis)
        .filter(Analysis.case_id == case_id)
        .all()
    )

    ev_scores: Dict[str, float] = {}
    for a in analyses:
        ev_scores[a.evidence_id] = max(ev_scores.get(a.evidence_id, 0.0), a.score)

    if ev_scores:
        max_artifact_score = max(ev_scores.values())
        high_risk_ev_ids = [eid for eid, sc in sorted(ev_scores.items()) if sc >= 0.5]
        if not high_risk_ev_ids:
            high_risk_ev_ids = [eid for eid, sc in sorted(ev_scores.items()) if sc == max_artifact_score]
    else:
        max_artifact_score = 0.0
        high_risk_ev_ids = []

    artifact_contrib = round(WEIGHT_ARTIFACT * max_artifact_score, 4)

    # 2. Correlation Component (Strictly excluding TEMPORAL_PROXIMITY)
    edges = db.query(Edge).filter(Edge.case_id == case_id).all()
    confirmed_link_types_found: Dict[str, Set[str]] = {}

    for edge in edges:
        # Exclude TEMPORAL_PROXIMITY from confirmed links
        if edge.link_type == "TEMPORAL_PROXIMITY":
            continue
        if edge.link_type in CONFIRMED_LINK_WEIGHTS:
            confirmed_link_types_found.setdefault(edge.link_type, set()).add(edge.source_evidence_id)
            confirmed_link_types_found[edge.link_type].add(edge.target_evidence_id)

    raw_correlation_sum = sum(
        CONFIRMED_LINK_WEIGHTS[lt] for lt in confirmed_link_types_found.keys()
    )
    correlation_score = min(1.0, raw_correlation_sum)
    correlation_contrib = round(WEIGHT_CORRELATION * correlation_score, 4)

    correlation_ev_ids = sorted(list(set.union(*confirmed_link_types_found.values()))) if confirmed_link_types_found else []

    # 3. Known Scam Pattern Detection
    # Pattern: KYC Phishing Lure URL + Malicious APK + Payment/Debit Activity
    pattern_detected = False
    pattern_ev_ids: List[str] = []
    pattern_reason = "No known composite campaign pattern detected."

    has_lure_url = any("kyc" in (e.raw_text or "").lower() or "verify" in (e.raw_text or "").lower() for e in evidence_records if e.type in {"sms", "chat", "url"})
    has_privileged_apk = any(e.type == "apk" for e in evidence_records)
    has_debit_or_payment = any("debit" in (e.raw_text or "").lower() or "upi" in (e.raw_text or "").lower() or "rs" in (e.raw_text or "").lower() for e in evidence_records)

    if has_lure_url and has_privileged_apk and (has_debit_or_payment or len(confirmed_link_types_found) >= 3):
        pattern_detected = True
        pattern_score = 1.0
        pattern_reason = "Identified Multi-Stage Banking/KYC Impersonation & Trojan Dropper Campaign."
        # Collect involved evidence items
        pattern_ev_ids = sorted(list({e.id for e in evidence_records if e.type in {"sms", "chat", "url", "apk"}}))
    else:
        pattern_score = 0.0

    pattern_contrib = round(WEIGHT_PATTERN * pattern_score, 4)

    # Final Score Calculation
    raw_final = artifact_contrib + correlation_contrib + pattern_contrib
    final_score = min(1.0, max(0.0, round(raw_final, 4)))

    # Risk Band Determination
    if final_score >= 0.70:
        risk_band = "high"
    elif final_score >= 0.35:
        risk_band = "medium"
    else:
        risk_band = "low"

    # Construct Transparent Breakdown Table
    breakdown = [
        {
            "factor_name": "Artifact Threat Severity",
            "factor_type": "artifact",
            "raw_value": round(max_artifact_score, 4),
            "weight": WEIGHT_ARTIFACT,
            "contribution": artifact_contrib,
            "evidence_ids": high_risk_ev_ids,
            "description": f"Maximum classifier probability across ingested artifacts ({max_artifact_score:.2f}).",
        },
        {
            "factor_name": "Corroborated Correlation Infrastructure",
            "factor_type": "correlation",
            "raw_value": round(correlation_score, 4),
            "weight": WEIGHT_CORRELATION,
            "contribution": correlation_contrib,
            "evidence_ids": correlation_ev_ids,
            "description": (
                f"Confirmed links: {', '.join(sorted(confirmed_link_types_found.keys())) or 'None'}. "
                "(TEMPORAL_PROXIMITY excluded from confirmed links count)."
            ),
        },
        {
            "factor_name": "Scam Campaign Pattern Bonus",
            "factor_type": "pattern",
            "raw_value": round(pattern_score, 4),
            "weight": WEIGHT_PATTERN,
            "contribution": pattern_contrib,
            "evidence_ids": pattern_ev_ids,
            "description": pattern_reason,
        },
    ]

    return {
        "case_id": case_id,
        "final_score": final_score,
        "risk_band": risk_band,
        "disclaimer": "SCAMTRACE risk score is an investigative triage aid, not legal proof of guilt, and is not calibrated to posterior probabilities.",
        "breakdown": breakdown,
        "components": {
            "artifact_score": round(max_artifact_score, 4),
            "correlation_score": round(correlation_score, 4),
            "pattern_score": round(pattern_score, 4),
        },
        "confirmed_link_types": sorted(list(confirmed_link_types_found.keys())),
    }

