"""Correlation engine for SCAMTRACE AI.
Executes all configured correlation rules, deduplicates edges,
and provides per-rule ablation toggles.
"""
import json
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.config import CORRELATION_RULE_SWITCHES
from backend.app.correlation.rules import (
    EdgeProposal,
    rule_apk_lure_pattern,
    rule_redirect_chain,
    rule_same_brand_impersonation,
    rule_same_cert_hash,
    rule_same_upi_handle,
    rule_shared_domain,
    rule_shared_phone,
    rule_similar_text_template,
    rule_temporal_proximity,
    rule_url_host_match,
)
from backend.app.db.models import Edge, Entity, Evidence
from backend.app.extraction.entities import (
    extract_entities_from_apk,
    extract_entities_from_text,
)
from backend.app.integrity.audit_log import record_audit_entry


def correlate_case(
    db: Session,
    case_id: str,
    rule_switches: Optional[Dict[str, bool]] = None,
    redirect_mappings: Optional[Dict[str, str]] = None,
    persist: bool = True,
) -> List[EdgeProposal]:
    """Execute all correlation rules over case evidence and entities.

    Returns:
        List of deduplicated EdgeProposal objects.
    """
    switches = dict(CORRELATION_RULE_SWITCHES)
    if rule_switches:
        switches.update(rule_switches)

    evidence_records = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.id)
        .all()
    )

    # Load or extract entities for each evidence item
    entities_by_ev: Dict[str, List[Any]] = {}

    for ev in evidence_records:
        existing_ents = (
            db.query(Entity)
            .filter(Entity.case_id == case_id, Entity.evidence_id == ev.id)
            .all()
        )
        if existing_ents:
            entities_by_ev[ev.id] = existing_ents
        else:
            # Extract and persist on the fly if not extracted yet
            new_ents = []
            if ev.type in {"sms", "chat", "url", "email_text"} and ev.raw_text:
                new_ents = extract_entities_from_text(ev.raw_text)
            elif ev.type == "apk" and ev.raw_text:
                try:
                    meta = json.loads(ev.raw_text)
                    new_ents = extract_entities_from_apk(meta)
                except Exception:
                    pass

            db_ents = []
            for e in new_ents:
                db_ent = Entity(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    evidence_id=ev.id,
                    entity_type=e.entity_type,
                    value=e.value,
                    raw_value=e.raw_value,
                    span_start=e.span_start,
                    span_end=e.span_end,
                )
                db.add(db_ent)
                db_ents.append(db_ent)

            if db_ents and persist:
                db.commit()
            entities_by_ev[ev.id] = db_ents

    # Collect proposals from all pure rule functions
    all_proposals: List[EdgeProposal] = []
    all_proposals.extend(rule_shared_phone(evidence_records, entities_by_ev, switches))
    all_proposals.extend(rule_shared_domain(evidence_records, entities_by_ev, switches))
    all_proposals.extend(rule_url_host_match(evidence_records, entities_by_ev, switches))
    all_proposals.extend(rule_redirect_chain(evidence_records, entities_by_ev, redirect_mappings, switches))
    all_proposals.extend(rule_similar_text_template(evidence_records, entities_by_ev, switches))
    all_proposals.extend(rule_same_brand_impersonation(evidence_records, entities_by_ev, switches))
    all_proposals.extend(rule_apk_lure_pattern(evidence_records, entities_by_ev, switches))
    all_proposals.extend(rule_same_cert_hash(evidence_records, entities_by_ev, switches))
    all_proposals.extend(rule_same_upi_handle(evidence_records, entities_by_ev, switches))
    all_proposals.extend(rule_temporal_proximity(evidence_records, entities_by_ev, switches))

    # Deduplicate proposals by (source, target, link_type)
    deduped_proposals: List[EdgeProposal] = []
    seen = set()
    for prop in all_proposals:
        # Ignore self-loops
        if prop.source_evidence_id == prop.target_evidence_id:
            continue
        key = (prop.source_evidence_id, prop.target_evidence_id, prop.link_type)
        if key not in seen:
            seen.add(key)
            deduped_proposals.append(prop)

    # Persist in DB if requested
    if persist:
        # Delete existing edges for this case to refresh
        db.query(Edge).filter(Edge.case_id == case_id).delete()

        for prop in deduped_proposals:
            edge_record = Edge(
                id=str(uuid.uuid4()),
                case_id=case_id,
                source_evidence_id=prop.source_evidence_id,
                target_evidence_id=prop.target_evidence_id,
                link_type=prop.link_type,
                confidence=prop.confidence,
                reason=prop.reason,
                supporting_fields=json.dumps(prop.supporting_fields),
                rule_version=prop.rule_version,
            )
            db.add(edge_record)

        db.commit()

        # Record audit log
        record_audit_entry(
            db=db,
            case_id=case_id,
            action="correlate",
            payload={
                "edges_created": len(deduped_proposals),
                "link_types": list({p.link_type for p in deduped_proposals}),
            },
            actor="investigator",
        )

    return deduped_proposals

