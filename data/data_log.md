# Data Log and Provenance Record

This file records all datasets used in SCAMTRACE AI, their provenance, license, file hashes, and generation details.

## Real Datasets (Held in data/raw/ - Read-Only, Never Committed)

| Dataset Name | Source URL | Version | License | Download Date | File SHA-256 | Notes |
|---|---|---|---|---|---|---|
| SMS Spam Collection | https://archive.ics.uci.edu/dataset/228/sms+spam+collection | 1.0 | CC BY 4.0 | N/A (Optional) | Pending verification if downloaded | UCI Repository benchmark |
| URLhaus Recent Database | https://urlhaus.abuse.ch/api/ | Snapshot | CC0 | N/A (Optional) | Pending verification if downloaded | Lexical feature extraction only |
| CIC-AndMal2017 Pre-extracted | https://www.unb.ca/cic/datasets/andmal2017.html | 2017 | Academic use | N/A (Optional) | Pending verification if downloaded | Static permissions & intents only |

*Note: In accordance with Rule 5, when real datasets are not present in `data/raw/`, all training and evaluation falls back strictly to the synthetic generator and all resulting figures are explicitly marked as synthetic.*

## Synthetic Datasets (Generated via experiments/generate_synthetic.py)

| Dataset Name | Generator Script | Generator Version | Base Seed | Generation Date | Scope / Records | File SHA-256 |
|---|---|---|---|---|---|---|
| Synthetic SMS Corpus | experiments/generate_synthetic.py | 1.0.0 | 42 | 2026-11-11 | Train, Dev, Test splits of KYC/phishing/benign SMS | Computed at generation |
| Synthetic URL Corpus | experiments/generate_synthetic.py | 1.0.0 | 42 | 2026-11-11 | Train, Dev, Test splits of phishing/benign URLs with held-out templates | Computed at generation |
| Synthetic APK Metadata | experiments/generate_synthetic.py | 1.0.0 | 42 | 2026-11-11 | Train, Dev, Test splits of malicious/benign Android manifests | Computed at generation |
| Synthetic Example Incident | experiments/generate_synthetic.py | 1.0.0 | 42 | 2026-11-11 | 5 evidence items (E1 to E5) for end-to-end testing | Fixed fixture |

*Safety Compliance Note*: Synthetic data strictly avoids real telephone numbers (using reserved `+91 99999 XXXXX` range), fake UPI handles (`*@fakebank`), and reserved `.test` domain names in strict adherence to Safety Rule 4.

