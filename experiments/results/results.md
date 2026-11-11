# SCAMTRACE AI Experimental Results & Benchmark Summary

> [!NOTE]
> All evaluations below were executed against sanitized synthetic datasets (`data/synthetic/`) across fixed seeds.
> Zero dynamic execution of APKs or live network lookups were performed. Provable data integrity is documented in `data/data_log.md`.

## 1. Classifier Performance on Sealed Test Splits (5 Seeds: 42–46)

### SMS Text Analysis (LinearSVM vs Logistic Regression)
| Model | Precision (Mean) | Recall (Mean) | F1-Score (Mean) | ROC-AUC (Mean) | FPR (Mean) |
|---|---|---|---|---|---|
| LinearSVM | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| LogisticRegression | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |

### URL Lexical Analysis (Random Forest vs Logistic Regression)
| Model | Precision (Mean) | Recall (Mean) | F1-Score (Mean) | ROC-AUC (Mean) | FPR (Mean) |
|---|---|---|---|---|---|
| LogisticRegression | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| RandomForest | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |

### APK Static Manifest Analysis (Random Forest vs Logistic Regression)
| Model | Precision (Mean) | Recall (Mean) | F1-Score (Mean) | ROC-AUC (Mean) | FPR (Mean) |
|---|---|---|---|---|---|
| LogisticRegression | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| RandomForest | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |

## 2. Correlation Rule Ablation Study
Evaluates the impact of dropping each rule from the 10-rule deterministic correlation engine against gold-standard incident ground truth.

| Rule Disabled | Link Precision | Link Recall | Link F1 |
|---|---|---|---|
| `none (baseline)` | 0.8889 | 0.8889 | 0.8889 |
| `SHARED_PHONE` | 0.875 | 0.7778 | 0.8235 |
| `SHARED_DOMAIN` | 1.0 | 0.6667 | 0.8 |
| `URL_HOST_MATCH` | 0.875 | 0.7778 | 0.8235 |
| `REDIRECT_CHAIN` | 0.8889 | 0.8889 | 0.8889 |
| `SIMILAR_TEXT_TEMPLATE` | 0.8889 | 0.8889 | 0.8889 |
| `SAME_BRAND_IMPERSONATION` | 0.8333 | 0.5556 | 0.6667 |
| `APK_LURE_PATTERN` | 0.875 | 0.7778 | 0.8235 |
| `SAME_CERT_HASH` | 0.8889 | 0.8889 | 0.8889 |
| `SAME_UPI_HANDLE` | 0.8889 | 0.8889 | 0.8889 |
| `TEMPORAL_PROXIMITY` | 0.8889 | 0.8889 | 0.8889 |

## 3. Cryptographic Integrity & Tamper Detection
Tamper simulation across five attack vectors against SHA-256 evidence digests and append-only hash chains.

| Tamper Scenario | Detected (Yes/No) | False Alarms on Untouched Data |
|---|---|---|
| `untouched_baseline` | **NO** | 0 |
| `modify_evidence_byte` | **YES** | 0 |
| `edit_audit_payload` | **YES** | 0 |
| `delete_audit_entry` | **YES** | 0 |
| `swap_audit_entries` | **YES** | 0 |
| `delete_evidence_file` | **YES** | 0 |

## 4. Explanation Faithfulness Evaluation
Tests feature attribution faithfulness by masking the top-attributed feature and measuring score decrease or class flip.

| Analyzer | Suspicious Samples | Label Flipped / Score Decreased | Faithfulness Score | Target (> 0.70) |
|---|---|---|---|---|
| SMS (Text) | 24 | 24 | **1.0** | PASS (> 0.70) |
| URL (Lexical) | 50 | 50 | **1.0** | PASS (> 0.70) |
| APK (Static Manifest) | 35 | 35 | **1.0** | PASS (> 0.70) |
