"""Verification and tamper detection module for SCAMTRACE AI.
Verifies stored evidence files, manifest integrity, and cryptographic audit hash chains.
"""
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.config import CASES_DIR
from backend.app.db.models import AuditEntry, Case, Evidence
from backend.app.ingestion.storage import compute_sha256
from backend.app.integrity.audit_log import compute_entry_hash
from backend.app.integrity.manifest import compute_manifest_hash, load_manifest


def verify_case_integrity(db: Session, case_id: str) -> Dict[str, Any]:
    """Perform comprehensive cryptographic verification of a case.

    Checks:
    1. Stored evidence files match recorded SHA-256 and are not missing or altered.
    2. Manifest file exists, recomputes accurately, and has not been tampered with.
    3. Audit log hash chain is unbroken, unedited, without sequence gaps or swaps.

    Returns:
        Structured verification report dictionary.
    """
    tamper_reasons: List[str] = []
    evidence_results: List[Dict[str, Any]] = []

    # 1. Verify Evidence Files
    evidence_records = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.id)
        .all()
    )

    for ev in evidence_records:
        file_path = Path(ev.stored_path)
        if not file_path.exists():
            tamper_reasons.append(f"Evidence file missing: {ev.id} at {file_path}")
            evidence_results.append({
                "evidence_id": ev.id,
                "status": "MISSING",
                "recorded_sha256": ev.sha256,
                "actual_sha256": None,
            })
            continue

        try:
            with open(file_path, "rb") as f:
                actual_bytes = f.read()
            actual_sha = compute_sha256(actual_bytes)
        except Exception as e:
            tamper_reasons.append(f"Cannot read evidence file {ev.id}: {str(e)}")
            evidence_results.append({
                "evidence_id": ev.id,
                "status": "UNREADABLE",
                "recorded_sha256": ev.sha256,
                "actual_sha256": None,
            })
            continue

        if actual_sha != ev.sha256:
            tamper_reasons.append(
                f"Evidence {ev.id} SHA-256 mismatch! Stored: {ev.sha256[:12]}..., Computed: {actual_sha[:12]}..."
            )
            evidence_results.append({
                "evidence_id": ev.id,
                "status": "MISMATCH",
                "recorded_sha256": ev.sha256,
                "actual_sha256": actual_sha,
            })
        else:
            evidence_results.append({
                "evidence_id": ev.id,
                "status": "MATCH",
                "recorded_sha256": ev.sha256,
                "actual_sha256": actual_sha,
            })

    # 2. Verify Manifest
    manifest_data = load_manifest(case_id)
    manifest_status = "MATCH"
    stored_manifest_hash = None
    computed_manifest_hash = None

    if not manifest_data:
        manifest_status = "MISSING"
        tamper_reasons.append(f"Manifest file missing for case {case_id}")
    else:
        stored_manifest_hash = manifest_data.get("manifest_hash")
        # Recompute from evidence_records
        recalc_items = [{
            "id": item.id,
            "type": item.type,
            "sha256": item.sha256,
            "size_bytes": item.size_bytes,
            "original_filename": item.original_filename,
            "stored_path": item.stored_path,
        } for item in evidence_records]
        computed_manifest_hash = compute_manifest_hash(recalc_items)

        if stored_manifest_hash != computed_manifest_hash:
            manifest_status = "MISMATCH"
            tamper_reasons.append(
                f"Manifest hash mismatch: recorded {stored_manifest_hash[:12]}... vs computed {computed_manifest_hash[:12]}..."
            )

    # 3. Verify Cryptographic Audit Chain
    audit_entries = (
        db.query(AuditEntry)
        .filter(AuditEntry.case_id == case_id)
        .order_by(AuditEntry.seq.asc())
        .all()
    )

    audit_status = "VALID"
    audit_details = "Audit chain verified"

    expected_seq = 1
    last_hash = "GENESIS"

    for entry in audit_entries:
        # Check sequence continuity
        if entry.seq != expected_seq:
            audit_status = "TAMPERED"
            reason = f"Audit sequence discontinuity: expected seq {expected_seq}, found seq {entry.seq}"
            tamper_reasons.append(reason)
            audit_details = reason
            break

        # Check prev_hash linking
        if entry.prev_hash != last_hash:
            audit_status = "TAMPERED"
            reason = f"Audit chain break at seq {entry.seq}: prev_hash '{entry.prev_hash[:12]}...' != expected '{last_hash[:12]}...'"
            tamper_reasons.append(reason)
            audit_details = reason
            break

        # Verify entry_hash recomputation
        ts_str = entry.timestamp_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        recomputed_hash = compute_entry_hash(
            seq=entry.seq,
            timestamp_utc=ts_str,
            actor=entry.actor,
            action=entry.action,
            payload_json=entry.payload_json,
            prev_hash=entry.prev_hash,
        )

        if recomputed_hash != entry.entry_hash:
            audit_status = "TAMPERED"
            reason = f"Audit payload tampering at seq {entry.seq}: recorded {entry.entry_hash[:12]}... != recomputed {recomputed_hash[:12]}..."
            tamper_reasons.append(reason)
            audit_details = reason
            break

        last_hash = entry.entry_hash
        expected_seq += 1

    is_valid = len(tamper_reasons) == 0

    return {
        "case_id": case_id,
        "is_valid": is_valid,
        "tamper_detected": not is_valid,
        "tamper_reasons": tamper_reasons,
        "evidence_integrity": evidence_results,
        "manifest_integrity": {
            "status": manifest_status,
            "stored_hash": stored_manifest_hash,
            "computed_hash": computed_manifest_hash,
        },
        "audit_chain_integrity": {
            "status": audit_status,
            "entry_count": len(audit_entries),
            "details": audit_details,
        },
    }

