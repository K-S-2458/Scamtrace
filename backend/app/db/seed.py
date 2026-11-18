"""Default demo investigation cases seeding module for SCAMTRACE AI.
Ensures standard forensic investigation scenarios are pre-seeded and always available.
"""
import datetime
import json
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.config import CASES_DIR
from backend.app.db.models import Analysis, Case, Edge, Entity, Evidence
from backend.app.analyzers import get_analyzer
from backend.app.correlation.engine import correlate_case
from backend.app.extraction.entities import extract_entities_from_text, extract_entities_from_apk
from backend.app.ingestion.storage import compute_sha256, store_evidence_file
from backend.app.integrity.manifest import generate_manifest


def seed_default_cases(db: Session) -> None:
    """Seed standard demo cases if they do not already exist."""
    existing_case_ids = {c.id for c in db.query(Case.id).all()}

    # Preset 1: Simple Banking Smishing (SMS + Phishing URL)
    if "CASE-SMISHING-01" not in existing_case_ids:
        _seed_smishing_case(db)

    # Preset 2: Vishing Phone Call & Remote Access APK
    if "CASE-VISHING-02" not in existing_case_ids:
        _seed_vishing_case(db)

    # Preset 3: Comprehensive 4-Tier Multimodal Campaign
    if "CASE-CAMPAIGN-03" not in existing_case_ids:
        _seed_multimodal_campaign(db)


def _seed_smishing_case(db: Session) -> Case:
    case_id = "CASE-SMISHING-01"
    case = Case(
        id=case_id,
        title="Simple Banking Smishing Incident",
        description="Minimal 2-artifact case: SMS KYC suspension threat referencing a spoofed phishing domain.",
        status="open",
        created_at=datetime.datetime.utcnow(),
    )
    db.add(case)
    db.commit()

    case_dir = CASES_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    # E1: SMS
    sms_text = "URGENT: Your Example Bank account has been restricted due to expired KYC. Update immediately at https://login.example-bank-secure.test or call +91 99999 00001."
    _ingest_and_analyze(
        db=db,
        case_id=case_id,
        evidence_id="E1",
        text=sms_text,
        ev_type="sms",
        filename="E1_smishing_sms.txt",
        source_ts_str="2026-03-10 10:00:00",
    )

    # E2: Phishing URL
    url_text = "https://login.example-bank-secure.test/verify-kyc?utm_source=sms"
    _ingest_and_analyze(
        db=db,
        case_id=case_id,
        evidence_id="E2",
        text=url_text,
        ev_type="url",
        filename="E2_phishing_link.txt",
        source_ts_str="2026-03-10 10:05:00",
    )

    correlate_case(db, case_id, persist=True)
    generate_manifest(case_id, db)
    return case


def _seed_vishing_case(db: Session) -> Case:
    case_id = "CASE-VISHING-02"
    case = Case(
        id=case_id,
        title="Vishing Phone Call & Remote Access APK",
        description="Voice social engineering incident: scammer calls victim and commands installation of privileged remote helper APK.",
        status="open",
        created_at=datetime.datetime.utcnow(),
    )
    db.add(case)
    db.commit()

    case_dir = CASES_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    # E1: Phone call
    call_text = (
        "Call from: +91 99999 00001\n"
        "Caller claimed to be Example Bank fraud manager: "
        "\"Your debit card has unauthorized international transactions. Install our official quick-support safety app immediately to block charges.\""
    )
    _ingest_and_analyze(
        db=db,
        case_id=case_id,
        evidence_id="E1",
        text=call_text,
        ev_type="phone_call",
        filename="E1_support_call.txt",
        source_ts_str="2026-03-10 11:00:00",
    )

    # E2: APK Metadata
    apk_meta = {
        "package_name": "com.examplebank.safetyapp",
        "min_sdk": 24,
        "target_sdk": 33,
        "requested_permissions": [
            "android.permission.INTERNET",
            "android.permission.READ_SMS",
            "android.permission.SEND_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.BIND_ACCESSIBILITY_SERVICE",
        ],
        "cert_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
    _ingest_and_analyze(
        db=db,
        case_id=case_id,
        evidence_id="E2",
        text=json.dumps(apk_meta),
        ev_type="apk",
        filename="E2_safety_support.apk",
        source_ts_str="2026-03-10 11:15:00",
    )

    correlate_case(db, case_id, persist=True)
    generate_manifest(case_id, db)
    return case


def _seed_multimodal_campaign(db: Session) -> Case:
    case_id = "CASE-CAMPAIGN-03"
    case = Case(
        id=case_id,
        title="Comprehensive 4-Step Multimodal Campaign",
        description="Full 4-tier campaign investigating cross-channel SMS smishing, WhatsApp dropper lure, phishing harvester, and accessibility-stealing APK.",
        status="open",
        created_at=datetime.datetime.utcnow(),
    )
    db.add(case)
    db.commit()

    case_dir = CASES_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    # E1: SMS
    sms_text = "Your KYC is expiring. Update now at https://kyc-update.example-bank-secure.test/verify to avoid account block. Call +91 99999 00001."
    _ingest_and_analyze(
        db=db,
        case_id=case_id,
        evidence_id="E1",
        text=sms_text,
        ev_type="sms",
        filename="E1_sms.txt",
        source_ts_str="2026-03-10 10:00:00",
    )

    # E2: WhatsApp Chat
    chat_text = "From: +919999900001\nDear customer, complete KYC here: https://kyc-update.example-bank-secure.test/verify and download the app: https://files.example-bank-secure.test/app.apk"
    _ingest_and_analyze(
        db=db,
        case_id=case_id,
        evidence_id="E2",
        text=chat_text,
        ev_type="chat",
        filename="E2_chat.txt",
        source_ts_str="2026-03-10 10:03:00",
    )

    # E3: Phishing URL
    url_text = "https://login.example-bank-secure.test/signin?utm_source=sms"
    _ingest_and_analyze(
        db=db,
        case_id=case_id,
        evidence_id="E3",
        text=url_text,
        ev_type="url",
        filename="E3_url.txt",
        source_ts_str="2026-03-10 10:05:00",
    )

    # E4: Malicious APK
    apk_meta = {
        "package_name": "com.fake.kycupdate",
        "min_sdk": 21,
        "target_sdk": 33,
        "requested_permissions": [
            "android.permission.INTERNET",
            "android.permission.READ_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.BIND_ACCESSIBILITY_SERVICE",
        ],
        "cert_sha256": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef01",
    }
    _ingest_and_analyze(
        db=db,
        case_id=case_id,
        evidence_id="E4",
        text=json.dumps(apk_meta),
        ev_type="apk",
        filename="E4_app.apk",
        source_ts_str="2026-03-10 10:08:00",
    )

    correlate_case(db, case_id, persist=True)
    generate_manifest(case_id, db)
    return case


def _ingest_and_analyze(
    db: Session,
    case_id: str,
    evidence_id: str,
    text: str,
    ev_type: str,
    filename: str,
    source_ts_str: Optional[str] = None,
) -> Evidence:
    raw_bytes = text.encode("utf-8")
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "txt"
    stored_path, sha256_hash, size_bytes = store_evidence_file(
        case_id=case_id,
        evidence_id=evidence_id,
        file_bytes=raw_bytes,
        extension=ext,
    )

    parsed_ts = None
    if source_ts_str:
        try:
            parsed_ts = datetime.datetime.fromisoformat(source_ts_str)
        except Exception:
            pass

    ev = Evidence(
        id=evidence_id,
        case_id=case_id,
        type=ev_type,
        original_filename=filename,
        mime_type="text/plain" if ev_type in {"sms", "chat", "url", "phone_call"} else "application/octet-stream",
        size_bytes=size_bytes,
        sha256=sha256_hash,
        stored_path=str(stored_path),
        uploaded_at=datetime.datetime.utcnow(),
        source_timestamp=parsed_ts,
        timestamp_source="user_entered" if parsed_ts else "none",
        uploader="investigator",
        raw_text=text,
        analysis_status="pending",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Extract entities
    if ev_type == "apk":
        try:
            meta = json.loads(text)
            extracted = extract_entities_from_apk(meta)
        except Exception:
            extracted = []
    else:
        extracted = extract_entities_from_text(text)

    for ent in extracted:
        ent_record = Entity(
            id=str(uuid.uuid4()),
            case_id=case_id,
            evidence_id=evidence_id,
            entity_type=ent.entity_type,
            value=ent.value,
            raw_value=getattr(ent, "raw_value", ent.value) or ent.value,
            span_start=getattr(ent, "span_start", None),
            span_end=getattr(ent, "span_end", None),
        )
        db.add(ent_record)

    # Run analyzer
    analyzer = get_analyzer(ev_type)
    res = analyzer.analyze(raw_bytes=raw_bytes, raw_text=text)

    analysis_record = Analysis(
        id=str(uuid.uuid4()),
        case_id=case_id,
        evidence_id=evidence_id,
        model_name=res.model_name,
        model_version=res.model_version,
        label=res.label,
        score=res.score,
        top_factors=json.dumps(res.top_factors),
        created_at=datetime.datetime.utcnow(),
    )
    db.add(analysis_record)
    ev.analysis_status = "analyzed"
    db.commit()

    return ev
