"""SMS and short-text scam analyzer for SCAMTRACE AI.
Uses TF-IDF + Logistic Regression model with linear coefficient explanations.
"""
import os
import unicodedata
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np

from backend.app.analyzers.base import AnalysisResult, BaseAnalyzer
from backend.app.config import ROOT_DIR

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "artifacts" / "sms_model.joblib"


def clean_text(text: str) -> str:
    """Normalize Unicode and whitespace while preserving tokens."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    lowered = norm.lower()
    return re.sub(r"\s+", " ", lowered).strip()


class SMSAnalyzer(BaseAnalyzer):
    """Forensic analyzer for SMS and short messages."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH
        self.model = None
        self.model_name = "TFIDF_LogisticRegression"
        self.model_version = "1.0.0"
        self._load_model()

    def _load_model(self):
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
            except Exception as e:
                print(f"[SMSAnalyzer] Error loading model: {e}")
                self.model = None

    def analyze(self, raw_bytes: bytes, raw_text: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Analyze text and produce probability score and top n-gram explanations."""
        text = raw_text or ""
        if not text and raw_bytes:
            try:
                text = raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                text = ""

        cleaned = clean_text(text)
        if not cleaned:
            return AnalysisResult(
                label="benign",
                score=0.0,
                model_name=self.model_name,
                model_version=self.model_version,
                top_factors=[],
                metadata={"cleaned_text": ""},
            )

        # Lazy load if not loaded yet
        if self.model is None:
            self._load_model()

        if self.model is not None:
            # Predict probability
            proba = float(self.model.predict_proba([cleaned])[0, 1])
            label = "suspicious" if proba >= 0.5 else "benign"

            # Compute linear explanations (coef * tfidf value)
            top_factors = self._explain_prediction(cleaned)
        else:
            # Fallback heuristic if model artifact is missing
            suspicious_terms = ["kyc", "block", "urgent", "debited", "suspend", "reward", "lottery", "call"]
            matches = [term for term in suspicious_terms if term in cleaned]
            proba = min(1.0, 0.2 * len(matches))
            label = "suspicious" if proba >= 0.5 else "benign"
            top_factors = [
                {"feature": term, "contribution": 0.2, "direction": "suspicious", "value": 1.0}
                for term in matches
            ]

        return AnalysisResult(
            label=label,
            score=proba,
            model_name=self.model_name,
            model_version=self.model_version,
            top_factors=top_factors,
            metadata={"text_length": len(text), "cleaned_length": len(cleaned)},
        )

    def _explain_prediction(self, cleaned_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Extract highest-contributing n-gram tokens (weight * feature coefficient)."""
        try:
            tfidf_union = self.model.named_steps["tfidf"]
            clf = self.model.named_steps["clf"]

            feature_names = tfidf_union.get_feature_names_out()
            feature_vector = tfidf_union.transform([cleaned_text]).toarray()[0]
            coefs = clf.coef_[0]

            contributions = feature_vector * coefs
            non_zero_indices = np.where(feature_vector > 0)[0]

            if len(non_zero_indices) == 0:
                return []

            # Sort indices by contribution (descending: highest positive contribution to suspicious)
            sorted_indices = sorted(
                non_zero_indices,
                key=lambda idx: abs(contributions[idx]),
                reverse=True
            )[:top_k]

            factors = []
            for idx in sorted_indices:
                feat_name = feature_names[idx].split("__")[-1]  # strip word__ / char__ prefix
                contrib = float(contributions[idx])
                direction = "suspicious" if contrib > 0 else "benign"
                factors.append({
                    "feature": feat_name,
                    "contribution": round(contrib, 4),
                    "direction": direction,
                    "value": round(float(feature_vector[idx]), 4),
                })
            return factors
        except Exception as e:
            return [{"feature": "error_explaining", "contribution": 0.0, "direction": "neutral", "value": str(e)}]

