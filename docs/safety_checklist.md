# Safety and Ethics Compliance Checklist

This document tracks strict enforcement of the non-negotiable safety rules outlined in Section 2 of the SCAMTRACE specification.

- [x] **1. Never execute APK files.**
  - *Enforcement*: `backend/app/analyzers/apk.py` uses `zipfile` and XML parsing strictly to read `AndroidManifest.xml` and inspect `META-INF` certificate fingerprints. No emulator, Dalvik/ART runtime, adb invocation, or process execution of any kind is ever triggered.

- [x] **2. Never make network requests from analyzers.**
  - *Enforcement*: Analyzers (`sms.py`, `url.py`, `apk.py`, `text.py`, `screenshot.py`) perform purely offline computation. URL analysis relies strictly on lexical heuristics and static token matching. Suffix parsing uses offline rules. `httpx` or `requests` are only allowed within test suites against the local FastAPI test client (`TestClient`), never inside analyzer logic.

- [x] **3. Malicious samples restricted.**
  - *Enforcement*: `data/samples_restricted/` is added to `.gitignore` and marked read-only with a protective README. No malicious live payloads are committed to source control.

- [x] **4. Synthetic data sanitization.**
  - *Enforcement*: Generator script `experiments/generate_synthetic.py` strictly restricts synthetic data generation to reserved formats:
    - Phone numbers: strictly in the `+91 99999 00000` to `+91 99999 99999` range.
    - UPI handles: use `@fakebank` or fictional bank identifiers.
    - Domains: strictly use the reserved RFC 2606 `.test` top-level domain.
    - Bank names and entities are purely fictional.

- [x] **5. Zero real personal data storage or scraping.**
  - *Enforcement*: No web scrapers, crawler modules, or external identity APIs exist in the codebase. All tests operate strictly on synthetic fixtures.

- [x] **6. Report limitations and forensic boundaries.**
  - *Enforcement*: The reporting engine (`backend/app/reporting/generator.py` and Jinja2 templates) forces a mandatory disclaimer section stating that outputs are investigative decision-support aids, not definitive legal evidence, and lists all known algorithmic limitations.

