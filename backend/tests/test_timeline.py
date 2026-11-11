"""Acceptance tests for Phase 6: Timeline Reconstruction and Conflict Detection."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.correlation.engine import correlate_case
from backend.app.db.session import SessionLocal, init_db
from backend.app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_example_scenario_timeline_order():
    """Acceptance test: Example scenario timeline matches ground truth order (E1 -> E2 -> E3 -> E4 -> E5)."""
    with open(FIXTURES_DIR / "example_scenario.json", "r", encoding="utf-8") as f:
        fixture = json.load(f)

    # 1. Create Case
    c_res = client.post("/api/cases", json={"title": "Timeline Test Case"})
    case_id = c_res.json()["id"]

    # 2. Ingest in arbitrary order (e.g. E5, E3, E1, E4, E2)
    ingestion_order = [fixture["evidence_items"][4], fixture["evidence_items"][2], fixture["evidence_items"][0], fixture["evidence_items"][3], fixture["evidence_items"][1]]
    for item in ingestion_order:
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

    # 3. Correlate
    client.post(f"/api/cases/{case_id}/correlate")

    # 4. Fetch Timeline
    tl_res = client.get(f"/api/cases/{case_id}/timeline")
    assert tl_res.status_code == 200
    tl_data = tl_res.json()

    assert tl_data["has_conflicts"] is False
    assert len(tl_data["timeline"]) == 5

    # Check timestamps are strictly chronological
    ts_list = [item["timestamp"] for item in tl_data["timeline"]]
    assert ts_list == sorted(ts_list)

    # Check time gaps are computed
    assert tl_data["timeline"][1]["time_gap_from_prev"] is not None
    assert tl_data["timeline"][0]["time_uncertain"] is False


def test_undated_evidence_flagged_time_uncertain():
    """Acceptance test: Undated items are flagged as time_uncertain and placed after dated items."""
    c_res = client.post("/api/cases", json={"title": "Undated Evidence Case"})
    case_id = c_res.json()["id"]

    # Item with timestamp
    client.post(
        f"/api/cases/{case_id}/evidence",
        json={"text": "Dated item", "type": "sms", "source_timestamp": "2026-03-10 10:00:00"}
    )
    # Item without timestamp
    client.post(
        f"/api/cases/{case_id}/evidence",
        json={"text": "Undated item", "type": "sms"}
    )

    tl_res = client.get(f"/api/cases/{case_id}/timeline")
    assert tl_res.status_code == 200
    items = tl_res.json()["timeline"]

    assert len(items) == 2
    assert items[0]["time_uncertain"] is False
    assert items[1]["time_uncertain"] is True
    assert items[1]["source_timestamp"] is None


def test_apk_before_url_conflict_detected():
    """Acceptance test: APK installation timestamp preceding lure message is flagged as an ordering conflict."""
    c_res = client.post("/api/cases", json={"title": "Causal Conflict Case"})
    case_id = c_res.json()["id"]

    # 1. APK installed at 10:00:00
    apk_meta = {
        "package_name": "com.fake.kyc",
        "requested_permissions": ["android.permission.READ_SMS", "android.permission.BIND_ACCESSIBILITY_SERVICE"]
    }
    client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "text": json.dumps(apk_meta),
            "type": "apk",
            "source_timestamp": "2026-03-10 10:00:00",
            "timestamp_source": "user_entered"
        }
    )

    # 2. Lure message sent later at 10:30:00 (30 min later, exceeds 2 min tolerance!)
    client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "text": "Please install the updated app now from our portal.",
            "type": "sms",
            "source_timestamp": "2026-03-10 10:30:00",
            "timestamp_source": "user_entered"
        }
    )

    # Run correlation to form APK_LURE_PATTERN edge
    client.post(f"/api/cases/{case_id}/correlate")

    # Fetch timeline
    tl_res = client.get(f"/api/cases/{case_id}/timeline")
    assert tl_res.status_code == 200
    tl_data = tl_res.json()

    assert tl_data["has_conflicts"] is True
    assert len(tl_data["conflicts"]) >= 1
    conflict_desc = tl_data["conflicts"][0]["description"]
    assert "precedes lure item" in conflict_desc

