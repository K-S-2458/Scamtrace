"""Acceptance tests for Phase 5: Correlation Engine, Rules, and Knowledge Graph."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.correlation.engine import correlate_case
from backend.app.correlation.rules import (
    rule_apk_lure_pattern,
    rule_redirect_chain,
    rule_same_brand_impersonation,
    rule_same_cert_hash,
    rule_same_upi_handle,
    rule_shared_domain,
    rule_shared_phone,
    rule_similar_text_template,
    rule_temporal_proximity,
    rule_url_host_match,
)
from backend.app.db.session import SessionLocal, init_db
from backend.app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def load_example_scenario_fixture():
    with open(FIXTURES_DIR / "example_scenario.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_example_scenario_correlation():
    """Acceptance test: Section 10 example scenario produces the expected edges with reasons."""
    fixture = load_example_scenario_fixture()
    db = SessionLocal()

    # Create Case
    c_res = client.post("/api/cases", json={"title": fixture["case_title"], "description": fixture["description"]})
    assert c_res.status_code == 201
    case_id = c_res.json()["id"]

    # Ingest 5 evidence items
    for item in fixture["evidence_items"]:
        text = item.get("text", "")
        if item["type"] == "apk":
            text = json.dumps(item["apk_metadata"])
        # If chat item has sender phone in text
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
            }
        )
        assert ev_res.status_code == 201

    # Run correlation
    corr_res = client.post(f"/api/cases/{case_id}/correlate")
    assert corr_res.status_code == 200
    corr_data = corr_res.json()
    edges = corr_data["edges"]

    assert len(edges) > 0

    link_types = {e["link_type"] for e in edges}
    assert "SHARED_PHONE" in link_types
    assert "SHARED_DOMAIN" in link_types
    assert "URL_HOST_MATCH" in link_types
    assert "SAME_BRAND_IMPERSONATION" in link_types
    assert "APK_LURE_PATTERN" in link_types

    # Assert SHARED_PHONE between E1 and E2
    phone_edges = [e for e in edges if e["link_type"] == "SHARED_PHONE"]
    assert any((e["source"] == "E1" and e["target"] == "E2") for e in phone_edges)
    assert phone_edges[0]["confidence"] == 0.90
    assert "+919999900001" in phone_edges[0]["reason"]
    assert phone_edges[0]["supporting_fields"]["phone"] == "+919999900001"

    # Assert SHARED_DOMAIN between E1 and E2, and E1 and E3
    domain_edges = [e for e in edges if e["link_type"] == "SHARED_DOMAIN"]
    pairs = {(e["source"], e["target"]) for e in domain_edges}
    assert ("E1", "E2") in pairs
    assert ("E1", "E3") in pairs

    # Assert URL_HOST_MATCH between E1 and E2
    host_edges = [e for e in edges if e["link_type"] == "URL_HOST_MATCH"]
    assert any((e["source"] == "E1" and e["target"] == "E2") for e in host_edges)

    # Test Graph Endpoint
    g_res = client.get(f"/api/cases/{case_id}/graph")
    assert g_res.status_code == 200
    g_data = g_res.json()
    assert "elements" in g_data
    assert len(g_data["elements"]["nodes"]) >= 5
    assert len(g_data["elements"]["edges"]) >= len(edges)
    assert len(g_data["clusters"]) >= 1

    db.close()


class MockEvidence:
    def __init__(self, id, type="sms", raw_text="", source_timestamp=None, uploaded_at=None):
        self.id = id
        self.type = type
        self.raw_text = raw_text
        self.source_timestamp = source_timestamp
        self.uploaded_at = uploaded_at


class MockEntity:
    def __init__(self, entity_type, value, metadata=None):
        self.entity_type = entity_type
        self.value = value
        self.metadata = metadata or {}


def test_rule_shared_phone_positive_and_negative():
    """Unit test: SHARED_PHONE positive and negative cases."""
    ev1 = MockEvidence("E1")
    ev2 = MockEvidence("E2")
    ev3 = MockEvidence("E3")

    ents = {
        "E1": [MockEntity("phone", "+919999900001")],
        "E2": [MockEntity("phone", "+919999900001")],
        "E3": [MockEntity("phone", "+919999900002")],
    }

    proposals = rule_shared_phone([ev1, ev2, ev3], ents)
    assert len(proposals) == 1
    assert proposals[0].link_type == "SHARED_PHONE"
    assert proposals[0].source_evidence_id == "E1"
    assert proposals[0].target_evidence_id == "E2"


def test_rule_same_upi_handle_positive_and_negative():
    """Unit test: SAME_UPI_HANDLE positive and negative cases."""
    ev1 = MockEvidence("E1")
    ev2 = MockEvidence("E2")
    ev3 = MockEvidence("E3")

    ents_pos = {
        "E1": [MockEntity("upi_handle", "victim@fakebank")],
        "E2": [MockEntity("upi_handle", "victim@fakebank")],
    }
    assert len(rule_same_upi_handle([ev1, ev2], ents_pos)) == 1

    ents_neg = {
        "E1": [MockEntity("upi_handle", "user1@fakebank")],
        "E3": [MockEntity("upi_handle", "user2@fakebank")],
    }
    assert len(rule_same_upi_handle([ev1, ev3], ents_neg)) == 0


def test_rule_same_cert_hash_positive_and_negative():
    """Unit test: SAME_CERT_HASH positive and negative cases."""
    cert = "a" * 64
    ev1 = MockEvidence("E1", type="apk")
    ev2 = MockEvidence("E2", type="apk")
    ev3 = MockEvidence("E3", type="apk")

    ents = {
        "E1": [MockEntity("cert_sha256", cert)],
        "E2": [MockEntity("cert_sha256", cert)],
        "E3": [MockEntity("cert_sha256", "b" * 64)],
    }
    props = rule_same_cert_hash([ev1, ev2, ev3], ents)
    assert len(props) == 1
    assert props[0].confidence == 0.95


def test_rule_redirect_chain_positive_and_negative():
    """Unit test: REDIRECT_CHAIN positive and negative cases."""
    ev1 = MockEvidence("E1")
    ev2 = MockEvidence("E2")
    ents = {
        "E1": [MockEntity("url", "https://short.test/xyz")],
        "E2": [MockEntity("url", "https://final-destination.test/login")],
    }

    # Positive: user supplied mapping
    mapping = {"https://short.test/xyz": "https://final-destination.test/login"}
    props = rule_redirect_chain([ev1, ev2], ents, redirect_mappings=mapping)
    assert len(props) == 1
    assert props[0].link_type == "REDIRECT_CHAIN"

    # Negative: no mapping supplied
    assert len(rule_redirect_chain([ev1, ev2], ents, redirect_mappings=None)) == 0


def test_rule_temporal_proximity_positive_and_negative():
    """Unit test: TEMPORAL_PROXIMITY positive and negative cases."""
    import datetime
    t0 = datetime.datetime(2026, 3, 10, 10, 0, 0)
    t_close = datetime.datetime(2026, 3, 10, 10, 15, 0)  # 15 min diff
    t_far = datetime.datetime(2026, 3, 10, 12, 0, 0)    # 120 min diff

    ev1 = MockEvidence("E1", source_timestamp=t0)
    ev2 = MockEvidence("E2", source_timestamp=t_close)
    ev3 = MockEvidence("E3", source_timestamp=t_far)

    # Positive
    p_pos = rule_temporal_proximity([ev1, ev2], {}, window_minutes=30)
    assert len(p_pos) == 1
    assert p_pos[0].confidence == 0.20

    # Negative
    p_neg = rule_temporal_proximity([ev1, ev3], {}, window_minutes=30)
    assert len(p_neg) == 0


def test_correlation_rule_switch_ablation():
    """Unit test: Ablation toggle can disable an individual rule."""
    ev1 = MockEvidence("E1")
    ev2 = MockEvidence("E2")
    ents = {
        "E1": [MockEntity("phone", "+919999900001")],
        "E2": [MockEntity("phone", "+919999900001")],
    }

    # Enabled
    assert len(rule_shared_phone([ev1, ev2], ents, switches={"SHARED_PHONE": True})) == 1
    # Ablated / Disabled
    assert len(rule_shared_phone([ev1, ev2], ents, switches={"SHARED_PHONE": False})) == 0

