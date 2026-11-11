"""Lexical offline URL analyzer for SCAMTRACE AI.
Extracts 15 offline features and applies a Random Forest classifier with factor explanations.
Strictly offline: Zero DNS, WHOIS, or HTTP requests.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np

from backend.app.analyzers.base import AnalysisResult, BaseAnalyzer
from backend.app.extraction.entities import extract_entities_from_text
from backend.app.ml.train_url import FEATURE_NAMES, extract_lexical_url_features

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "artifacts" / "url_model.joblib"


class URLAnalyzer(BaseAnalyzer):
    """Offline forensic analyzer for URLs."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH
        self.model = None
        self.feature_names = FEATURE_NAMES
        self.medians = {}
        self.model_name = "Lexical_RandomForest"
        self.model_version = "1.0.0"
        self._load_model()

    def _load_model(self):
        if self.model_path.exists():
            try:
                bundle = joblib.load(self.model_path)
                self.model = bundle["model"]
                self.feature_names = bundle.get("feature_names", FEATURE_NAMES)
                self.medians = bundle.get("medians", {})
            except Exception as e:
                print(f"[URLAnalyzer] Error loading model: {e}")
                self.model = None

    def analyze(self, raw_bytes: bytes, raw_text: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Analyze URL and produce risk probability score and feature explanations."""
        url = (raw_text or "").strip()
        if not url and raw_bytes:
            try:
                url = raw_bytes.decode("utf-8", errors="replace").strip()
            except Exception:
                url = ""

        if not url:
            return AnalysisResult(
                label="benign",
                score=0.0,
                model_name=self.model_name,
                model_version=self.model_version,
                top_factors=[],
                metadata={"url": ""},
            )

        domain_age = None
        if metadata and "domain_age_days" in metadata:
            try:
                domain_age = int(metadata["domain_age_days"])
            except Exception:
                domain_age = None

        features = extract_lexical_url_features(url, domain_age_days=domain_age)
        feat_vector = np.array([[features[name] for name in self.feature_names]])

        if self.model is None:
            self._load_model()

        if self.model is not None:
            proba = float(self.model.predict_proba(feat_vector)[0, 1])
            label = "suspicious" if proba >= 0.5 else "benign"
            top_factors = self._explain_prediction(features)
        else:
            # Fallback heuristic
            score_terms = features["keyword_count"] * 0.2 + features["brand_mismatch"] * 0.4 + features["is_suspicious_tld"] * 0.3
            proba = min(1.0, score_terms)
            label = "suspicious" if proba >= 0.5 else "benign"
            top_factors = [
                {"feature": k, "contribution": round(v, 2), "direction": "suspicious", "value": features[k]}
                for k, v in features.items() if v > 0
            ][:5]

        extracted_ents = []
        try:
            extracted_ents = [e.to_dict() for e in extract_entities_from_text(url)]
        except Exception:
            extracted_ents = []

        return AnalysisResult(
            label=label,
            score=proba,
            model_name=self.model_name,
            model_version=self.model_version,
            top_factors=top_factors,
            metadata={"features": features, "url": url, "extracted_entities": extracted_ents},
        )

    def _explain_prediction(self, features: Dict[str, float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Explain model prediction based on feature importance and deviations from training medians."""
        importances = self.model.feature_importances_
        factors = []

        for i, name in enumerate(self.feature_names):
            val = features[name]
            median = self.medians.get(name, 0.0)
            imp = importances[i]

            # High value relative to median pushes score
            diff = val - median
            contribution = float(imp * (1.0 if diff > 0 else -0.5 if diff < 0 else 0.0))
            direction = "suspicious" if val > median and val > 0 else "benign"

            if val > 0 or diff != 0:
                factors.append({
                    "feature": name,
                    "contribution": round(contribution, 4),
                    "direction": direction,
                    "value": round(val, 2),
                })

        # Sort by contribution descending
        factors = sorted(factors, key=lambda x: abs(x["contribution"]), reverse=True)[:top_k]
        return factors

