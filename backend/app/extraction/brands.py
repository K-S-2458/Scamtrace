"""Curated brand directory and official domain whitelist for SCAMTRACE AI.
Used for brand impersonation detection and lexical URL brand-mismatch analysis.
"""
from typing import Dict, List, Optional, Tuple

# Mapping brand canonical names to official domain whitelists
BRAND_OFFICIAL_DOMAINS: Dict[str, List[str]] = {
    # Synthetic brands (RFC 2606 compliant .test domains)
    "examplebank": ["examplebank.test", "examplebank.in"],
    "securebank": ["securebank.test"],
    "trustpay": ["trustpay.test"],
    "fastupi": ["fastupi.test"],
    # Widely known real-world brand references (for comparison / rule testing)
    "hdfc": ["hdfcbank.com"],
    "sbi": ["onlinesbi.sbi", "sbi.co.in", "sbi.bank.in"],
    "icici": ["icicibank.com"],
    "axis": ["axisbank.com"],
    "paytm": ["paytm.com"],
    "phonepe": ["phonepe.com"],
    "googlepay": ["pay.google.com", "google.com"],
}

# Synonyms and aliases mapping to canonical brand key
BRAND_ALIASES: Dict[str, str] = {
    "examplebank": "examplebank",
    "example bank": "examplebank",
    "example-bank": "examplebank",
    "ad-examplebk": "examplebank",
    "securebank": "securebank",
    "secure bank": "securebank",
    "trustpay": "trustpay",
    "trust pay": "trustpay",
    "fastupi": "fastupi",
    "fast upi": "fastupi",
    "hdfc": "hdfc",
    "hdfc bank": "hdfc",
    "ad-hdfcbk": "hdfc",
    "sbi": "sbi",
    "state bank of india": "sbi",
    "sbicard": "sbi",
    "icici": "icici",
    "icici bank": "icici",
    "axis": "axis",
    "axis bank": "axis",
    "paytm": "paytm",
    "phonepe": "phonepe",
    "google pay": "googlepay",
    "gpay": "googlepay",
}


def match_brand(text: str) -> Optional[Tuple[str, str]]:
    """Match brand in text.

    Returns:
        (canonical_brand, matched_raw_text) or None
    """
    import re
    text_lower = text.lower()
    for alias, canonical in sorted(BRAND_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = r"\b" + re.escape(alias) + r"\b"
        match = re.search(pattern, text_lower)
        if match:
            return canonical, text[match.start():match.end()]
    return None


def is_official_domain_for_brand(brand: str, domain_or_host: str) -> bool:
    """Check if domain or host is an official registered domain for the brand."""
    canonical = BRAND_ALIASES.get(brand.lower(), brand.lower())
    official_list = BRAND_OFFICIAL_DOMAINS.get(canonical, [])
    domain_clean = domain_or_host.lower().strip()

    for official in official_list:
        if domain_clean == official or domain_clean.endswith("." + official):
            return True
    return False

