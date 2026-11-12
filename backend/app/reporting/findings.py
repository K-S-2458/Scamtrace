"""Investigation findings compiler for SCAMTRACE AI.
Compiles identified entities, key findings, and multi-tier conclusions directly
from database evidence records, correlation edges, and verified hashes.
"""
from typing import Any, Dict, List, Set
from sqlalchemy.orm import Session

from backend.app.db.models import Analysis, Case, Edge, Entity, Evidence
from backend.app.integrity.verify import verify_case_integrity
from backend.app.risk.scoring import compute_case_risk


def compile_investigation_findings(db: Session, case_id: str) -> Dict[str, Any]:
    """Deterministically compile identified entities, key findings, and categorized conclusions."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case {case_id} not found")

    evidence_records = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.id)
        .all()
    )
    ev_map = {e.id: e for e in evidence_records}

    entities = db.query(Entity).filter(Entity.case_id == case_id).all()
    edges = (
        db.query(Edge)
        .filter(Edge.case_id == case_id)
        .order_by(Edge.confidence.desc())
        .all()
    )
    analyses = db.query(Analysis).filter(Analysis.case_id == case_id).all()
    risk_data = compute_case_risk(db, case_id)
    integrity_data = verify_case_integrity(db, case_id)

    # 1. Identified Entities Grouping
    entity_groups: Dict[str, Dict[str, Dict[str, Any]]] = {
        "phone_numbers": {},
        "domains": {},
        "upi_handles": {},
        "package_names": {},
        "certificate_hashes": {},
        "brand_names": {},
        "amounts": {},
    }

    type_to_group = {
        "phone": "phone_numbers",
        "domain": "domains",
        "url": "domains",
        "upi_handle": "upi_handles",
        "apk_package": "package_names",
        "cert_sha256": "certificate_hashes",
        "brand": "brand_names",
        "amount": "amounts",
    }

    for ent in entities:
        group_name = type_to_group.get(ent.entity_type)
        if not group_name:
            continue
        val = ent.value
        if val not in entity_groups[group_name]:
            entity_groups[group_name][val] = {
                "value": val,
                "raw_value": ent.raw_value,
                "evidence_ids": set(),
            }
        entity_groups[group_name][val]["evidence_ids"].add(ent.evidence_id)

    categorized_entities = {
        k: [
            {
                "value": item["value"],
                "raw_value": item["raw_value"],
                "evidence_ids": sorted(list(item["evidence_ids"])),
            }
            for item in sorted(v.values(), key=lambda x: x["value"])
        ]
        for k, v in entity_groups.items()
    }

    # 2. Key Findings
    key_findings: List[Dict[str, Any]] = []

    # A. Findings from correlation edges
    for edge in edges:
        conf = edge.confidence or 0.8
        strength = "Strong" if conf >= 0.85 else ("Possible" if conf >= 0.50 else "Weak")

        if edge.link_type == "SHARED_PHONE":
            title = "Cross-Artifact Phone Number Reuse"
        elif edge.link_type == "SHARED_DOMAIN":
            title = "Shared Malicious Domain Infrastructure"
        elif edge.link_type == "SAME_BRAND_IMPERSONATION":
            title = "Multi-Channel Brand Impersonation"
        elif edge.link_type == "APK_LURE_PATTERN":
            title = "Lure-to-App Trojan Dropper Sequence"
        elif edge.link_type == "URL_HOST_MATCH":
            title = "Hyperlink Hostname Match"
        elif edge.link_type == "REDIRECT_CHAIN":
            title = "Identified Traffic Redirection Chain"
        elif edge.link_type == "SIMILAR_TEXT_TEMPLATE":
            title = "Template-Based Lure Similarity"
        else:
            title = edge.link_type.replace("_", " ").title()

        key_findings.append({
            "id": f"finding_edge_{edge.id}",
            "title": title,
            "explanation": edge.reason,
            "evidence_ids": sorted([edge.source_evidence_id, edge.target_evidence_id]),
            "confidence": round(conf, 2),
            "strength": strength,
            "rule_id": edge.link_type,
        })

    # B. Findings from high-threat analyses
    for an in analyses:
        if an.score >= 0.50:
            ev = ev_map.get(an.evidence_id)
            ev_label = f"{ev.id} ({ev.type.upper()})" if ev else an.evidence_id
            key_findings.append({
                "id": f"finding_analysis_{an.id}",
                "title": f"Elevated Threat Detected in {ev_label}",
                "explanation": f"Classifier {an.model_name} evaluated threat score {an.score:.2f} based on suspicious indicators.",
                "evidence_ids": [an.evidence_id],
                "confidence": round(an.score, 2),
                "strength": "High" if an.score >= 0.80 else "Moderate",
                "rule_id": "ANALYZER_SEVERITY",
            })

    # 3. Investigation Conclusion (Categorized into Confirmed, Inferences, Unverified)
    confirmed_obs: List[str] = []
    inferences: List[str] = []
    unverified: List[str] = []

    # Check cryptographic integrity
    if integrity_data.get("is_valid"):
        confirmed_obs.append(
            f"All {len(evidence_records)} ingested evidence artifacts are cryptographically verified with unbroken SHA-256 hashes."
        )
    else:
        confirmed_obs.append("Tampering detected in case evidence files or audit log sequence.")

    # Check shared entities
    for phone_item in categorized_entities["phone_numbers"]:
        if len(phone_item["evidence_ids"]) > 1:
            confirmed_obs.append(
                f"Identical phone number '{phone_item['raw_value']}' is verified across artifacts: {', '.join(phone_item['evidence_ids'])}."
            )

    for domain_item in categorized_entities["domains"]:
        if len(domain_item["evidence_ids"]) > 1:
            confirmed_obs.append(
                f"Common domain '{domain_item['value']}' is referenced across artifacts: {', '.join(domain_item['evidence_ids'])}."
            )

    for pkg_item in categorized_entities["package_names"]:
        confirmed_obs.append(
            f"Android package '{pkg_item['value']}' identified in artifact {', '.join(pkg_item['evidence_ids'])}."
        )

    for amt_item in categorized_entities["amounts"]:
        confirmed_obs.append(
            f"Financial transaction value {amt_item['value']} referenced in artifact {', '.join(amt_item['evidence_ids'])}."
        )

    # Inferences
    brand_items = categorized_entities["brand_names"]
    if brand_items and len(categorized_entities["domains"]) > 0:
        inferences.append(
            f"Threat actors are impersonating brand(s) {', '.join([b['raw_value'] for b in brand_items])} utilizing unauthorized web infrastructure."
        )

    if any(e.link_type == "APK_LURE_PATTERN" for e in edges):
        inferences.append(
            "Attack pattern indicates a coordinated dropper campaign where victims are socially engineered to install credential-intercepting malware."
        )

    raw_risk_score = risk_data.get("final_score", 0.0)
    risk_score_int = int(round(raw_risk_score * 100))
    risk_band = risk_data.get("risk_band", "low")

    if risk_band == "high":
        inferences.append(
            f"Case presents HIGH risk (overall score: {risk_score_int}/100) due to corroboration across multiple communication channels."
        )
    elif risk_band == "medium":
        inferences.append(
            f"Case presents MODERATE risk (score: {risk_score_int}/100) with partial infrastructure corroboration."
        )
    else:
        inferences.append(
            f"Current evidence shows LOW risk triage score ({risk_score_int}/100); indicators remain within baseline parameters."
        )

    # Unverified possibilities
    unverified.append(
        "Perpetrator legal identity and physical geolocation remain unverified without lawful telecommunications carrier records (CDR/IPDR)."
    )
    unverified.append(
        "Direct banking ledger debits cannot be independently confirmed without live core-banking API reconciliation."
    )
    if any(e.link_type == "TEMPORAL_PROXIMITY" for e in edges):
        unverified.append(
            "Artifacts occurring in close temporal succession suggest unified operator intent, but direct infrastructural linkage is not established."
        )

    # Summary Text
    ev_count = len(evidence_records)
    link_count = len(edges)
    summary_text = (
        f"Investigation encompasses {ev_count} evidence item(s) with {link_count} established cross-artifact correlation link(s). "
        f"The incident evaluates to an overall risk score of {risk_score_int}/100 ({risk_band.upper()}). "
        f"{'Corroborating indicators demonstrate multi-stage threat coordination.' if link_count > 0 else 'Evidence exhibits isolated indicators pending further corroboration.'}"
    )

    # Compute additional summary indicators for forensic dashboards
    connected_ids = set()
    for edge in edges:
        if edge.link_type != "CONTAINS_ENTITY":
            connected_ids.add(edge.source_evidence_id)
            connected_ids.add(edge.target_evidence_id)
    connected_artifacts_count = len(connected_ids)

    suspicious_indicators_count = sum(1 for a in analyses if a.score >= 0.4) + len(edges)
    mean_analysis_score = (
        sum(a.score for a in analyses) / len(analyses) if analyses else 0.85
    )
    # Evidence confidence: certitude of the collected evidence & cryptographic verification
    evidence_confidence = round(
        0.5 + 0.5 * (1.0 if integrity_data.get("is_valid") else 0.2) * (mean_analysis_score if analyses else 0.8),
        2,
    )

    return {
        "case_id": case_id,
        "title": case.title,
        "evidence_count": ev_count,
        "connected_artifacts_count": connected_artifacts_count,
        "suspicious_indicators_count": suspicious_indicators_count,
        "evidence_confidence": evidence_confidence,
        "risk_score": risk_score_int,
        "risk_band": risk_band,
        "identified_entities": categorized_entities,
        "key_findings": key_findings,
        "conclusion": {
            "summary": summary_text,
            "confirmed_observations": confirmed_obs,
            "system_inferences": inferences,
            "unverified_possibilities": unverified,
        },
    }
