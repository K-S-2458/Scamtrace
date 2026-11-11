"""Static APK metadata analyzer for SCAMTRACE AI.
Strictly offline, static-only analysis: NEVER installs or executes the APK.
Extracts manifest permissions, components, SDK targets, and certificate fingerprints.
"""
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np

from backend.app.analyzers.base import AnalysisResult, BaseAnalyzer
from backend.app.config import APK_SUSPICIOUS_PERMISSIONS
from backend.app.ml.train_apk import APK_FEATURE_NAMES, extract_apk_features

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "artifacts" / "apk_model.joblib"


class APKAnalyzer(BaseAnalyzer):
    """Forensic analyzer for Android APK packages (static metadata only)."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH
        self.model = None
        self.feature_names = APK_FEATURE_NAMES
        self.model_name = "StaticAPK_RandomForest"
        self.model_version = "1.0.0"
        self._load_model()

    def _load_model(self):
        if self.model_path.exists():
            try:
                bundle = joblib.load(self.model_path)
                self.model = bundle["model"]
                self.feature_names = bundle.get("feature_names", APK_FEATURE_NAMES)
            except Exception as e:
                print(f"[APKAnalyzer] Error loading model: {e}")
                self.model = None

    def analyze(self, raw_bytes: bytes, raw_text: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Statically inspect APK bytes or manifest metadata and classify threat score."""
        parsed_meta = self._extract_metadata(raw_bytes, raw_text, metadata)

        features = extract_apk_features(parsed_meta)
        feat_vector = np.array([[features[name] for name in self.feature_names]])

        if self.model is None:
            self._load_model()

        if self.model is not None:
            proba = float(self.model.predict_proba(feat_vector)[0, 1])
            label = "suspicious" if proba >= 0.5 else "benign"
            top_factors = self._explain_prediction(features, parsed_meta)
        else:
            # Fallback heuristic
            susp_count = features["suspicious_permissions_count"]
            proba = min(1.0, 0.25 * susp_count)
            label = "suspicious" if proba >= 0.5 else "benign"
            top_factors = [
                {"feature": "suspicious_permissions_count", "contribution": round(proba, 2), "direction": "suspicious", "value": susp_count}
            ]

        return AnalysisResult(
            label=label,
            score=proba,
            model_name=self.model_name,
            model_version=self.model_version,
            top_factors=top_factors,
            metadata={
                "package_name": parsed_meta.get("package_name"),
                "cert_sha256": parsed_meta.get("cert_sha256"),
                "min_sdk": parsed_meta.get("min_sdk"),
                "target_sdk": parsed_meta.get("target_sdk"),
                "requested_permissions": parsed_meta.get("requested_permissions", []),
                "activities": parsed_meta.get("activities", []),
                "services": parsed_meta.get("services", []),
                "receivers": parsed_meta.get("receivers", []),
            },
        )

    def _extract_metadata(self, raw_bytes: bytes, raw_text: Optional[str], metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Safely extract manifest and certificate metadata from APK zip or metadata."""
        if metadata and "apk_metadata" in metadata:
            return metadata["apk_metadata"]

        if metadata and "package_name" in metadata:
            return metadata

        # Check if text is JSON formatted metadata
        if raw_text:
            try:
                data = json.loads(raw_text)
                if isinstance(data, dict) and ("package_name" in data or "requested_permissions" in data):
                    return data
            except Exception:
                pass

        extracted = {
            "package_name": "unknown.apk.package",
            "min_sdk": 21,
            "target_sdk": 30,
            "requested_permissions": [],
            "activities": [],
            "services": [],
            "receivers": [],
            "cert_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        }

        if not raw_bytes:
            return extracted

        # Try parsing as Zip archive
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                # Look for certificate in META-INF
                for name in z.namelist():
                    if name.startswith("META-INF/") and (name.endswith(".RSA") or name.endswith(".DSA") or name.endswith(".EC") or name.endswith(".SF")):
                        cert_data = z.read(name)
                        extracted["cert_sha256"] = hashlib.sha256(cert_data).hexdigest()
                        break

                # Inspect AndroidManifest.xml
                if "AndroidManifest.xml" in z.namelist():
                    manifest_data = z.read("AndroidManifest.xml")
                    # Try plain XML parsing first
                    try:
                        root = ET.fromstring(manifest_data)
                        extracted["package_name"] = root.attrib.get("package", "unknown.apk.package")
                        for elem in root.findall("uses-permission"):
                            perm = elem.attrib.get("{http://schemas.android.com/apk/res/android}name") or elem.attrib.get("name")
                            if perm:
                                extracted["requested_permissions"].append(perm)
                    except Exception:
                        # Fallback for binary AXML: extract readable ASCII/UTF-8 strings using regex
                        # Looks for permission strings like android.permission.SEND_SMS
                        strings = re.findall(rb"android\.permission\.[A-Za-z0-9_]+", manifest_data)
                        extracted["requested_permissions"] = list({s.decode("ascii") for s in strings})

                        # Extract potential package name
                        pkg_matches = re.findall(rb"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2,}", manifest_data)
                        if pkg_matches:
                            extracted["package_name"] = pkg_matches[0].decode("ascii", errors="ignore")
        except Exception:
            pass

        return extracted

    def _explain_prediction(self, features: Dict[str, float], parsed_meta: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """Explain model prediction: feature contributions and suspicious permission trace."""
        importances = self.model.feature_importances_
        factors = []

        # Find which suspicious permissions were triggered
        suspicious_present = []
        for p in parsed_meta.get("requested_permissions", []):
            short = p.replace("android.permission.", "")
            if any(short == s.replace("android.permission.", "") for s in APK_SUSPICIOUS_PERMISSIONS):
                suspicious_present.append(short)

        if suspicious_present:
            factors.append({
                "feature": "high_risk_permissions_detected",
                "contribution": 0.5,
                "direction": "suspicious",
                "value": ", ".join(sorted(set(suspicious_present))),
            })

        for i, name in enumerate(self.feature_names):
            val = features[name]
            imp = importances[i]
            if val > 0 and imp > 0.05:
                factors.append({
                    "feature": name,
                    "contribution": round(float(imp * val), 4),
                    "direction": "suspicious",
                    "value": round(val, 2),
                })

        factors = sorted(factors, key=lambda x: x["contribution"], reverse=True)[:top_k]
        return factors

