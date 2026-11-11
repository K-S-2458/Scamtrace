"""Acceptance tests for Phase 3: Multimodal Forensic Analyzers and Explainability."""
import io
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.analyzers.apk import APKAnalyzer
from backend.app.analyzers.screenshot import ScreenshotAnalyzer
from backend.app.analyzers.sms import SMSAnalyzer
from backend.app.analyzers.url import URLAnalyzer
from backend.app.db.session import init_db
from backend.app.main import app
from backend.app.ml.train_apk import extract_apk_features
from backend.app.ml.train_url import extract_lexical_url_features

client = TestClient(app)
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts"


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_sms_analyzer_classification_and_explanation():
    """Test text/SMS analyzer classifies suspicious message and returns top n-gram factors."""
    analyzer = SMSAnalyzer()

    # Suspicious KYC lure text
    susp_text = "URGENT: Your KYC is expiring today. Update immediately at http://kyc.test/verify to avoid account suspension."
    res_susp = analyzer.analyze(raw_bytes=susp_text.encode("utf-8"), raw_text=susp_text)

    assert res_susp.score >= 0.5
    assert res_susp.label == "suspicious"
    assert len(res_susp.top_factors) > 0
    # Every factor has feature, contribution, direction
    for factor in res_susp.top_factors:
        assert "feature" in factor
        assert "contribution" in factor
        assert factor["direction"] in {"suspicious", "benign", "neutral"}

    # Benign text
    benign_text = "Hey, are we still meeting for lunch today at 1 PM?"
    res_benign = analyzer.analyze(raw_bytes=benign_text.encode("utf-8"), raw_text=benign_text)
    assert res_benign.score < 0.5
    assert res_benign.label == "benign"


def test_url_feature_extraction_and_analysis():
    """Test URL feature extraction and Random Forest analysis with explainability."""
    url = "https://kyc-update.example-bank-secure.test/verify?step=1&user_id=1234"
    feats = extract_lexical_url_features(url)

    assert feats["url_length"] == len(url)
    assert feats["is_https"] == 1.0
    assert feats["keyword_count"] >= 2.0  # kyc, verify
    assert feats["is_suspicious_tld"] == 1.0  # .test
    assert feats["brand_mismatch"] == 1.0  # example-bank-secure.test is not official for examplebank

    analyzer = URLAnalyzer()
    res = analyzer.analyze(raw_bytes=url.encode("utf-8"), raw_text=url)

    assert res.score >= 0.5
    assert res.label == "suspicious"
    assert len(res.top_factors) > 0
    for factor in res.top_factors:
        assert "feature" in factor
        assert "contribution" in factor


def test_apk_metadata_extraction_and_analysis():
    """Test APK static analysis without execution and verify high-risk permission traces."""
    manifest_meta = {
        "package_name": "com.fake.kycupdate",
        "min_sdk": 21,
        "target_sdk": 30,
        "requested_permissions": [
            "android.permission.INTERNET",
            "android.permission.READ_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.BIND_ACCESSIBILITY_SERVICE",
        ],
        "activities": ["com.fake.kycupdate.MainActivity"],
        "services": ["com.fake.kycupdate.AccessibilitySpy"],
        "receivers": ["com.fake.kycupdate.SmsReceiver"],
        "cert_sha256": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01",
    }

    feats = extract_apk_features(manifest_meta)
    assert feats["suspicious_permissions_count"] >= 3.0
    assert feats["perm_read_sms"] == 1.0
    assert feats["perm_bind_accessibility_service"] == 1.0

    analyzer = APKAnalyzer()
    res = analyzer.analyze(
        raw_bytes=b"",
        raw_text=json.dumps(manifest_meta),
        metadata={"apk_metadata": manifest_meta}
    )

    assert res.score >= 0.5
    assert res.label == "suspicious"
    assert any("permission" in f["feature"].lower() for f in res.top_factors)
    assert res.metadata["package_name"] == "com.fake.kycupdate"
    assert res.metadata["cert_sha256"].startswith("a1b2c3d4")


def test_screenshot_analyzer_metadata_only():
    """Test screenshot analyzer computes digest and dimensions with zero classification score."""
    analyzer = ScreenshotAnalyzer()

    # Generate a tiny 10x10 PNG bytes
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (10, 10), color="blue")
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    res = analyzer.analyze(raw_bytes=png_bytes)
    assert res.score == 0.0
    assert res.label == "benign"
    assert res.metadata["width"] == 10
    assert res.metadata["height"] == 10
    assert res.metadata["format"] == "PNG"
    assert res.metadata["ocr_performed"] is False


def test_analyzer_api_endpoint():
    """Test POST /api/cases/{case_id}/evidence/{evidence_id}/analyze endpoint."""
    case_res = client.post("/api/cases", json={"title": "Analyzer API Test"})
    case_id = case_res.json()["id"]

    ev_res = client.post(
        f"/api/cases/{case_id}/evidence",
        json={"text": "URGENT: Your KYC is expiring. Update now at http://kyc.test/verify. Call +91 99999 00001", "type": "sms"}
    )
    ev_id = ev_res.json()["id"]

    # Run analysis
    an_res = client.post(f"/api/cases/{case_id}/evidence/{ev_id}/analyze")
    assert an_res.status_code == 200
    data = an_res.json()

    assert data["evidence_id"] == ev_id
    assert data["case_id"] == case_id
    assert data["label"] in {"suspicious", "benign"}
    assert 0.0 <= data["score"] <= 1.0
    assert isinstance(data["top_factors"], list)

    # Verify evidence status updated
    ev_check = client.get(f"/api/cases/{case_id}/evidence/{ev_id}")
    assert ev_check.json()["analysis_status"] == "analyzed"

    # Verify audit entry recorded
    audit_res = client.get(f"/api/cases/{case_id}/audit")
    actions = [e["action"] for e in audit_res.json()]
    assert "analyze" in actions


def test_training_metrics_exist_and_cover_5_seeds():
    """Acceptance test: training runs and saves metrics over at least 5 seeds."""
    for model_name in ["sms", "url", "apk"]:
        metrics_file = ARTIFACTS_DIR / f"{model_name}_metrics.json"
        assert metrics_file.exists(), f"Metrics file missing for {model_name}"

        with open(metrics_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "seeds" in data
        assert len(data["seeds"]) >= 5

        # Check metrics keys
        if model_name == "sms":
            assert len(data["logistic_regression"]) >= 5
            assert len(data["linear_svm"]) >= 5
            for m in data["logistic_regression"]:
                for metric in ["precision", "recall", "f1", "roc_auc", "pr_auc", "fpr"]:
                    assert metric in m
        else:
            assert len(data["random_forest"]) >= 5
            assert len(data["logistic_regression"]) >= 5
            for m in data["random_forest"]:
                for metric in ["precision", "recall", "f1", "roc_auc", "pr_auc", "fpr"]:
                    assert metric in m

