"""End-to-End full lifecycle integration test for SCAMTRACE AI.
Simulates the entire investigator workflow:
Create Case -> Ingest Multimodal Evidence -> Analyze -> Correlate -> Graph -> Timeline -> Risk -> Report -> Verify.
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import init_db
from backend.app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_full_investigator_workflow_end_to_end():
    """Verify entire workflow matching Section 10 example scenario end-to-end."""
    with open(FIXTURES_DIR / "example_scenario.json", "r", encoding="utf-8") as f:
        fixture = json.load(f)

    # 1. Create Case
    create_res = client.post(
        "/api/cases",
        json={
            "title": fixture["case_title"],
            "description": fixture["description"],
            "notes": "Opened investigation based on consumer grievance reports.",
        },
    )
    assert create_res.status_code == 201
    case = create_res.json()
    case_id = case["id"]
    assert case["status"] == "open"

    # 2. Ingest Multimodal Evidence Items E1 to E5
    evidence_ids = []
    for item in fixture["evidence_items"]:
        text = item.get("text", "")
        if item["type"] == "apk":
            text = json.dumps(item["apk_metadata"])
        if item.get("sender_phone") and item["sender_phone"] not in text:
            text = f"From: {item['sender_phone']}\n{text}"

        ev_res = client.post(
            f"/api/cases/{case_id}/evidence",
            json={
                "text": text,
                "type": item["type"],
                "source_timestamp": item["source_timestamp"],
                "timestamp_source": item["timestamp_source"],
                "original_filename": item["original_filename"],
                "uploader": item.get("uploader", "investigator"),
            },
        )
        assert ev_res.status_code == 201
        ev_data = ev_res.json()
        evidence_ids.append(ev_data["id"])

    assert evidence_ids == ["E1", "E2", "E3", "E4", "E5"]

    # 3. Analyze each piece of evidence
    for eid in evidence_ids:
        an_res = client.post(f"/api/cases/{case_id}/evidence/{eid}/analyze")
        assert an_res.status_code == 200
        an_data = an_res.json()
        assert an_data["evidence_id"] == eid
        assert "top_factors" in an_data

    # 4. Run Cross-Artifact Correlation Engine
    corr_res = client.post(f"/api/cases/{case_id}/correlate")
    assert corr_res.status_code == 200
    corr_data = corr_res.json()
    edges = corr_data["edges"]

    # Assert expected edges from Section 10
    link_types = {e["link_type"] for e in edges}
    assert "SHARED_PHONE" in link_types
    assert "SHARED_DOMAIN" in link_types
    assert "URL_HOST_MATCH" in link_types
    assert "SAME_BRAND_IMPERSONATION" in link_types
    assert "APK_LURE_PATTERN" in link_types

    # 5. Query Cytoscape Knowledge Graph
    graph_res = client.get(f"/api/cases/{case_id}/graph")
    assert graph_res.status_code == 200
    g_data = graph_res.json()
    assert len(g_data["elements"]["nodes"]) >= 5
    assert len(g_data["clusters"]) >= 1

    # 6. Query Incident Timeline
    tl_res = client.get(f"/api/cases/{case_id}/timeline")
    assert tl_res.status_code == 200
    tl_data = tl_res.json()
    assert tl_data["has_conflicts"] is False
    assert [item["evidence_id"] for item in tl_data["timeline"]] == ["E1", "E2", "E3", "E4", "E5"]

    # 7. Evaluate Case Risk
    risk_res = client.get(f"/api/cases/{case_id}/risk")
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert risk_data["risk_band"] == "high"
    assert risk_data["final_score"] >= 0.70

    # 8. Cryptographic Tamper Verification
    verify_res = client.post(f"/api/cases/{case_id}/verify")
    assert verify_res.status_code == 200
    ver_data = verify_res.json()
    assert ver_data["is_valid"] is True
    assert ver_data["tamper_detected"] is False

    # 9. Audited Report (HTML and JSON)
    html_res = client.get(f"/api/cases/{case_id}/report")
    assert html_res.status_code == 200
    assert "text/html" in html_res.headers["content-type"]
    assert "SCAMTRACE AI Forensic Investigation Report" in html_res.text

    json_res = client.get(f"/api/cases/{case_id}/report.json")
    assert json_res.status_code == 200
    j_data = json_res.json()
    assert len(j_data["case_summary_claims"]) > 0
    for claim in j_data["case_summary_claims"]:
        assert len(claim["evidence_ids"]) > 0

    # 10. Audit Chain Verification
    audit_res = client.get(f"/api/cases/{case_id}/audit")
    assert audit_res.status_code == 200
    audit_entries = audit_res.json()
    # At least create, 5 ingests, 5 analyses, correlate, verify, generate report
    assert len(audit_entries) >= 12
    actions = [e["action"] for e in audit_entries]
    assert "create_case" in actions
    assert "ingest" in actions
    assert "analyze" in actions
    assert "correlate" in actions
    assert "verify" in actions
    assert "generate_report" in actions

