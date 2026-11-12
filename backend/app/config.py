"""SCAMTRACE configuration module.
Contains all paths, thresholds, weights, and feature flags.
"""
from pathlib import Path
from typing import Dict, List

# Base Directories
import os
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
# Support Vercel and serverless read-only filesystems by routing storage to /tmp
if os.environ.get("VERCEL"):
    STORAGE_DIR = Path("/tmp/storage")
else:
    STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", str(ROOT_DIR / "storage")))
CASES_DIR = STORAGE_DIR / "cases"
DATABASE_PATH = STORAGE_DIR / "scamtrace.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# Ingestion constraints
MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB default limit

# Suspicious permissions for Android APK static triage
APK_SUSPICIOUS_PERMISSIONS: List[str] = [
    "android.permission.SEND_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.READ_SMS",
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.READ_CONTACTS",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.RECEIVE_BOOT_COMPLETED",
    "android.permission.CALL_PHONE",
    "android.permission.RECORD_AUDIO",
    "android.permission.CAMERA",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_PHONE_STATE",
]

# High-risk permissions specifically examined for lure correlation
APK_HIGH_RISK_LURE_PERMS: List[str] = [
    "READ_SMS",
    "SEND_SMS",
    "RECEIVE_SMS",
    "BIND_ACCESSIBILITY_SERVICE",
    "REQUEST_INSTALL_PACKAGES",
]

# Known suspicious TLDs for offline lexical URL analysis
SUSPICIOUS_TLDS: List[str] = [
    ".test",  # Synthetic domain test environment
    ".xyz",
    ".top",
    ".club",
    ".work",
    ".click",
    ".link",
    ".live",
    ".online",
    ".site",
    ".icu",
    ".buzz",
    ".monster",
    ".app",
]

# Lure & KYC Keywords for URL analysis
LURE_KEYWORDS: List[str] = [
    "kyc",
    "update",
    "verify",
    "secure",
    "login",
    "bank",
    "refund",
    "upi",
    "otp",
    "reward",
    "support",
    "account",
    "claim",
    "bonus",
]

# Correlation Thresholds and Windows
SIMILARITY_THRESHOLD: float = 0.75  # TF-IDF cosine threshold
TEMPORAL_WINDOW_MINUTES: int = 30   # Temporal proximity window
ORDERING_TOLERANCE_MINUTES: int = 2 # Tolerance window for chronological conflict

# Risk Scoring Weights (sum to 1.0)
WEIGHT_ARTIFACT: float = 0.40
WEIGHT_CORRELATION: float = 0.40
WEIGHT_PATTERN: float = 0.20

# Artifact Analyzer Weights
ARTIFACT_TYPE_WEIGHTS: Dict[str, float] = {
    "sms": 0.25,
    "chat": 0.25,
    "url": 0.30,
    "apk": 0.35,
    "email_text": 0.25,
    "screenshot": 0.10,
}

# Correlation Rule Switches (for ablation studies)
CORRELATION_RULE_SWITCHES: Dict[str, bool] = {
    "SHARED_PHONE": True,
    "SHARED_DOMAIN": True,
    "URL_HOST_MATCH": True,
    "REDIRECT_CHAIN": True,
    "SIMILAR_TEXT_TEMPLATE": True,
    "SAME_BRAND_IMPERSONATION": True,
    "APK_LURE_PATTERN": True,
    "SAME_CERT_HASH": True,
    "SAME_UPI_HANDLE": True,
    "TEMPORAL_PROXIMITY": True,
}

