"""Acceptance tests for Phase 8: Audited Forensic Reporting and Citation Enforcement."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import init_db
from backend.app.main import app
from backend.app.reporting.generator import (
    ClaimCitationError,
    build_report_data,
    render_html_report,
    validate_claim_citations,
)

client = TestClient(app)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_claim_citation_enforcement_validation():
    """Acceptance test: Report generator strictly fails if any narrative claim lacks evidence IDs or cites unknown IDs."""
    valid_ids = ["E1", "E2", "E3"]

    # 1. Valid citation passes
    valid_claim = [{"claim_text": "Artifact E1 links to E2", "evidence_ids": ["E1", "E2"]}]
    validate_claim_citations(valid_claim, valid_ids)

    # 2. Claim with empty evidence_ids raises ClaimCitationError
    empty_citation = [{"claim_text": "Unverified hallucinated assertion", "evidence_ids": []}]
    with pytest.raises(ClaimCitationError) as exc_empty:
        validate_claim_citations(empty_citation, valid_ids)
    assert "lacks 'evidence_ids'" in str(exc_empty.value)

    # 3. Claim with missing evidence_ids key raises ClaimCitationError
    missing_key = [{"claim_text": "No citation key provided"}]
    with pytest.raises(ClaimCitationError):
        validate_claim_citations(missing_key, valid_ids)

    # 4. Claim citing non-existent evidence ID raises ClaimCitationError
    unknown_id = [{"claim_text": "Citing fake artifact", "evidence_ids": ["E99"]}]
    with pytest.raises(ClaimCitationError) as exc_unknown:
        validate_claim_citations(unknown_id, valid_ids)
    assert "cites unknown evidence ID" in str(exc_unknown.value)


def test_example_scenario_report_generation_all_sections():
    """Acceptance test: Full forensic report for example scenario renders all required sections in HTML and JSON."""
    with open(FIXTURES_DIR / "example_scenario.json", "r", encoding="utf-8") as f:
        fixture = json.load(f)

    # 1. Ingest example scenario
    c_res = client.post("/api/cases", json={"title": "Report Verification Case"})
    case_id = c_res.json()["id"]

    for item in fixture["evidence_items"]:
        text = item.get("text", "")
        if item["type"] == "apk":
            text = json.dumps(item["apk_metadata"])
        if item.get("sender_phone") and item["sender_phone"] not in text:
            text = f"From: {item['sender_phone']}\n{text}"

        res = client.post(
            f"/api/cases/{case_id}/evidence",
            json={
                "text": text,
                "type": item["type"],
                "source_timestamp": item["source_timestamp"],
                "timestamp_source": item["timestamp_source"],
                "original_filename": item["original_filename"],
            }
        )
        ev_id = res.json()["id"]
        client.post(f"/api/cases/{case_id}/evidence/{ev_id}/analyze")

    client.post(f"/api/cases/{case_id}/correlate")

    # 2. Test HTML Report
    html_res = client.get(f"/api/cases/{case_id}/report")
    assert html_res.status_code == 200
    assert "text/html" in html_res.headers["content-type"]
    html = html_res.text

    # Assert all 10 required report sections are present:
    assert "SCAMTRACE AI Forensic Investigation Report" in html  # Header
    assert "1. Traceable Incident Summary" in html                # Summary
    assert "2. Cryptographic Evidence Inventory" in html          # Evidence inventory
    assert "3. Incident Timeline" in html                        # Timeline
    assert "4. Corroborated Relationship Edges" in html          # Edges
    assert "5. Explainable Risk Breakdown" in html               # Risk breakdown
    assert "6. Multimodal Artifact Explanations" in html         # Explanations
    assert "7. Cryptographic Chain & Tamper Audit" in html       # Integrity
    assert "8. Forensic Limitations & Disclaimers" in html       # Limitations
    assert "SCAMTRACE AI v0.1.0" in html                         # Footer

    # Check evidence citation in claims
    assert "E1" in html
    assert "E2" in html
    assert "SHARED_PHONE" in html

    # 3. Test JSON Report
    json_res = client.get(f"/api/cases/{case_id}/report.json")
    assert json_res.status_code == 200
    report_json = json_res.json()

    assert "case_header" in report_json
    assert "case_summary_claims" in report_json
    assert "evidence_inventory" in report_json
    assert "timeline" in report_json
    assert "correlation_edges" in report_json
    assert "risk_assessment" in report_json
    assert "analyses" in report_json
    assert "integrity_verification" in report_json
    assert "limitations" in report_json
    assert "footer" in report_json

