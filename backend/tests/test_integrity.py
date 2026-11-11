"""Acceptance tests for Phase 2: Integrity layer and tamper detection suite."""
import csv
import os
import stat
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.config import CASES_DIR, ROOT_DIR
from backend.app.db.models import AuditEntry, Case, Evidence
from backend.app.db.session import SessionLocal, init_db
from backend.app.integrity.verify import verify_case_integrity
from backend.app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def create_sample_case_with_evidence():
    """Helper to populate an untouched case with 2 evidence items and audit logs."""
    db = SessionLocal()
    # Create case
    case_res = client.post("/api/cases", json={"title": "Integrity Test Case"})
    assert case_res.status_code == 201
    case_id = case_res.json()["id"]

    # Ingest evidence 1
    ev1_res = client.post(
        f"/api/cases/{case_id}/evidence",
        json={"text": "Evidence item 1: Contact +91 99999 00001", "type": "sms"}
    )
    assert ev1_res.status_code == 201

    # Ingest evidence 2
    ev2_res = client.post(
        f"/api/cases/{case_id}/evidence",
        json={"text": "Evidence item 2: Visit https://kyc.example.test", "type": "url"}
    )
    assert ev2_res.status_code == 201

    db.close()
    return case_id


def test_integrity_untouched_passes():
    """Acceptance test: verification passes on untouched data with zero false alarms."""
    case_id = create_sample_case_with_evidence()
    db = SessionLocal()
    report = verify_case_integrity(db, case_id)
    db.close()

    assert report["is_valid"] is True
    assert report["tamper_detected"] is False
    assert len(report["tamper_reasons"]) == 0
    assert report["audit_chain_integrity"]["status"] == "VALID"
    assert report["manifest_integrity"]["status"] == "MATCH"
    for item in report["evidence_integrity"]:
        assert item["status"] == "MATCH"


def test_tamper_scenario_1_modify_evidence_byte():
    """Tamper scenario 1: Modify one byte of a stored evidence file."""
    case_id = create_sample_case_with_evidence()
    db = SessionLocal()

    ev = db.query(Evidence).filter(Evidence.case_id == case_id).first()
    file_path = Path(ev.stored_path)

    # Change permissions temporarily to tamper
    os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
    with open(file_path, "r+b") as f:
        content = bytearray(f.read())
        content[0] ^= 0xFF  # Flip bits of first byte
        f.seek(0)
        f.write(content)
    os.chmod(file_path, stat.S_IREAD)

    report = verify_case_integrity(db, case_id)
    db.close()

    assert report["is_valid"] is False
    assert report["tamper_detected"] is True
    assert any("SHA-256 mismatch" in r for r in report["tamper_reasons"])


def test_tamper_scenario_2_edit_audit_payload():
    """Tamper scenario 2: Edit a payload in the audit table."""
    case_id = create_sample_case_with_evidence()
    db = SessionLocal()

    # Modify the payload of seq 2
    audit = db.query(AuditEntry).filter(AuditEntry.case_id == case_id, AuditEntry.seq == 2).first()
    audit.payload_json = '{"tampered":"malicious_change"}'
    db.commit()

    report = verify_case_integrity(db, case_id)
    db.close()

    assert report["is_valid"] is False
    assert report["tamper_detected"] is True
    assert report["audit_chain_integrity"]["status"] == "TAMPERED"
    assert any("Audit payload tampering" in r for r in report["tamper_reasons"])


def test_tamper_scenario_3_delete_audit_entry():
    """Tamper scenario 3: Delete an audit entry."""
    case_id = create_sample_case_with_evidence()
    db = SessionLocal()

    audit = db.query(AuditEntry).filter(AuditEntry.case_id == case_id, AuditEntry.seq == 2).first()
    db.delete(audit)
    db.commit()

    report = verify_case_integrity(db, case_id)
    db.close()

    assert report["is_valid"] is False
    assert report["tamper_detected"] is True
    assert report["audit_chain_integrity"]["status"] == "TAMPERED"
    assert any("Audit sequence discontinuity" in r or "Audit chain break" in r for r in report["tamper_reasons"])


def test_tamper_scenario_4_swap_audit_entries():
    """Tamper scenario 4: Swap two audit entries."""
    case_id = create_sample_case_with_evidence()
    db = SessionLocal()

    e1 = db.query(AuditEntry).filter(AuditEntry.case_id == case_id, AuditEntry.seq == 1).first()
    e2 = db.query(AuditEntry).filter(AuditEntry.case_id == case_id, AuditEntry.seq == 2).first()

    # Swap their seq safely across commits
    e1.seq = 999
    db.commit()
    e2.seq = 1
    db.commit()
    e1.seq = 2
    db.commit()

    report = verify_case_integrity(db, case_id)
    db.close()

    assert report["is_valid"] is False
    assert report["tamper_detected"] is True
    assert report["audit_chain_integrity"]["status"] == "TAMPERED"


def test_tamper_scenario_5_delete_evidence_file():
    """Tamper scenario 5: Delete a stored evidence file."""
    case_id = create_sample_case_with_evidence()
    db = SessionLocal()

    ev = db.query(Evidence).filter(Evidence.case_id == case_id).first()
    file_path = Path(ev.stored_path)
    os.chmod(file_path, stat.S_IWRITE)
    file_path.unlink()

    report = verify_case_integrity(db, case_id)
    db.close()

    assert report["is_valid"] is False
    assert report["tamper_detected"] is True
    assert any("Evidence file missing" in r for r in report["tamper_reasons"])


def test_generate_integrity_tamper_csv():
    """Run all tamper scenarios systematically and export results to experiments/results/integrity_tamper.csv."""
    results_dir = ROOT_DIR / "experiments" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_file = results_dir / "integrity_tamper.csv"

    scenarios = [
        ("untouched_baseline", False),
        ("modify_evidence_byte", True),
        ("edit_audit_payload", True),
        ("delete_audit_entry", True),
        ("swap_audit_entries", True),
        ("delete_evidence_file", True),
    ]

    records = []
    false_alarms = 0

    for scenario_name, should_detect in scenarios:
        case_id = create_sample_case_with_evidence()
        db = SessionLocal()

        if scenario_name == "modify_evidence_byte":
            ev = db.query(Evidence).filter(Evidence.case_id == case_id).first()
            p = Path(ev.stored_path)
            os.chmod(p, stat.S_IWRITE)
            with open(p, "r+b") as f:
                b = bytearray(f.read())
                b[0] ^= 0xFF
                f.seek(0)
                f.write(b)
            os.chmod(p, stat.S_IREAD)
        elif scenario_name == "edit_audit_payload":
            a = db.query(AuditEntry).filter(AuditEntry.case_id == case_id, AuditEntry.seq == 2).first()
            a.payload_json = '{"altered":true}'
            db.commit()
        elif scenario_name == "delete_audit_entry":
            a = db.query(AuditEntry).filter(AuditEntry.case_id == case_id, AuditEntry.seq == 2).first()
            db.delete(a)
            db.commit()
        elif scenario_name == "swap_audit_entries":
            a1 = db.query(AuditEntry).filter(AuditEntry.case_id == case_id, AuditEntry.seq == 1).first()
            a2 = db.query(AuditEntry).filter(AuditEntry.case_id == case_id, AuditEntry.seq == 2).first()
            a1.seq = 999
            db.commit()
            a2.seq = 1
            db.commit()
            a1.seq = 2
            db.commit()
        elif scenario_name == "delete_evidence_file":
            ev = db.query(Evidence).filter(Evidence.case_id == case_id).first()
            p = Path(ev.stored_path)
            os.chmod(p, stat.S_IWRITE)
            p.unlink()

        rep = verify_case_integrity(db, case_id)
        db.close()

        detected = "yes" if rep["tamper_detected"] else "no"

        if scenario_name == "untouched_baseline":
            if rep["tamper_detected"]:
                false_alarms += 1

        records.append({
            "scenario": scenario_name,
            "detected (yes/no)": detected,
            "false alarms on untouched data": false_alarms,
        })

    # Write CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "detected (yes/no)", "false alarms on untouched data"])
        writer.writeheader()
        writer.writerows(records)

    assert csv_file.exists()
    assert false_alarms == 0
