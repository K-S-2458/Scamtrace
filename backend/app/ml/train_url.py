"""Training script for Lexical Offline URL Scam/Phishing Classifier.
Extracts 15 purely lexical offline features.
Trains Random Forest (primary) and Logistic Regression (baseline) over 5 seeds.
Saves model, feature medians, and metrics.
"""
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    auc,
    confusion_matrix,
)

from backend.app.config import LURE_KEYWORDS, SUSPICIOUS_TLDS
from backend.app.extraction.brands import match_brand, is_official_domain_for_brand
from backend.app.extraction.normalize import extract_domain_and_host

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
SYNTHETIC_URL_FILE = ROOT_DIR / "data" / "synthetic" / "url_dataset.json"
SPLITS_FILE = ROOT_DIR / "data" / "splits" / "url_splits.json"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_NAMES = [
    "url_length",
    "num_dots",
    "num_hyphens",
    "num_digits",
    "has_at_symbol",
    "is_ip_host",
    "num_subdomains",
    "is_https",
    "is_suspicious_tld",
    "keyword_count",
    "brand_mismatch",
    "has_punycode",
    "path_depth",
    "query_length",
    "domain_age_days",
]


def extract_lexical_url_features(url: str, domain_age_days: Optional[int] = None) -> Dict[str, float]:
    """Extract 15 purely lexical features from a URL without live network lookups."""
    if not url:
        return {f: 0.0 for f in FEATURE_NAMES}

    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned

    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parsed.query or ""

    # Feature 1: URL length
    url_length = float(len(url))

    # Feature 2: Dots
    num_dots = float(url.count("."))

    # Feature 3: Hyphens
    num_hyphens = float(url.count("-"))

    # Feature 4: Digits
    num_digits = float(sum(c.isdigit() for c in url))

    # Feature 5: @ symbol
    has_at_symbol = 1.0 if "@" in url else 0.0

    # Feature 6: IP address as host
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    is_ip_host = 1.0 if ip_pattern.match(host) else 0.0

    # Feature 7: Subdomain count
    _, reg_domain = extract_domain_and_host(cleaned)
    host_parts = host.split(".")
    reg_parts = reg_domain.split(".") if reg_domain else []
    num_subdomains = float(max(0, len(host_parts) - len(reg_parts)))

    # Feature 8: HTTPS
    is_https = 1.0 if cleaned.startswith("https://") else 0.0

    # Feature 9: Suspicious TLD
    is_suspicious_tld = 1.0 if any(host.endswith(tld) for tld in SUSPICIOUS_TLDS) else 0.0

    # Feature 10: Lure / KYC Keywords
    url_lower = url.lower()
    keyword_count = float(sum(1 for kw in LURE_KEYWORDS if kw in url_lower))

    # Feature 11: Brand in non-official domain
    brand_match = match_brand(url_lower)
    brand_mismatch = 0.0
    if brand_match:
        canonical_brand, _ = brand_match
        if not is_official_domain_for_brand(canonical_brand, reg_domain or host):
            brand_mismatch = 1.0

    # Feature 12: Punycode
    has_punycode = 1.0 if "xn--" in host else 0.0

    # Feature 13: Path depth
    segments = [s for s in path.split("/") if s]
    path_depth = float(len(segments))

    # Feature 14: Query length
    query_length = float(len(query))

    # Feature 15: Optional user-supplied domain age
    age = float(domain_age_days) if domain_age_days is not None and domain_age_days >= 0 else 0.0

    return {
        "url_length": url_length,
        "num_dots": num_dots,
        "num_hyphens": num_hyphens,
        "num_digits": num_digits,
        "has_at_symbol": has_at_symbol,
        "is_ip_host": is_ip_host,
        "num_subdomains": num_subdomains,
        "is_https": is_https,
        "is_suspicious_tld": is_suspicious_tld,
        "keyword_count": keyword_count,
        "brand_mismatch": brand_mismatch,
        "has_punycode": has_punycode,
        "path_depth": path_depth,
        "query_length": query_length,
        "domain_age_days": age,
    }


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray, y_scores: np.ndarray) -> Dict[str, float]:
    """Calculate Precision, Recall, F1, ROC-AUC, PR-AUC, FPR."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        roc_auc = float(roc_auc_score(y_true, y_scores))
    except Exception:
        roc_auc = 0.5

    try:
        precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_scores)
        pr_auc = float(auc(recall_curve, precision_curve))
    except Exception:
        pr_auc = 0.0

    return {
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "fpr": fpr,
    }


def train_and_evaluate(seeds: List[int] = [42, 43, 44, 45, 46]) -> Dict[str, Any]:
    """Train Random Forest (primary) and Logistic Regression (baseline) on development split across 5 seeds."""
    with open(SYNTHETIC_URL_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    with open(SPLITS_FILE, "r", encoding="utf-8") as f:
        splits = json.load(f)

    id_to_record = {r["id"]: r for r in records}
    train_dev_ids = splits["train"] + splits["dev"]

    X_list = []
    y_list = []
    for rid in train_dev_ids:
        rec = id_to_record[rid]
        feats = extract_lexical_url_features(rec["url"])
        X_list.append([feats[name] for name in FEATURE_NAMES])
        y_list.append(rec["label"])

    X = np.array(X_list)
    y = np.array(y_list)

    # Compute training medians for explanation contrast
    feature_medians = {name: float(np.median(X[:, i])) for i, name in enumerate(FEATURE_NAMES)}
    with open(ARTIFACTS_DIR / "url_medians.json", "w", encoding="utf-8") as f:
        json.dump(feature_medians, f, indent=2)

    rf_seed_metrics = []
    lr_seed_metrics = []

    print(f"Training URL models across 5 seeds on development set...")
    for seed in seeds:
        # Random Forest (Primary)
        rf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=seed)
        rf.fit(X, y)
        scores_rf = rf.predict_proba(X)[:, 1]
        preds_rf = (scores_rf >= 0.5).astype(int)
        m_rf = evaluate_predictions(y, preds_rf, scores_rf)
        m_rf["seed"] = seed
        m_rf["model"] = "RandomForest"
        rf_seed_metrics.append(m_rf)

        # Logistic Regression (Baseline)
        lr = LogisticRegression(max_iter=1000, random_state=seed)
        lr.fit(X, y)
        scores_lr = lr.predict_proba(X)[:, 1]
        preds_lr = (scores_lr >= 0.5).astype(int)
        m_lr = evaluate_predictions(y, preds_lr, scores_lr)
        m_lr["seed"] = seed
        m_lr["model"] = "LogisticRegression"
        lr_seed_metrics.append(m_lr)

    # Train final model on seed 42
    final_rf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    final_rf.fit(X, y)

    # Save model artifact
    model_path = ARTIFACTS_DIR / "url_model.joblib"
    joblib.dump({
        "model": final_rf,
        "feature_names": FEATURE_NAMES,
        "medians": feature_medians,
    }, model_path)
    print(f"Saved primary URL model to {model_path}")

    metrics_summary = {
        "dataset_type": "synthetic_url",
        "is_synthetic": True,
        "seeds": seeds,
        "random_forest": rf_seed_metrics,
        "logistic_regression": lr_seed_metrics,
    }

    metrics_path = ARTIFACTS_DIR / "url_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"Saved URL metrics to {metrics_path}")

    return metrics_summary


if __name__ == "__main__":
    train_and_evaluate()

