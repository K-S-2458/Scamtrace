"""Incident timeline reconstruction and conflict detection for SCAMTRACE AI."""
import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.config import ORDERING_TOLERANCE_MINUTES
from backend.app.db.models import Edge, Evidence


def format_time_gap(seconds: float) -> str:
    """Format seconds into a human-readable duration."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = seconds / 60.0
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = minutes / 60.0
    if hours < 24:
        return f"{hours:.1f}h"
    days = hours / 24.0
    return f"{days:.1f}d"


def build_evidence_summary(ev: Evidence) -> str:
    """Generate a concise one-line forensic summary of an evidence item."""
    if ev.type == "url":
        url = ev.raw_text or ev.original_filename or ""
        return f"Access to URL endpoint: {url[:60]}"
    elif ev.type == "apk":
        pkg = "Android APK package"
        if ev.raw_text and "package_name" in ev.raw_text:
            try:
                import json
                meta = json.loads(ev.raw_text)
                pkg = f"APK package '{meta.get('package_name', '')}'"
            except Exception:
                pass
        return f"Static analysis of {pkg}"
    elif ev.type in {"sms", "chat", "email_text"}:
        txt = (ev.raw_text or "").replace("\n", " ").strip()
        preview = txt[:70] + "..." if len(txt) > 70 else txt
        return f"{ev.type.upper()}: \"{preview}\""
    elif ev.type == "screenshot":
        return f"Screenshot capture: {ev.original_filename} ({ev.size_bytes} bytes)"
    return f"Artifact {ev.id} ({ev.type})"


def build_case_timeline(db: Session, case_id: str) -> Dict[str, Any]:
    """Reconstruct chronological timeline, compute gaps, and flag ordering conflicts."""
    all_evidence = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .all()
    )

    dated_items = [e for e in all_evidence if e.source_timestamp is not None]
    undated_items = [e for e in all_evidence if e.source_timestamp is None]

    # Sort dated items by source_timestamp ascending, then uploaded_at
    dated_items.sort(key=lambda x: (x.source_timestamp, x.uploaded_at))
    # Sort undated items by uploaded_at ascending
    undated_items.sort(key=lambda x: x.uploaded_at)

    ordered_evidence = dated_items + undated_items

    # 1. Conflict Detection across correlation edges
    edges = db.query(Edge).filter(Edge.case_id == case_id).all()
    ev_map = {e.id: e for e in all_evidence}
    all_conflicts: List[Dict[str, Any]] = []
    item_conflicts: Dict[str, List[str]] = {e.id: [] for e in all_evidence}

    for edge in edges:
        if edge.link_type == "APK_LURE_PATTERN":
            src = ev_map.get(edge.source_evidence_id)
            tgt = ev_map.get(edge.target_evidence_id)
            if src and tgt:
                # Identify which is lure and which is APK
                lure = src if src.type in {"sms", "chat", "url", "email_text"} else (tgt if tgt.type in {"sms", "chat", "url", "email_text"} else None)
                apk = tgt if tgt.type == "apk" else (src if src.type == "apk" else None)

                if lure and apk and lure.source_timestamp and apk.source_timestamp:
                    tolerance_sec = ORDERING_TOLERANCE_MINUTES * 60
                    # If APK occurred before Lure by more than tolerance
                    if (lure.source_timestamp - apk.source_timestamp).total_seconds() > tolerance_sec:
                        msg = (
                            f"Ordering Conflict: APK artifact {apk.id} ({apk.source_timestamp.strftime('%Y-%m-%d %H:%M:%S')}) "
                            f"precedes lure item {lure.id} ({lure.source_timestamp.strftime('%Y-%m-%d %H:%M:%S')}) "
                            f"by more than {ORDERING_TOLERANCE_MINUTES} minutes."
                        )
                        conflict_entry = {
                            "type": "CAUSAL_ORDERING_CONFLICT",
                            "evidence_a": apk.id,
                            "evidence_b": lure.id,
                            "description": msg,
                        }
                        all_conflicts.append(conflict_entry)
                        item_conflicts[apk.id].append(msg)
                        item_conflicts[lure.id].append(msg)

    # 2. Build Timeline items with time gaps
    timeline_items = []
    prev_dt: Optional[datetime.datetime] = None

    for ev in ordered_evidence:
        is_uncertain = ev.source_timestamp is None
        current_dt = ev.source_timestamp if not is_uncertain else ev.uploaded_at

        gap_str = None
        gap_sec = None
        if prev_dt and not is_uncertain:
            gap_sec = (current_dt - prev_dt).total_seconds()
            gap_str = format_time_gap(gap_sec)

        if not is_uncertain:
            prev_dt = current_dt

        timeline_items.append({
            "evidence_id": ev.id,
            "type": ev.type,
            "original_filename": ev.original_filename,
            "timestamp": current_dt.strftime("%Y-%m-%d %H:%M:%S") if current_dt else None,
            "source_timestamp": ev.source_timestamp.strftime("%Y-%m-%d %H:%M:%S") if ev.source_timestamp else None,
            "timestamp_source": ev.timestamp_source,
            "time_uncertain": is_uncertain,
            "time_gap_from_prev": gap_str,
            "time_gap_seconds": gap_sec,
            "summary": build_evidence_summary(ev),
            "conflicts": item_conflicts.get(ev.id, []),
        })

    return {
        "case_id": case_id,
        "total_items": len(timeline_items),
        "has_conflicts": len(all_conflicts) > 0,
        "conflicts": all_conflicts,
        "timeline": timeline_items,
    }

