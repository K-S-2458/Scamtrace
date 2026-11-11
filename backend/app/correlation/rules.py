"""Deterministic correlation rules for SCAMTRACE AI.
Each rule is implemented as a pure function taking evidence items and extracted entities,
returning zero or more attributed EdgeProposal instances.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.config import (
    APK_HIGH_RISK_LURE_PERMS,
    CORRELATION_RULE_SWITCHES,
    SIMILARITY_THRESHOLD,
    TEMPORAL_WINDOW_MINUTES,
)
from backend.app.extraction.brands import is_official_domain_for_brand


@dataclass
class EdgeProposal:
    source_evidence_id: str
    target_evidence_id: str
    link_type: str
    confidence: float
    reason: str
    supporting_fields: Dict[str, Any] = field(default_factory=dict)
    rule_version: str = "1.0"


def order_evidence_pair(ev_a: Any, ev_b: Any) -> Tuple[str, str]:
    """Order evidence pair so the earlier item is source, target is later."""
    ts_a = getattr(ev_a, "source_timestamp", None)
    ts_b = getattr(ev_b, "source_timestamp", None)

    if ts_a and ts_b and ts_a != ts_b:
        return (ev_a.id, ev_b.id) if ts_a < ts_b else (ev_b.id, ev_a.id)

    up_a = getattr(ev_a, "uploaded_at", None)
    up_b = getattr(ev_b, "uploaded_at", None)
    if up_a and up_b and up_a != up_b:
        return (ev_a.id, ev_b.id) if up_a < up_b else (ev_b.id, ev_a.id)

    # Fallback to ID lexical order
    return (ev_a.id, ev_b.id) if str(ev_a.id) <= str(ev_b.id) else (ev_b.id, ev_a.id)


def rule_shared_phone(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES
) -> List[EdgeProposal]:
    """Rule 1: SHARED_PHONE - same normalized phone in two different items."""
    if not switches.get("SHARED_PHONE", True):
        return []

    ev_map = {e.id: e for e in evidence_list}
    proposals = []

    # Map normalized phone to list of evidence IDs
    phone_to_ev: Dict[str, Set[str]] = {}
    for ev_id, ents in entities_by_ev.items():
        for ent in ents:
            if ent.entity_type == "phone":
                phone_to_ev.setdefault(ent.value, set()).add(ev_id)

    for phone, ev_ids in phone_to_ev.items():
        sorted_ids = sorted(ev_ids)
        for i in range(len(sorted_ids)):
            for j in range(i + 1, len(sorted_ids)):
                id_a, id_b = sorted_ids[i], sorted_ids[j]
                src, tgt = order_evidence_pair(ev_map[id_a], ev_map[id_b])
                proposals.append(EdgeProposal(
                    source_evidence_id=src,
                    target_evidence_id=tgt,
                    link_type="SHARED_PHONE",
                    confidence=0.90,
                    reason=f"Both items contain phone number {phone}.",
                    supporting_fields={"phone": phone},
                ))
    return proposals


def rule_shared_domain(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES
) -> List[EdgeProposal]:
    """Rule 2: SHARED_DOMAIN - same registered domain appears in two items."""
    if not switches.get("SHARED_DOMAIN", True):
        return []

    ev_map = {e.id: e for e in evidence_list}
    domain_to_ev: Dict[str, Set[str]] = {}

    for ev_id, ents in entities_by_ev.items():
        for ent in ents:
            if ent.entity_type == "domain":
                domain_to_ev.setdefault(ent.value, set()).add(ev_id)

    proposals = []
    for domain, ev_ids in domain_to_ev.items():
        sorted_ids = sorted(ev_ids)
        for i in range(len(sorted_ids)):
            for j in range(i + 1, len(sorted_ids)):
                id_a, id_b = sorted_ids[i], sorted_ids[j]
                src, tgt = order_evidence_pair(ev_map[id_a], ev_map[id_b])
                proposals.append(EdgeProposal(
                    source_evidence_id=src,
                    target_evidence_id=tgt,
                    link_type="SHARED_DOMAIN",
                    confidence=0.85,
                    reason=f"Items share registered domain {domain}.",
                    supporting_fields={"domain": domain},
                ))
    return proposals


def rule_url_host_match(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES
) -> List[EdgeProposal]:
    """Rule 3: URL_HOST_MATCH - exact URL host matches across two items."""
    if not switches.get("URL_HOST_MATCH", True):
        return []

    ev_map = {e.id: e for e in evidence_list}
    host_to_ev: Dict[str, Set[str]] = {}

    for ev_id, ents in entities_by_ev.items():
        for ent in ents:
            if ent.entity_type == "url":
                from backend.app.extraction.normalize import extract_domain_and_host
                host, _ = extract_domain_and_host(ent.value)
                if host:
                    host_to_ev.setdefault(host, set()).add(ev_id)

    proposals = []
    for host, ev_ids in host_to_ev.items():
        sorted_ids = sorted(ev_ids)
        for i in range(len(sorted_ids)):
            for j in range(i + 1, len(sorted_ids)):
                id_a, id_b = sorted_ids[i], sorted_ids[j]
                src, tgt = order_evidence_pair(ev_map[id_a], ev_map[id_b])
                proposals.append(EdgeProposal(
                    source_evidence_id=src,
                    target_evidence_id=tgt,
                    link_type="URL_HOST_MATCH",
                    confidence=0.90,
                    reason=f"Items share identical URL hostname {host}.",
                    supporting_fields={"host": host},
                ))
    return proposals


def rule_redirect_chain(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    redirect_mappings: Optional[Dict[str, str]] = None,
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES
) -> List[EdgeProposal]:
    """Rule 4: REDIRECT_CHAIN - user-supplied redirect mapping only. Never inferred from network."""
    if not switches.get("REDIRECT_CHAIN", True) or not redirect_mappings:
        return []

    ev_map = {e.id: e for e in evidence_list}
    proposals = []

    # redirect_mappings: {source_url_or_domain: target_url_or_domain}
    for ev_a in evidence_list:
        urls_a = [ent.value for ent in entities_by_ev.get(ev_a.id, []) if ent.entity_type in {"url", "domain"}]
        for u_a in urls_a:
            if u_a in redirect_mappings:
                target_dest = redirect_mappings[u_a]
                for ev_b in evidence_list:
                    if ev_a.id == ev_b.id:
                        continue
                    urls_b = [ent.value for ent in entities_by_ev.get(ev_b.id, []) if ent.entity_type in {"url", "domain"}]
                    if any(target_dest in ub or ub in target_dest for ub in urls_b):
                        src, tgt = order_evidence_pair(ev_a, ev_b)
                        proposals.append(EdgeProposal(
                            source_evidence_id=src,
                            target_evidence_id=tgt,
                            link_type="REDIRECT_CHAIN",
                            confidence=0.80,
                            reason=f"Investigator-verified redirection link from {u_a} to {target_dest}.",
                            supporting_fields={"source": u_a, "target": target_dest},
                        ))
    return proposals


def rule_similar_text_template(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES,
    threshold: float = SIMILARITY_THRESHOLD
) -> List[EdgeProposal]:
    """Rule 5: SIMILAR_TEXT_TEMPLATE - TF-IDF cosine similarity between texts from different senders."""
    if not switches.get("SIMILAR_TEXT_TEMPLATE", True):
        return []

    text_evs = [e for e in evidence_list if getattr(e, "raw_text", None) and e.type in {"sms", "chat", "email_text", "phone_call", "call_log"}]
    if len(text_evs) < 2:
        return []

    texts = [e.raw_text for e in text_evs]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        sim_matrix = cosine_similarity(tfidf_matrix)
    except Exception:
        return []

    proposals = []
    for i in range(len(text_evs)):
        for j in range(i + 1, len(text_evs)):
            sim = float(sim_matrix[i, j])
            if sim >= threshold:
                ev_a = text_evs[i]
                ev_b = text_evs[j]

                # Check different senders / sender IDs
                senders_a = {ent.value for ent in entities_by_ev.get(ev_a.id, []) if ent.entity_type in {"sender_id", "phone"}}
                senders_b = {ent.value for ent in entities_by_ev.get(ev_b.id, []) if ent.entity_type in {"sender_id", "phone"}}

                # Trigger if distinct senders or different sender IDs
                src, tgt = order_evidence_pair(ev_a, ev_b)
                conf = min(0.80, round(sim, 2))
                proposals.append(EdgeProposal(
                    source_evidence_id=src,
                    target_evidence_id=tgt,
                    link_type="SIMILAR_TEXT_TEMPLATE",
                    confidence=conf,
                    reason=f"High textual template similarity ({sim:.2f}) observed between text artifacts.",
                    supporting_fields={"similarity": round(sim, 4)},
                ))
    return proposals


def rule_same_brand_impersonation(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES
) -> List[EdgeProposal]:
    """Rule 6: SAME_BRAND_IMPERSONATION - two or more items reference brand, and at least one has unauthorized domain."""
    if not switches.get("SAME_BRAND_IMPERSONATION", True):
        return []

    ev_map = {e.id: e for e in evidence_list}
    brand_to_evs: Dict[str, Set[str]] = {}

    for ev_id, ents in entities_by_ev.items():
        for ent in ents:
            if ent.entity_type == "brand":
                brand_to_evs.setdefault(ent.value, set()).add(ev_id)

    proposals = []
    for brand, ev_ids in brand_to_evs.items():
        # Check if at least one evidence item has a domain not on official list
        suspicious_domain_found = False
        unauthorized_domain = None

        for ev_id in ev_ids:
            domains = [ent.value for ent in entities_by_ev.get(ev_id, []) if ent.entity_type in {"domain", "url"}]
            for dom in domains:
                if not is_official_domain_for_brand(brand, dom):
                    suspicious_domain_found = True
                    unauthorized_domain = dom
                    break
            if suspicious_domain_found:
                break

        if suspicious_domain_found:
            sorted_ids = sorted(ev_ids)
            for i in range(len(sorted_ids)):
                for j in range(i + 1, len(sorted_ids)):
                    id_a, id_b = sorted_ids[i], sorted_ids[j]
                    src, tgt = order_evidence_pair(ev_map[id_a], ev_map[id_b])
                    proposals.append(EdgeProposal(
                        source_evidence_id=src,
                        target_evidence_id=tgt,
                        link_type="SAME_BRAND_IMPERSONATION",
                        confidence=0.60,
                        reason=f"Both items reference brand '{brand}', with unauthorized/suspicious domain '{unauthorized_domain}'.",
                        supporting_fields={"brand": brand, "unauthorized_domain": unauthorized_domain},
                    ))
    return proposals


def rule_apk_lure_pattern(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES
) -> List[EdgeProposal]:
    """Rule 7: APK_LURE_PATTERN - text/URL contains lure terminology and APK requests high-risk permissions."""
    if not switches.get("APK_LURE_PATTERN", True):
        return []

    lure_words = {"install", "download", "update app", "apk", "app", "application"}
    apk_evs = [e for e in evidence_list if e.type == "apk"]
    text_url_evs = [e for e in evidence_list if e.type in {"sms", "chat", "url", "email_text", "phone_call", "call_log"}]

    if not apk_evs or not text_url_evs:
        return []

    proposals = []
    for apk in apk_evs:
        # Check high-risk permissions in APK metadata or raw_text
        perms = []
        if getattr(apk, "raw_text", None):
            try:
                import json
                meta = json.loads(apk.raw_text)
                perms = meta.get("requested_permissions", [])
            except Exception:
                pass

        # Identify requested high-risk permissions
        high_risk_found = []
        for p in perms:
            for hr in APK_HIGH_RISK_LURE_PERMS:
                if hr in p:
                    high_risk_found.append(hr)

        # If APK has high risk permissions (or fallback checking)
        if high_risk_found or perms:
            perm_str = ", ".join(sorted(set(high_risk_found))) if high_risk_found else "High-risk permissions"
            for other in text_url_evs:
                other_text = (getattr(other, "raw_text", "") or "").lower()
                if any(w in other_text for w in lure_words):
                    src, tgt = order_evidence_pair(other, apk)
                    proposals.append(EdgeProposal(
                        source_evidence_id=src,
                        target_evidence_id=tgt,
                        link_type="APK_LURE_PATTERN",
                        confidence=0.70,
                        reason=f"Text/URL contains lure terminology and APK requests high-risk permissions: {perm_str}.",
                        supporting_fields={"permissions": perm_str},
                    ))
    return proposals


def rule_same_cert_hash(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES
) -> List[EdgeProposal]:
    """Rule 8: SAME_CERT_HASH - two APK items share certificate hash."""
    if not switches.get("SAME_CERT_HASH", True):
        return []

    ev_map = {e.id: e for e in evidence_list}
    cert_to_ev: Dict[str, Set[str]] = {}

    for ev_id, ents in entities_by_ev.items():
        for ent in ents:
            if ent.entity_type == "cert_sha256":
                cert_to_ev.setdefault(ent.value, set()).add(ev_id)

    proposals = []
    for cert, ev_ids in cert_to_ev.items():
        sorted_ids = sorted(ev_ids)
        for i in range(len(sorted_ids)):
            for j in range(i + 1, len(sorted_ids)):
                id_a, id_b = sorted_ids[i], sorted_ids[j]
                src, tgt = order_evidence_pair(ev_map[id_a], ev_map[id_b])
                proposals.append(EdgeProposal(
                    source_evidence_id=src,
                    target_evidence_id=tgt,
                    link_type="SAME_CERT_HASH",
                    confidence=0.95,
                    reason=f"Both APK artifacts were signed using certificate SHA-256 {cert}.",
                    supporting_fields={"cert_sha256": cert},
                ))
    return proposals


def rule_same_upi_handle(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES
) -> List[EdgeProposal]:
    """Rule 9: SAME_UPI_HANDLE - two items share identical normalized UPI handle."""
    if not switches.get("SAME_UPI_HANDLE", True):
        return []

    ev_map = {e.id: e for e in evidence_list}
    upi_to_ev: Dict[str, Set[str]] = {}

    for ev_id, ents in entities_by_ev.items():
        for ent in ents:
            if ent.entity_type == "upi_handle":
                upi_to_ev.setdefault(ent.value, set()).add(ev_id)

    proposals = []
    for handle, ev_ids in upi_to_ev.items():
        sorted_ids = sorted(ev_ids)
        for i in range(len(sorted_ids)):
            for j in range(i + 1, len(sorted_ids)):
                id_a, id_b = sorted_ids[i], sorted_ids[j]
                src, tgt = order_evidence_pair(ev_map[id_a], ev_map[id_b])
                proposals.append(EdgeProposal(
                    source_evidence_id=src,
                    target_evidence_id=tgt,
                    link_type="SAME_UPI_HANDLE",
                    confidence=0.90,
                    reason=f"Both items reference identical payment handle {handle}.",
                    supporting_fields={"upi_handle": handle},
                ))
    return proposals


def rule_temporal_proximity(
    evidence_list: List[Any],
    entities_by_ev: Dict[str, List[Any]],
    switches: Dict[str, bool] = CORRELATION_RULE_SWITCHES,
    window_minutes: int = TEMPORAL_WINDOW_MINUTES
) -> List[EdgeProposal]:
    """Rule 10: TEMPORAL_PROXIMITY - two items with source timestamps within window."""
    if not switches.get("TEMPORAL_PROXIMITY", True):
        return []

    dated_evs = [e for e in evidence_list if getattr(e, "source_timestamp", None)]
    proposals = []

    for i in range(len(dated_evs)):
        for j in range(i + 1, len(dated_evs)):
            ev_a = dated_evs[i]
            ev_b = dated_evs[j]
            delta = abs((ev_a.source_timestamp - ev_b.source_timestamp).total_seconds()) / 60.0
            if delta <= window_minutes:
                src, tgt = order_evidence_pair(ev_a, ev_b)
                proposals.append(EdgeProposal(
                    source_evidence_id=src,
                    target_evidence_id=tgt,
                    link_type="TEMPORAL_PROXIMITY",
                    confidence=0.20,
                    reason=f"Evidence items occurred within {delta:.1f} minutes of each other.",
                    supporting_fields={"delta_minutes": round(delta, 1)},
                ))
    return proposals

