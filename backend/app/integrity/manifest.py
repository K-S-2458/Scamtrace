"""Case manifest management for SCAMTRACE AI.
Provides generation, storage, and hash computation for case manifests.
"""
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.config import CASES_DIR
from backend.app.db.models import Evidence


def get_manifest_path(case_id: str) -> Path:
    """Return the filesystem path to a case's manifest.json."""
    return CASES_DIR / case_id / "manifest.json"


def canonical_json(data: Any) -> str:
    """Serialize data into a deterministic canonical JSON string."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def compute_manifest_hash(evidence_list: List[Dict[str, Any]]) -> str:
    """Compute deterministic SHA-256 over the canonical JSON of evidence entries."""
    # Ensure evidence is sorted by ID
    sorted_evidence = sorted(evidence_list, key=lambda x: str(x.get("id", "")))
    canon_bytes = canonical_json(sorted_evidence).encode("utf-8")
    return hashlib.sha256(canon_bytes).hexdigest()


def generate_manifest(case_id: str, db: Session) -> Dict[str, Any]:
    """Generate or regenerate manifest.json for a case from current database evidence.

    Returns:
        Manifest dictionary including evidence items and manifest_hash.
    """
    case_dir = CASES_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = get_manifest_path(case_id)

    # Query all evidence for this case
    evidence_records = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.id)
        .all()
    )

    evidence_list = []
    for item in evidence_records:
        evidence_list.append({
            "id": item.id,
            "type": item.type,
            "sha256": item.sha256,
            "size_bytes": item.size_bytes,
            "original_filename": item.original_filename,
            "stored_path": item.stored_path,
        })

    manifest_hash = compute_manifest_hash(evidence_list)
    manifest_data = {
        "case_id": case_id,
        "evidence_count": len(evidence_list),
        "evidence": evidence_list,
        "manifest_hash": manifest_hash,
    }

    # Write manifest file
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, sort_keys=True)

    return manifest_data


def load_manifest(case_id: str) -> Optional[Dict[str, Any]]:
    """Load manifest.json from disk if present."""
    path = get_manifest_path(case_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
