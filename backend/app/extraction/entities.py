"""Entity extraction and normalization engine for SCAMTRACE AI.
Extracts phone numbers, URLs, domains, UPI handles, APK packages,
certificate fingerprints, amounts, datetimes, brands, and sender IDs with exact text spans.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.app.extraction.brands import match_brand, is_official_domain_for_brand, BRAND_ALIASES
from backend.app.extraction.normalize import (
    extract_domain_and_host,
    normalize_amount,
    normalize_apk_package,
    normalize_cert_hash,
    normalize_phone,
    normalize_upi_handle,
    normalize_url,
)
from backend.app.ingestion.storage import parse_timestamp


@dataclass
class ExtractedEntity:
    entity_type: str  # phone, url, domain, upi_handle, apk_package, cert_sha256, amount, datetime, brand, sender_id
    value: str        # normalized value
    raw_value: str
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "value": self.value,
            "raw_value": self.raw_value,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "metadata": self.metadata,
        }


# Regular expressions for entity patterns
PHONE_PATTERN = re.compile(
    r"(?:(?:\+91|0)[\s\-]?)?(?:[6-9]\d{4}|99999)[\s\-]?\d{5}\b"
)

URL_PATTERN = re.compile(
    r"(https?://[^\s<>\"]+|www\.[^\s<>\"]+)",
    re.IGNORECASE
)

UPI_HANDLE_PATTERN = re.compile(
    r"\b([a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,})\b"
)

AMOUNT_PATTERN = re.compile(
    r"(?:Rs\.?|INR|₹)\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)\b",
    re.IGNORECASE
)

SENDER_ID_PATTERN = re.compile(
    r"\b([A-Z]{2}-[A-Za-z0-9]{3,9})\b"
)

PACKAGE_PATTERN = re.compile(
    r"\b([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,})\b"
)

CERT_SHA256_PATTERN = re.compile(
    r"\b([0-9a-fA-F]{64})\b"
)

DATE_PATTERN = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?)\b"
)


def extract_entities_from_text(text: str) -> List[ExtractedEntity]:
    """Extract all forensic entities with accurate character spans from text."""
    if not text:
        return []

    entities: List[ExtractedEntity] = []

    # 1. Phone Numbers (spaced, contiguous, +91, 0-prefix)
    for m in PHONE_PATTERN.finditer(text):
        raw_val = m.group(0)
        norm = normalize_phone(raw_val)
        if norm:
            entities.append(ExtractedEntity(
                entity_type="phone",
                value=norm,
                raw_value=raw_val,
                span_start=m.start(),
                span_end=m.end(),
            ))

    # 2. URLs and Domains
    for m in URL_PATTERN.finditer(text):
        raw_val = m.group(0)
        norm_u = normalize_url(raw_val)
        host, reg_dom = extract_domain_and_host(norm_u)

        entities.append(ExtractedEntity(
            entity_type="url",
            value=norm_u,
            raw_value=raw_val,
            span_start=m.start(),
            span_end=m.end(),
            metadata={"host": host, "registered_domain": reg_dom}
        ))

        # Also register the domain entity
        if reg_dom:
            entities.append(ExtractedEntity(
                entity_type="domain",
                value=reg_dom,
                raw_value=reg_dom,
                span_start=m.start(),
                span_end=m.end(),
                metadata={"host": host}
            ))

    # 3. Sender IDs (e.g. AD-EXAMPLEBK)
    for m in SENDER_ID_PATTERN.finditer(text):
        raw_val = m.group(0)
        entities.append(ExtractedEntity(
            entity_type="sender_id",
            value=raw_val.upper(),
            raw_value=raw_val,
            span_start=m.start(),
            span_end=m.end(),
        ))

    # 4. UPI Handles
    for m in UPI_HANDLE_PATTERN.finditer(text):
        raw_val = m.group(0)
        # Avoid standard web emails if suffix contains dot (e.g. user@site.com) unless fakebank/upi
        domain_part = raw_val.split("@")[-1]
        if "." not in domain_part or "bank" in domain_part or "upi" in domain_part:
            entities.append(ExtractedEntity(
                entity_type="upi_handle",
                value=normalize_upi_handle(raw_val),
                raw_value=raw_val,
                span_start=m.start(),
                span_end=m.end(),
            ))

    # 5. Currency Amounts
    for m in AMOUNT_PATTERN.finditer(text):
        raw_val = m.group(0)
        num_val = normalize_amount(raw_val)
        if num_val is not None:
            entities.append(ExtractedEntity(
                entity_type="amount",
                value=f"INR {num_val:,.2f}",
                raw_value=raw_val,
                span_start=m.start(),
                span_end=m.end(),
                metadata={"numeric_value": num_val}
            ))

    # 6. Dates and Timestamps
    for m in DATE_PATTERN.finditer(text):
        raw_val = m.group(0)
        parsed_dt = parse_timestamp(raw_val)
        if parsed_dt:
            iso_val = parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            entities.append(ExtractedEntity(
                entity_type="datetime",
                value=iso_val,
                raw_value=raw_val,
                span_start=m.start(),
                span_end=m.end(),
            ))

    # 7. Brands
    text_lower = text.lower()
    for alias, canonical in sorted(BRAND_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            raw_val = text[m.start():m.end()]
            entities.append(ExtractedEntity(
                entity_type="brand",
                value=canonical,
                raw_value=raw_val,
                span_start=m.start(),
                span_end=m.end(),
                metadata={"canonical": canonical}
            ))

    # 8. Certificate SHA-256
    for m in CERT_SHA256_PATTERN.finditer(text):
        raw_val = m.group(0)
        entities.append(ExtractedEntity(
            entity_type="cert_sha256",
            value=normalize_cert_hash(raw_val),
            raw_value=raw_val,
            span_start=m.start(),
            span_end=m.end(),
        ))

    # Deduplicate entities by (entity_type, value, span_start)
    unique_entities = []
    seen = set()
    for ent in entities:
        key = (ent.entity_type, ent.value, ent.span_start)
        if key not in seen:
            seen.add(key)
            unique_entities.append(ent)

    return unique_entities


def extract_entities_from_apk(metadata: Dict[str, Any]) -> List[ExtractedEntity]:
    """Extract package name, certificate hash, and permissions from APK metadata."""
    entities = []

    pkg = metadata.get("package_name")
    if pkg and pkg != "unknown.apk.package":
        entities.append(ExtractedEntity(
            entity_type="apk_package",
            value=normalize_apk_package(pkg),
            raw_value=pkg,
            span_start=None,
            span_end=None,
        ))

    cert = metadata.get("cert_sha256")
    if cert and len(cert) == 64:
        entities.append(ExtractedEntity(
            entity_type="cert_sha256",
            value=normalize_cert_hash(cert),
            raw_value=cert,
            span_start=None,
            span_end=None,
        ))

    return entities

