# Correlation Rules Reference

The SCAMTRACE correlation engine uses explicit, deterministic rules to link evidence items into a knowledge graph. Every generated edge is assigned a link type, confidence score, explanatory reason, and supporting field values.

---

### 1. SHARED_PHONE
- **Trigger**: The exact normalized phone number appears in two distinct evidence items within the same case.
- **Normalization**: Normalized to `+91XXXXXXXXXX` (handles leading 0, bare 10-digit, and `+91` formats).
- **Confidence**: 0.90
- **Reason**: `"Both items contain phone number {value}."`
- **Known False Positive**: Legitimate institutional customer-support hotlines (e.g. telecom or bank helpline numbers quoted in a legitimate verification SMS or forwarding chain).

---

### 2. SHARED_DOMAIN
- **Trigger**: The same registered domain (eTLD+1) appears in a URL entity and a text or URL entity from two distinct evidence items.
- **Normalization**: Lowercase, eTLD+1 extracted using offline suffix mapping.
- **Confidence**: 0.85
- **Reason**: `"Items share registered domain {value}."`
- **Known False Positive**: Public hosting or URL shortener domains (e.g., `bit.ly`, `firebaseapp.com`, `github.io`) where multiple unrelated parties register subdomains.

---

### 3. URL_HOST_MATCH
- **Trigger**: The full URL hostname in item A equals the full hostname in item B.
- **Normalization**: Lowercase, strip default ports (80, 443), trailing slashes.
- **Confidence**: 0.90
- **Reason**: `"Items share identical URL hostname {value}."`
- **Known False Positive**: Shared infrastructure hosts such as content delivery network endpoints or public cloud buckets.

---

### 4. REDIRECT_CHAIN
- **Trigger**: Explicit user-supplied redirect mapping for the case indicates that URL A resolves to domain/URL B.
- **Confidence**: 0.80
- **Reason**: `"Investigator-verified redirection link from {source} to {target}."`
- **Known False Positive**: Stale investigator annotations or misattributed redirect loops.

---

### 5. SIMILAR_TEXT_TEMPLATE
- **Trigger**: Cosine similarity of TF-IDF vectors between two text items from different senders or different sender IDs exceeds `SIMILARITY_THRESHOLD` (config default: 0.75).
- **Confidence**: Set to the computed cosine similarity score, capped at 0.80.
- **Reason**: `"High textual template similarity ({similarity:.2f}) observed between distinct senders."`
- **Known False Positive**: Standard banking transactional boilerplate messages (e.g., "OTP for transaction... Valid for 10 minutes") that share templated language across benign senders.

---

### 6. SAME_BRAND_IMPERSONATION
- **Trigger**: Two or more items reference the same brand name, and at least one item's URL or sender domain is not in that brand's official domain whitelist.
- **Confidence**: 0.60
- **Reason**: `"Both items reference brand '{brand}', with unauthorized/suspicious domain '{domain}'."`
- **Known False Positive**: Legitimate third-party service providers, affiliate partners, or payment gateway domains not present in the curated official domain map.

---

### 7. APK_LURE_PATTERN
- **Trigger**: An APK evidence item and a text or URL evidence item co-exist in the case, where the text/URL item contains download/install keywords (`install`, `download`, `update app`, `apk`) and the APK requests at least one high-risk permission (e.g., `READ_SMS`, `SEND_SMS`, `BIND_ACCESSIBILITY_SERVICE`, `REQUEST_INSTALL_PACKAGES`).
- **Confidence**: 0.70
- **Reason**: `"Text/URL contains lure terminology and APK requests high-risk permissions: {permissions}."`
- **Known False Positive**: Legitimate app distribution notifications (e.g., corporate enterprise MDM enrollment or test builds via link) that require privileged permissions.

---

### 8. SAME_CERT_HASH
- **Trigger**: Two APK evidence items share an identical certificate SHA-256 fingerprint.
- **Confidence**: 0.95
- **Reason**: `"Both APK artifacts were signed using certificate SHA-256 {cert_hash}."`
- **Known False Positive**: Generic or default debug keys used by different developers during prototyping (e.g., Android debug keystore).

---

### 9. SAME_UPI_HANDLE
- **Trigger**: Two evidence items share an identical normalized UPI-style handle (`user@bank`).
- **Confidence**: 0.90
- **Reason**: `"Both items reference identical payment handle {handle}."`
- **Known False Positive**: Common customer care or merchant donation handles posted across multiple forums or messages.

---

### 10. TEMPORAL_PROXIMITY
- **Trigger**: Two evidence items have source timestamps within `TEMPORAL_WINDOW_MINUTES` (config default: 30 minutes).
- **Confidence**: 0.20
- **Reason**: `"Evidence items occurred within {delta_minutes:.1f} minutes of each other."`
- **Known False Positive**: Unrelated scam broadcasts or coincidental spam arriving around the same time window.
- **Critical Policy**: *TEMPORAL_PROXIMITY is strictly excluded from the 'confirmed link' count in risk scoring to prevent temporal coincidence from falsely elevating case severity.*

