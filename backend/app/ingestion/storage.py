"""Evidence storage and ingestion module for SCAMTRACE AI.
Handles write-once immutable file storage, SHA-256 computation,
mime/type detection, and timestamp parsing.
"""
import datetime
import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config import CASES_DIR, STORAGE_DIR

# Accepted evidence types
EVIDENCE_TYPES = {"sms", "chat", "url", "apk", "screenshot", "email_text"}

# Common timestamp formats (ISO and Indian regional formats)
TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d/%m/%y %H:%M:%S",
    "%d/%m/%y %H:%M",
    "%d-%m-%y %H:%M:%S",
    "%d-%m-%y %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
]


def compute_sha256(data: bytes) -> str:
    """Compute the SHA-256 hexadecimal digest of the given bytes."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()


def detect_evidence_type(
    filename: Optional[str],
    content_bytes: bytes,
    hint_text: Optional[str] = None
) -> str:
    """Detect evidence type using file extensions, magic bytes, and content hints."""
    ext = Path(filename).suffix.lower() if filename else ""

    # Magic byte checks
    if ext == ".apk" or (content_bytes.startswith(b"PK\x03\x04") and b"AndroidManifest.xml" in content_bytes[:4096]):
        return "apk"

    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} or (
        content_bytes.startswith(b"\x89PNG\r\n\x1a\n") or
        content_bytes.startswith(b"\xff\xd8\xff") or
        (content_bytes.startswith(b"RIFF") and b"WEBP" in content_bytes[:16])
    ):
        return "screenshot"

    text = hint_text or ""
    if not text and content_bytes:
        try:
            text = content_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            text = ""

    # Check for URL
    if text:
        url_pattern = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
        if url_pattern.match(text) and "\n" not in text:
            return "url"

        # Call log or voice call transcript
        if re.search(r"^(Call from|Incoming call|Call transcript|Audio call|Voice call):", text, re.IGNORECASE):
            return "phone_call"

        # Email headers
        if re.search(r"^(From|To|Subject|Date):", text, re.MULTILINE):
            return "email_text"

        # Chat patterns (e.g. timestamps or [Name]: or +91...)
        if re.search(r"(\[\d{1,2}:\d{2}\]|\b\w+:\s|\+\d{10,12}:)", text):
            return "chat"

    return "sms"


def parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime.datetime]:
    """Parse timestamp strings using ISO 8601 or common Indian regional formats."""
    if not timestamp_str or not timestamp_str.strip():
        return None

    cleaned = timestamp_str.strip()
    # Replace timezone offset with standard format if simple +05:30 style
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    # Fallback using dateutil if available
    try:
        from dateutil import parser
        return parser.parse(cleaned)
    except Exception:
        return None


def store_evidence_file(
    case_id: str,
    evidence_id: str,
    file_bytes: bytes,
    extension: str
) -> Tuple[Path, str, int]:
    """Write evidence file to storage with write-once immutable semantics (chmod 0444).

    Returns:
        Tuple of (stored_path, sha256_hash, size_bytes)
    Raises:
        FileExistsError: If a file already exists at the target path.
    """
    ext = extension.lstrip(".")
    if not ext:
        ext = "bin"

    evidence_dir = CASES_DIR / case_id / "evidence" / evidence_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    target_path = evidence_dir / f"original.{ext}"

    if target_path.exists():
        raise FileExistsError(f"Evidence file already exists at: {target_path}")

    # Compute SHA-256
    sha256 = compute_sha256(file_bytes)
    size_bytes = len(file_bytes)

    # Write file
    with open(target_path, "wb") as f:
        f.write(file_bytes)

    # Set read-only permissions (chmod 0444 / S_IREAD)
    try:
        os.chmod(target_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except Exception:
        pass

    return target_path, sha256, size_bytes

