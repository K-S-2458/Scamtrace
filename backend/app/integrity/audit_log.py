"""Append-only cryptographic audit log for SCAMTRACE AI.
Maintains a verifiable hash chain of all mutating case events.
"""
import datetime
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.db.models import AuditEntry


def canonical_json(data: Any) -> str:
    """Format dictionary/data into deterministic canonical JSON string."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def compute_entry_hash(
    seq: int,
    timestamp_utc: str,
    actor: str,
    action: str,
    payload_json: str,
    prev_hash: str
) -> str:
    """Compute the SHA-256 hash for a chained audit log entry."""
    chain_payload = f"{seq}|{timestamp_utc}|{actor}|{action}|{payload_json}|{prev_hash}"
    return hashlib.sha256(chain_payload.encode("utf-8")).hexdigest()


def get_latest_audit_entry(db: Session, case_id: str) -> Optional[AuditEntry]:
    """Retrieve the most recent audit entry for a case."""
    return (
        db.query(AuditEntry)
        .filter(AuditEntry.case_id == case_id)
        .order_by(AuditEntry.seq.desc())
        .first()
    )


def record_audit_entry(
    db: Session,
    case_id: str,
    action: str,
    payload: Dict[str, Any],
    actor: str = "investigator",
    commit: bool = True
) -> AuditEntry:
    """Append a new cryptographically chained audit entry for a case."""
    latest = get_latest_audit_entry(db, case_id)

    if latest is None:
        seq = 1
        prev_hash = "GENESIS"
    else:
        seq = latest.seq + 1
        prev_hash = latest.entry_hash

    now_utc = datetime.datetime.utcnow()
    # Format timestamp deterministically (ISO without microseconds)
    timestamp_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    canon_payload = canonical_json(payload)
    entry_hash = compute_entry_hash(
        seq=seq,
        timestamp_utc=timestamp_str,
        actor=actor,
        action=action,
        payload_json=canon_payload,
        prev_hash=prev_hash,
    )

    entry = AuditEntry(
        id=str(uuid.uuid4()),
        case_id=case_id,
        seq=seq,
        timestamp_utc=now_utc,
        actor=actor,
        action=action,
        payload_json=canon_payload,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )

    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)

    return entry

