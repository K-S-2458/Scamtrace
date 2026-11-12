# Architectural Decisions Record (ADR)

## DEC-001: Technology Stack and Runtime Environment
- **Date**: 2026-11-11
- **Options**:
  - Python 3.11 with FastAPI / SQLAlchemy / NetworkX vs Django / Node.js
  - SQLite vs PostgreSQL vs Neo4j
- **Choice**: Python 3.13 (compatible with 3.11+ specs), FastAPI, SQLAlchemy 2.x with SQLite, NetworkX, scikit-learn.
- **Reason**: Single-user local forensic investigation tool. SQLite provides zero-configuration, atomic local storage, and file-based portability. NetworkX satisfies in-memory graph queries and serialization without external daemon dependencies like Neo4j.

## DEC-002: Deferred Graph Neural Networks (GNN) and Neo4j
- **Date**: 2026-11-11
- **Options**: Neo4j graph database / PyTorch Geometric GNN vs NetworkX with deterministic rule engine.
- **Choice**: NetworkX with explicit rule-based correlation engine.
- **Reason**: Digital forensics in legal and investigative contexts requires strict deterministic traceability and auditability. Rule-based correlation ensures every link has a known, inspectable trigger condition, threshold, and supporting fields. GNN and external graph databases add operational complexity and non-transparent link heuristics inappropriate for the MVP.

## DEC-003: Exclusion of External LLM APIs and RAG
- **Date**: 2026-11-11
- **Options**: OpenAI / Claude API / local Ollama RAG vs Jinja2 template-based forensic report generator.
- **Choice**: Jinja2 structured template generation with mandatory evidence citation validation.
- **Reason**: Hallucination cannot be tolerated in forensic reporting. Every factual claim, correlation, and risk factor must strictly cite verified evidence IDs (E1, E2, etc.). Template-based generation guarantees determinism, citation enforcement, and offline operation without API fees or network requirements.

## DEC-004: Purely Offline Lexical URL Analysis
- **Date**: 2026-11-11
- **Options**: Live WHOIS/DNS/HTTP redirect resolution vs Purely lexical offline feature extraction with optional user-supplied domain age.
- **Choice**: Strict offline lexical analysis (length, token counts, entropy, brand matching, suspicious TLDs, keyword matching).
- **Reason**: Safety Rule #2 strictly prohibits active probing, DNS lookups, or HTTP requests to avoid triggering honeypots, tipping off scam operators, or executing malicious redirects.

## DEC-005: Static Metadata-Only APK Analysis & Parser Fallback
- **Date**: 2026-11-11
- **Options**: Full dynamic sandbox execution vs Androguard vs Minimal zipfile/xml.etree static manifest parser.
- **Choice**: Static parsing via `zipfile` and `xml.etree` (supporting decoded manifests or extracted XML/metadata) without ever executing APK bytecode.
- **Reason**: Safety Rule #1 dictates APK files must never be executed or installed. Static inspection of permissions, SDK versions, package name, and certificate SHA-256 provides sufficient forensic signal for triage while ensuring investigator safety.

## DEC-006: Deferred Transformer Models (IndicBERT / MuRIL)
- **Date**: 2026-11-11
- **Options**: Heavy transformer models (IndicBERT, MuRIL, BERT) vs TF-IDF + Logistic Regression / Linear SVM with n-gram feature weight explanations.
- **Choice**: TF-IDF (word 1-2 grams, char 3-5 grams) + Logistic Regression / Linear SVM.
- **Reason**: High inference speed, zero GPU requirement, transparent linear model explanations (coefficients * TF-IDF weights) that allow investigators to see exact character/word n-gram contributions directly. Transformers will only be evaluated if baseline linear models exhibit unacceptable error margins on development benchmarks.

## DEC-007: Domain Extraction & Offline Suffix Handling
- **Date**: 2026-11-11
- **Options**: Online `tldextract` snapshot vs Bundled static multi-part suffix parser.
- **Choice**: Robust offline suffix parser utilizing standard two-part TLD patterns (.co.in, .com, .test, .org, .net, .gov.in, etc.) and fallback registered domain extraction without network calls.
- **Reason**: Ensures 100% offline determinism and prevents network socket calls during test and analysis phases.

## DEC-008: Temporal Proximity Weighting Exclusion
- **Date**: 2026-11-11
- **Options**: Treat temporal proximity as a primary correlation link vs Auxiliary link only.
- **Choice**: TEMPORAL_PROXIMITY confidence is set to 0.2 and explicitly excluded from the "confirmed link" count in the risk scoring engine.
- **Reason**: Temporal closeness alone is circumstantial; coincidence must not artificially inflate a case's risk score unless corroborated by entity overlap (shared phone, domain, UPI handle, or APK lure).

## DEC-009: Interactive Evidence Correlation Matrix as Primary Relationship Interface
- **Date**: 2026-11-12
- **Options**: Cytoscape force-directed network graph as sole relationship view vs Interactive pairwise Evidence Correlation Matrix with side drawer inspector.
- **Choice**: Evidence Correlation Matrix as primary relationship interface; Cytoscape network graph retained as secondary toggleable view.
- **Reason**: Complex force-directed network graphs can become cluttered and difficult to inspect as artifact count grows. A pairwise correlation matrix provides an intuitive, sortable grid with restrained strength indicators (`Strong`, `Possible`, `Weak`, `—`) and immediate side-panel inspection showing shared entities, correlation rules, and plain-language explanations.

## DEC-010: Multi-Tier Investigation Findings & Three-Tier Conclusions
- **Date**: 2026-11-12
- **Options**: Monolithic conclusion summary vs Rigorous three-tier categorization (Confirmed Observations, System Inferences, Unverified Possibilities).
- **Choice**: Deterministic compilation of 7 entity categories (phones, domains, UPI, packages, cert hashes, brands, amounts), rule-attributed key findings, and three-tier conclusions.
- **Reason**: Forensic integrity requires explicit boundaries between verifiable facts (unbroken SHA-256 hashes, exact entity equality across artifacts), algorithmic heuristics (brand impersonation, dropper sequence patterns), and external unknowns (legal ownership, CDR/IPDR subscriber identities).


