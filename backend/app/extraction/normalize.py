"""Data normalization module for SCAMTRACE AI.
Provides canonical normalization for phones, URLs, domains, UPI handles,
and certificates completely offline.
"""
import re
from typing import Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Common known two-part and multi-part public suffixes for offline eTLD+1 extraction
MULTI_PART_SUFFIXES = {
    "co.in", "com.in", "net.in", "org.in", "gen.in", "ind.in",
    "gov.in", "ac.in", "edu.in", "mil.in", "res.in",
    "co.uk", "org.uk", "gov.uk", "ac.uk",
    "com.au", "net.au", "org.au",
    "co.nz", "org.nz",
}


def normalize_phone(raw_phone: str) -> Optional[str]:
    """Normalize Indian phone numbers to canonical E.164 (+91XXXXXXXXXX) format.

    Handles formats such as:
    - +91 99999 00001 -> +919999900001
    - +91-99999-00001 -> +919999900001
    - 09999900001     -> +919999900001
    - 9999900001      -> +919999900001
    """
    if not raw_phone:
        return None

    # Remove all formatting characters except leading plus
    digits = re.sub(r"[^\d+]", "", raw_phone.strip())

    if digits.startswith("+91"):
        pure_digits = digits[3:]
    elif digits.startswith("91") and len(digits) == 12:
        pure_digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        pure_digits = digits[1:]
    else:
        pure_digits = digits

    if len(pure_digits) == 10 and pure_digits.isdigit():
        return f"+91{pure_digits}"

    return None


def extract_domain_and_host(url_or_host: str) -> Tuple[str, str]:
    """Extract (host, registered_domain) completely offline without live DNS or network.

    Example:
    'https://kyc-update.example-bank-secure.test/verify' ->
    host: 'kyc-update.example-bank-secure.test'
    registered_domain: 'example-bank-secure.test'
    """
    cleaned = url_or_host.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "http://" + cleaned

    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower()

    if not host:
        return "", ""

    parts = host.split(".")
    if len(parts) <= 1:
        return host, host

    # Check two-part suffixes (e.g. example.co.in)
    if len(parts) >= 3:
        two_part = f"{parts[-2]}.{parts[-1]}"
        if two_part in MULTI_PART_SUFFIXES:
            reg_domain = f"{parts[-3]}.{two_part}"
            return host, reg_domain

    # Standard single suffix (e.g. example.test, domain.com)
    reg_domain = f"{parts[-2]}.{parts[-1]}"
    return host, reg_domain


def normalize_url(raw_url: str) -> str:
    """Normalize URL by lowercasing host, removing default ports and tracking parameters."""
    if not raw_url:
        return ""

    cleaned = raw_url.strip()
    if not cleaned.lower().startswith(("http://", "https://")):
        cleaned = "https://" + cleaned

    parsed = urlparse(cleaned)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        netloc = host
    elif port:
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
    if not path:
        path = ""

    # Filter out tracking query params: utm_*, fbclid, gclid, etc.
    filtered_queries = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        k_lower = k.lower()
        if k_lower.startswith("utm_") or k_lower in {"fbclid", "gclid", "ref", "source"}:
            continue
        filtered_queries.append((k, v))

    query = urlencode(filtered_queries)

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def normalize_upi_handle(raw_handle: str) -> str:
    """Normalize UPI-style handle (e.g. user@fakebank)."""
    return raw_handle.strip().lower()


def normalize_apk_package(raw_pkg: str) -> str:
    """Normalize Android package identifier."""
    return raw_pkg.strip().lower()


def normalize_cert_hash(raw_hash: str) -> str:
    """Normalize 64-character SHA-256 certificate fingerprint."""
    return re.sub(r"[\s:]", "", raw_hash).lower()


def normalize_amount(raw_amount: str) -> Optional[float]:
    """Parse Indian currency amount string into numeric float."""
    # Matches patterns like Rs 25,000, INR 500.50, ₹10,000
    cleaned = re.sub(r"[Rs|INR|₹\s,]", "", raw_amount, flags=re.IGNORECASE)
    try:
        return float(cleaned)
    except ValueError:
        return None

