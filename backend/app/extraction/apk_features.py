"""Static APK feature extraction for SCAMTRACE AI.
Purely offline and lightweight: no Scikit-Learn or Pandas dependencies.
"""
from typing import Any, Dict, List

from backend.app.config import APK_SUSPICIOUS_PERMISSIONS


def build_apk_feature_names() -> List[str]:
    """Construct ordered list of APK feature names focused on permissions and components."""
    names = [
        "suspicious_permissions_count",
        "activities_count",
        "services_count",
        "receivers_count",
    ]
    # Individual binary features for each monitored permission
    for perm in APK_SUSPICIOUS_PERMISSIONS:
        short_name = perm.replace("android.permission.", "").lower()
        names.append(f"perm_{short_name}")
    return names


APK_FEATURE_NAMES = build_apk_feature_names()


def extract_apk_features(manifest_metadata: Dict[str, Any]) -> Dict[str, float]:
    """Extract numeric feature vector from APK manifest metadata dict."""
    perms = set(manifest_metadata.get("requested_permissions", []))
    # Normalize permission strings (check both full and short forms)
    norm_perms = set()
    for p in perms:
        norm_perms.add(p)
        if not p.startswith("android.permission."):
            norm_perms.add(f"android.permission.{p}")

    susp_count = 0
    perm_flags = {}
    for monitored in APK_SUSPICIOUS_PERMISSIONS:
        short_name = monitored.replace("android.permission.", "").lower()
        has_perm = 1.0 if (monitored in norm_perms or monitored.split(".")[-1] in norm_perms) else 0.0
        if has_perm > 0:
            susp_count += 1
        perm_flags[f"perm_{short_name}"] = has_perm

    feats = {
        "suspicious_permissions_count": float(susp_count),
        "activities_count": float(len(manifest_metadata.get("activities", []))),
        "services_count": float(len(manifest_metadata.get("services", []))),
        "receivers_count": float(len(manifest_metadata.get("receivers", []))),
    }
    feats.update(perm_flags)
    return feats
