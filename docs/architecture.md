# SCAMTRACE AI System Architecture

## Architecture Overview

SCAMTRACE is designed as a modular, decoupled digital forensics system prioritizing offline operation, strict cryptographic integrity, and deterministic explainability.

```mermaid
flowchart TD
    subgraph Evidence Ingestion & Cryptography
        RawEvidence[Evidence Upload / Paste / Bulk] --> Storage[Write-Once Storage: chmod 0444]
        Storage --> Hasher[SHA-256 Hasher]
        Hasher --> Manifest[Case Manifest]
        Manifest --> Audit[Append-Only Hash-Chained Audit Log]
    end

    subgraph Multimodal Analyzers
        Storage --> TextAnalyzer[Text / SMS Analyzer (TF-IDF + LR/SVM)]
        Storage --> URLAnalyzer[Lexical URL Analyzer (RandomForest)]
        Storage --> APKAnalyzer[Static APK Metadata Parser]
        Storage --> ScreenshotAnalyzer[Screenshot Hasher & Metadata]
    end

    subgraph Forensic Graph & Correlation
        TextAnalyzer & URLAnalyzer & APKAnalyzer --> EntityExtractor[Entity Extractor & Normalizer]
        EntityExtractor --> CorrelationEngine[Deterministic Rule Engine (10 Rules)]
        CorrelationEngine --> KnowledgeGraph[NetworkX Knowledge Graph]
        KnowledgeGraph --> CytoscapeSerializer[Cytoscape.js Serializer]
    end

    subgraph Incident Reconstruction & Risk
        EntityExtractor --> TimelineBuilder[Timeline Reconstruction & Conflict Engine]
        CorrelationEngine & TextAnalyzer & URLAnalyzer & APKAnalyzer --> RiskScorer[Factorized Risk Scoring Engine]
    end

    subgraph Output & Reporting
        KnowledgeGraph & TimelineBuilder & RiskScorer & Audit --> ReportGenerator[Jinja2 Report Generator]
        ReportGenerator --> HTMLReport[Audited HTML Report]
        ReportGenerator --> JSONReport[Traceable JSON Report]
        HTMLReport & JSONReport -.-> CitationValidator{Strict Citation Validator}
    end
```

## Component Architecture

1. **Ingestion & Integrity Engine**
   - Direct hashing of incoming bytes (UTF-8 encoding enforced for pasted text).
   - Write-once storage layout: `storage/cases/{case_id}/evidence/{evidence_id}/original.{ext}`.
   - Filesystem write guards (`0444` read-only attribute).
   - Manifest hash recalculation per mutation.
   - Cryptographic audit block chaining: `entry_hash = SHA256(seq, timestamp, actor, action, payload, prev_hash)`.

2. **Analyzer Suite (100% Offline)**
   - Isolated analyzer implementations implementing `BaseAnalyzer`.
   - Feature weights extracted directly from model coefficients / trees for explainability.
   - Zero external socket/network calls.

3. **Entity Extraction & Canonical Normalization**
   - Extraction of phones, URLs, domains, UPI handles, APK packages, certificate hashes, amounts, and dates.
   - Robust normalization (e.g. `+91` E.164 standardization, URL canonicalization, eTLD+1 extraction).

4. **Deterministic Correlation Engine**
   - 10 pure-function rule implementations.
   - Configurable rule toggle switches for ablation studies.
   - Attributed edges containing human-readable rationale and triggering entities.

5. **Timeline Reconstruction**
   - Multi-format source timestamp parsing with explicit source attribution (`embedded`, `user_entered`, `none`).
   - Causal sequencing conflict detection (e.g. install before lure URL).

6. **Factorized Risk Scoring**
   - Transparent weighted linear model separating artifact risk from confirmed correlation topologies.
   - Strict exclusion of temporal proximity from confirmed link credit.

7. **Forensic Reporting & Citation Enforcement**
   - Strict schema enforcement: all factual narrative assertions must be bound to concrete evidence IDs (`E1`, `E2`, etc.).

