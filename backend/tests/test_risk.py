"""Acceptance tests for Phase 7: Explainable Factor-Based Risk Scoring."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import init_db
from backend.app.main import app
from backend.app.risk.explain import format_risk_explanation

client = TestClient(app)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_example_scenario_yields_high_risk_band():
    """Acceptance test: Section 10 example scenario yields a high risk band with full factor breakdown."""
    with open(FIXTURES_DIR / "example_scenario.json", "r", encoding="utf-8") as f:
        fixture = json.load(f)

    # 1. Create case
    c_res = client.post("/api/cases", json={"title": "High Risk Case"})
    case_id = c_res.json()["id"]

    # 2. Ingest 5 items
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
        assert res.status_code == 201
        ev_id = res.json()["id"]

        # Run analysis on each item
        an_res = client.post(f"/api/cases/{case_id}/evidence/{ev_id}/analyze")
        assert an_res.status_code == 200

    # 3. Correlate
    corr_res = client.post(f"/api/cases/{case_id}/correlate")
    assert corr_res.status_code == 200

    # 4. Fetch Risk Assessment
    risk_res = client.get(f"/api/cases/{case_id}/risk")
    assert risk_res.status_code == 200
    risk_data = risk_res.json()

    # Acceptance Assertions:
    # 1. Band is high
    assert risk_data["risk_band"] == "high"
    assert risk_data["final_score"] >= 0.70

    # 2. Breakdown sums to final score
    breakdown = risk_data["breakdown"]
    sum_contributions = sum(f["contribution"] for f in breakdown)
    assert abs(sum_contributions - risk_data["final_score"]) < 1e-3

    # 3. Every factor lists evidence IDs
    for factor in breakdown:
        assert "evidence_ids" in factor
        if factor["contribution"] > 0:
            assert len(factor["evidence_ids"]) > 0

    # 4. Explanation text generation
    explanation = format_risk_explanation(risk_data)
    assert "HIGH" in explanation
    assert "Key Contributing Factors:" in explanation


def test_benign_only_case_yields_low_risk_band():
    """Acceptance test: Benign-only case yields a low risk band."""
    c_res = client.post("/api/cases", json={"title": "Benign Case"})
    case_id = c_res.json()["id"]

    # Benign SMS
    ev1 = client.post(
        f"/api/cases/{case_id}/evidence",
        json={"text": "Hey, let's meet for lunch today at 1 PM.", "type": "sms"}
    ).json()

    # Benign Note
    ev2 = client.post(
        f"/api/cases/{case_id}/evidence",
        json={"text": "Project roadmap review meeting scheduled.", "type": "chat"}
    ).json()

    # Analyze both
    client.post(f"/api/cases/{case_id}/evidence/{ev1['id']}/analyze")
    client.post(f"/api/cases/{case_id}/evidence/{ev2['id']}/analyze")

    # Correlate
    client.post(f"/api/cases/{case_id}/correlate")

    # Risk evaluation
    risk_res = client.get(f"/api/cases/{case_id}/risk")
    assert risk_res.status_code == 200
    risk_data = risk_res.json()

    assert risk_data["risk_band"] == "low"
    assert risk_data["final_score"] < 0.35


def test_temporal_proximity_exclusion_from_confirmed_links():
    """Acceptance test: TEMPORAL_PROXIMITY is strictly excluded from the confirmed links score."""
    c_res = client.post("/api/cases", json={"title": "Temporal Only Case"})
    case_id = c_res.json()["id"]

    # Two items with timestamps within 10 minutes, but completely unrelated benign texts
    ev1 = client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "text": "Weather forecast is sunny today.",
            "type": "sms",
            "source_timestamp": "2026-03-10 10:00:00",
            "timestamp_source": "user_entered"
        }
    ).json()

    ev2 = client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "text": "Remember to pick up the groceries.",
            "type": "sms",
            "source_timestamp": "2026-03-10 10:08:00",
            "timestamp_source": "user_entered"
        }
    ).json()

    client.post(f"/api/cases/{case_id}/evidence/{ev1['id']}/analyze")
    client.post(f"/api/cases/{case_id}/evidence/{ev2['id']}/analyze")

    # Run correlation: will generate TEMPORAL_PROXIMITY edge
    corr_res = client.post(f"/api/cases/{case_id}/correlate")
    edges = corr_res.json()["edges"]
    assert any(e["link_type"] == "TEMPORAL_PROXIMITY" for e in edges)

    # Check risk
    risk_res = client.get(f"/api/cases/{case_id}/risk")
    risk_data = risk_res.json()

    # The correlation component MUST BE 0.0 because TEMPORAL_PROXIMITY is excluded
    assert risk_data["components"]["correlation_score"] == 0.0
    assert "TEMPORAL_PROXIMITY" not in risk_data["confirmed_link_types"]

