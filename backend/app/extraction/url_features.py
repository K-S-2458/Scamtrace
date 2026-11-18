"""Lexical URL feature extraction for SCAMTRACE AI.
Purely offline and lightweight: no Scikit-Learn or Pandas dependencies.
"""
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from backend.app.config import LURE_KEYWORDS, SUSPICIOUS_TLDS
from backend.app.extraction.brands import match_brand, is_official_domain_for_brand
from backend.app.extraction.normalize import extract_domain_and_host

FEATURE_NAMES = [
    "url_length",
    "num_dots",
    "num_hyphens",
    "num_digits",
    "has_at_symbol",
    "is_ip_host",
    "num_subdomains",
    "is_https",
    "is_suspicious_tld",
    "keyword_count",
    "brand_mismatch",
    "has_punycode",
    "path_depth",
    "query_length",
    "domain_age_days",
]


def extract_lexical_url_features(url: str, domain_age_days: Optional[int] = None) -> Dict[str, float]:
    """Extract 15 purely lexical features from a URL without live network lookups."""
    if not url:
        return {f: 0.0 for f in FEATURE_NAMES}

    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned

    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parsed.query or ""

    # Feature 1: URL length
    url_length = float(len(url))

    # Feature 2: Dots
    num_dots = float(url.count("."))

    # Feature 3: Hyphens
    num_hyphens = float(url.count("-"))

    # Feature 4: Digits
    num_digits = float(sum(c.isdigit() for c in url))

    # Feature 5: @ symbol
    has_at_symbol = 1.0 if "@" in url else 0.0

    # Feature 6: IP address as host
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    is_ip_host = 1.0 if ip_pattern.match(host) else 0.0

    # Feature 7: Subdomain count
    _, reg_domain = extract_domain_and_host(cleaned)
    host_parts = host.split(".")
    reg_parts = reg_domain.split(".") if reg_domain else []
    num_subdomains = float(max(0, len(host_parts) - len(reg_parts)))

    # Feature 8: HTTPS
    is_https = 1.0 if cleaned.startswith("https://") else 0.0

    # Feature 9: Suspicious TLD
    is_suspicious_tld = 1.0 if any(host.endswith(tld) for tld in SUSPICIOUS_TLDS) else 0.0

    # Feature 10: Lure / KYC Keywords
    url_lower = url.lower()
    keyword_count = float(sum(1 for kw in LURE_KEYWORDS if kw in url_lower))

    # Feature 11: Brand in non-official domain
    brand_match = match_brand(url_lower)
    brand_mismatch = 0.0
    if brand_match:
        canonical_brand, _ = brand_match
        if not is_official_domain_for_brand(canonical_brand, reg_domain or host):
            brand_mismatch = 1.0

    # Feature 12: Punycode
    has_punycode = 1.0 if "xn--" in host else 0.0

    # Feature 13: Path depth
    segments = [s for s in path.split("/") if s]
    path_depth = float(len(segments))

    # Feature 14: Query length
    query_length = float(len(query))

    # Feature 15: Optional user-supplied domain age
    age = float(domain_age_days) if domain_age_days is not None and domain_age_days >= 0 else 0.0

    return {
        "url_length": url_length,
        "num_dots": num_dots,
        "num_hyphens": num_hyphens,
        "num_digits": num_digits,
        "has_at_symbol": has_at_symbol,
        "is_ip_host": is_ip_host,
        "num_subdomains": num_subdomains,
        "is_https": is_https,
        "is_suspicious_tld": is_suspicious_tld,
        "keyword_count": keyword_count,
        "brand_mismatch": brand_mismatch,
        "has_punycode": has_punycode,
        "path_depth": path_depth,
        "query_length": query_length,
        "domain_age_days": age,
    }
