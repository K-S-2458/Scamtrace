"""Acceptance tests for Phase 4: Entity Extraction and Canonical Normalization."""
from backend.app.extraction.entities import extract_entities_from_text, extract_entities_from_apk
from backend.app.extraction.normalize import (
    extract_domain_and_host,
    normalize_amount,
    normalize_apk_package,
    normalize_cert_hash,
    normalize_phone,
    normalize_upi_handle,
    normalize_url,
)
from backend.app.extraction.brands import match_brand, is_official_domain_for_brand


def test_phone_normalization_formats():
    """Acceptance test: verify +91 prefix, 0-prefix, and bare 10-digit formats normalize to +91XXXXXXXXXX."""
    assert normalize_phone("+91 99999 00001") == "+919999900001"
    assert normalize_phone("+91-99999-00001") == "+919999900001"
    assert normalize_phone("09999900001") == "+919999900001"
    assert normalize_phone("9999900001") == "+919999900001"
    assert normalize_phone("+919876543210") == "+919876543210"
    assert normalize_phone("09876543210") == "+919876543210"
    assert normalize_phone("9876543210") == "+919876543210"
    # Invalid length
    assert normalize_phone("12345") is None


def test_url_normalization():
    """Acceptance test: verify URL normalization (case, default ports, trailing slash, utm removal)."""
    raw_url = "HTTP://Login.Example-Bank.TEST:80/SignIn/?utm_source=sms&utm_medium=blast&ref=123"
    norm_url = normalize_url(raw_url)

    # Scheme and host should be lowercase, port 80 stripped, trailing slash stripped, utm params removed
    assert norm_url.startswith("http://login.example-bank.test/SignIn")
    assert "utm_source" not in norm_url
    assert "utm_medium" not in norm_url
    assert "ref=123" not in norm_url  # tracking ref removed
    assert ":80" not in norm_url


def test_domain_extraction_offline():
    """Acceptance test: verify host and registered domain (eTLD+1) extraction completely offline."""
    host, reg_dom = extract_domain_and_host("https://kyc-update.example-bank-secure.test/verify")
    assert host == "kyc-update.example-bank-secure.test"
    assert reg_dom == "example-bank-secure.test"

    # Multi-part TLD (.co.in)
    host_in, reg_dom_in = extract_domain_and_host("https://netbanking.samplebank.co.in/login")
    assert host_in == "netbanking.samplebank.co.in"
    assert reg_dom_in == "samplebank.co.in"


def test_upi_handle_extraction_and_normalization():
    """Acceptance test: UPI-style handles are normalized to lowercase."""
    text = "Please transfer registration fee to User.Name_123@FakeBank or support@trustpay."
    entities = extract_entities_from_text(text)
    upi_ents = [e for e in entities if e.entity_type == "upi_handle"]

    assert len(upi_ents) >= 2
    values = [e.value for e in upi_ents]
    assert "user.name_123@fakebank" in values
    assert "support@trustpay" in values

    # Test span correctness
    for e in upi_ents:
        assert text[e.span_start:e.span_end] == e.raw_value


def test_amount_extraction_and_normalization():
    """Acceptance test: parse currency formats (Rs, INR, ₹)."""
    text = "Transferred Rs 25,000.50 on 2026-03-10, remaining INR 5,000 and ₹1,200."
    entities = extract_entities_from_text(text)
    amt_ents = [e for e in entities if e.entity_type == "amount"]

    assert len(amt_ents) == 3
    assert amt_ents[0].metadata["numeric_value"] == 25000.50
    assert amt_ents[1].metadata["numeric_value"] == 5000.00
    assert amt_ents[2].metadata["numeric_value"] == 1200.00

    for e in amt_ents:
        assert text[e.span_start:e.span_end] == e.raw_value


def test_date_and_brand_extraction_with_spans():
    """Acceptance test: extract ISO dates and brand matches with verified spans."""
    text = "Alert from ExampleBank on 2026-03-10 10:00:00: Contact +91 99999 00001."
    entities = extract_entities_from_text(text)

    # Brand match
    brand_ents = [e for e in entities if e.entity_type == "brand"]
    assert len(brand_ents) == 1
    assert brand_ents[0].value == "examplebank"
    assert text[brand_ents[0].span_start:brand_ents[0].span_end] == "ExampleBank"

    # Official domain checking
    assert is_official_domain_for_brand("examplebank", "examplebank.test") is True
    assert is_official_domain_for_brand("examplebank", "kyc-update.example-bank-secure.test") is False

    # Datetime match
    date_ents = [e for e in entities if e.entity_type == "datetime"]
    assert len(date_ents) == 1
    assert "2026-03-10" in date_ents[0].value
    assert text[date_ents[0].span_start:date_ents[0].span_end] == "2026-03-10 10:00:00"

    # Phone span check
    phone_ents = [e for e in entities if e.entity_type == "phone"]
    assert len(phone_ents) == 1
    assert phone_ents[0].value == "+919999900001"
    assert text[phone_ents[0].span_start:phone_ents[0].span_end] == "+91 99999 00001"


def test_apk_package_and_cert_extraction():
    """Acceptance test: extract APK package and certificate hash."""
    test_cert = "0123456789abcdef" * 4
    assert len(test_cert) == 64
    meta = {
        "package_name": "com.fake.kycupdate",
        "cert_sha256": test_cert,
    }
    ents = extract_entities_from_apk(meta)
    assert len(ents) == 2

    pkg_ent = [e for e in ents if e.entity_type == "apk_package"][0]
    assert pkg_ent.value == "com.fake.kycupdate"

    cert_ent = [e for e in ents if e.entity_type == "cert_sha256"][0]
    assert cert_ent.value == meta["cert_sha256"].lower()
