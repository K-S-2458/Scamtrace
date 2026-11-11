"""Training script for Static APK Metadata Scam/Malware Classifier.
Extracts static manifest features (requested permissions, components, SDK targets).
Trains Random Forest over 5 seeds.
Saves model and metrics.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import joblib
import numpy as np
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

from backend.app.config import APK_SUSPICIOUS_PERMISSIONS
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
SYNTHETIC_APK_FILE = ROOT_DIR / "data" / "synthetic" / "apk_dataset.json"
SPLITS_FILE = ROOT_DIR / "data" / "splits" / "apk_splits.json"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


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
    """Train Random Forest (primary) and Logistic Regression (baseline) across 5 seeds."""
    with open(SYNTHETIC_APK_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    with open(SPLITS_FILE, "r", encoding="utf-8") as f:
        splits = json.load(f)

    id_to_record = {r["id"]: r for r in records}
    train_dev_ids = splits["train"] + splits["dev"]

    X_list = []
    y_list = []
    for rid in train_dev_ids:
        rec = id_to_record[rid]
        feats = extract_apk_features(rec)
        X_list.append([feats[name] for name in APK_FEATURE_NAMES])
        y_list.append(rec["label"])

    X = np.array(X_list)
    y = np.array(y_list)

    rf_seed_metrics = []
    lr_seed_metrics = []

    print(f"Training APK models across 5 seeds on development set...")
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
    model_path = ARTIFACTS_DIR / "apk_model.joblib"
    joblib.dump({
        "model": final_rf,
        "feature_names": APK_FEATURE_NAMES,
    }, model_path)
    print(f"Saved primary APK model to {model_path}")

    metrics_summary = {
        "dataset_type": "synthetic_apk",
        "is_synthetic": True,
        "seeds": seeds,
        "random_forest": rf_seed_metrics,
        "logistic_regression": lr_seed_metrics,
    }

    metrics_path = ARTIFACTS_DIR / "apk_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"Saved APK metrics to {metrics_path}")

    return metrics_summary


if __name__ == "__main__":
    train_and_evaluate()

