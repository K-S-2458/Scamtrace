"""Acceptance tests for Phase 1: Case and evidence ingestion with hashing."""
import hashlib
import os
import stat
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import init_db
from backend.app.ingestion.storage import compute_sha256, store_evidence_file, detect_evidence_type

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()


def test_sha256_computation_and_consistency():
    """Acceptance test: uploading/hashing the same content yields identical SHA-256."""
    content = b"Alert: Your bank account will be blocked today. Click http://example.test/kyc"
    hash1 = compute_sha256(content)
    hash2 = compute_sha256(content)

    assert hash1 == hash2
    assert hash1 == hashlib.sha256(content).hexdigest()
    assert len(hash1) == 64


def test_store_evidence_file_read_only_and_duplicate_rejection(tmp_path, monkeypatch):
    """Acceptance test: second write to same path is rejected and file permissions are read-only."""
    import backend.app.ingestion.storage as storage_mod
    monkeypatch.setattr(storage_mod, "CASES_DIR", tmp_path)

    case_id = "TEST-CASE-001"
    evidence_id = "E1"
    content = b"Sample malicious evidence content"

    path, sha, size = store_evidence_file(case_id, evidence_id, content, "txt")
    assert Path(path).exists()
    assert sha == hashlib.sha256(content).hexdigest()
    assert size == len(content)

    # 1. Verify read-only permissions
    # In Windows/POSIX, writing to read-only file raises PermissionError
    with pytest.raises(PermissionError):
        with open(path, "wb") as f:
            f.write(b"Tamper attempt")

    # 2. Verify duplicate write to same evidence path is rejected
    with pytest.raises(FileExistsError):
        store_evidence_file(case_id, evidence_id, b"New content", "txt")


def test_pasted_text_hashed_as_utf8():
    """Acceptance test: pasted text is hashed strictly as UTF-8 bytes."""
    unicode_text = "KYC update required immediately: ₹50,000 refund pending! Call +91 99999 00001."
    expected_hash = hashlib.sha256(unicode_text.encode("utf-8")).hexdigest()

    # Create case
    case_res = client.post("/api/cases", json={"title": "Unicode Text Ingestion Test"})
    assert case_res.status_code == 201
    case_id = case_res.json()["id"]

    # Ingest pasted text via JSON
    evidence_res = client.post(
        f"/api/cases/{case_id}/evidence",
        json={"text": unicode_text, "type": "sms", "uploader": "officer1"}
    )
    assert evidence_res.status_code == 201
    ev_data = evidence_res.json()

    assert ev_data["sha256"] == expected_hash
    assert ev_data["type"] == "sms"
    assert ev_data["raw_text"] == unicode_text
    assert ev_data["size_bytes"] == len(unicode_text.encode("utf-8"))


def test_case_lifecycle_endpoints():
    """Test full case CRUD lifecycle: create, list, get, update, notes, close."""
    # 1. Create
    c_res = client.post("/api/cases", json={"title": "Test Phishing Campaign", "description": "Test"})
    assert c_res.status_code == 201
    case_id = c_res.json()["id"]

    # 2. Get
    get_res = client.get(f"/api/cases/{case_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Test Phishing Campaign"
    assert get_res.json()["status"] == "open"

    # 3. Update
    patch_res = client.patch(f"/api/cases/{case_id}", json={"description": "Updated description"})
    assert patch_res.status_code == 200
    assert patch_res.json()["description"] == "Updated description"

    # 4. Add notes
    notes_res = client.post(f"/api/cases/{case_id}/notes", json={"note": "Initial investigator finding"})
    assert notes_res.status_code == 200
    assert "Initial investigator finding" in notes_res.json()["notes"]

    # 5. Close
    close_res = client.post(f"/api/cases/{case_id}/close")
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "closed"

    # 6. Audit log entries exist
    audit_res = client.get(f"/api/cases/{case_id}/audit")
    assert audit_res.status_code == 200
    entries = audit_res.json()
    assert len(entries) >= 4  # create, update, edit_note, close
    actions = [e["action"] for e in entries]
    assert "create_case" in actions
    assert "edit_note" in actions
    assert "close_case" in actions


def test_multipart_file_upload_and_type_conflict():
    """Test multipart upload, type detection, and user/detected type conflict recording."""
    case_res = client.post("/api/cases", json={"title": "File Upload Test"})
    case_id = case_res.json()["id"]

    # Upload an image file while claiming it's an 'sms' to trigger conflict detection
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20
    files = {"file": ("screenshot.png", fake_png, "image/png")}
    data = {"type": "sms"}  # Conflict!

    res = client.post(f"/api/cases/{case_id}/evidence", files=files, data=data)
    assert res.status_code == 201
    ev = res.json()
    assert ev["type"] == "sms"
    assert ev["type_conflict"] is not None
    assert "detected 'screenshot'" in ev["type_conflict"]
    assert ev["sha256"] == hashlib.sha256(fake_png).hexdigest()


def test_bulk_csv_ingestion():
    """Test bulk ingestion from CSV content."""
    case_res = client.post("/api/cases", json={"title": "Bulk Ingestion Test"})
    case_id = case_res.json()["id"]

    csv_data = (
        "text,timestamp,type\n"
        "Your account is blocked call 9999900001,2026-03-10 10:00:00,sms\n"
        "Claim your prize at https://win.example.test,10/03/2026 10:05,url\n"
    )

    files = {"file": ("messages.csv", csv_data.encode("utf-8"), "text/csv")}
    res = client.post(f"/api/cases/{case_id}/evidence/bulk", files=files)
    assert res.status_code == 201
    items = res.json()
    assert len(items) == 2
    assert items[0]["id"] == "E1"
    assert items[1]["id"] == "E2"
    assert items[0]["timestamp_source"] == "user_entered"
    assert items[0]["source_timestamp"] is not None

