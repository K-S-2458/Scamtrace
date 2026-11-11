"""Synthetic Data Generator for SCAMTRACE AI.
Generates reproducible synthetic SMS, URL, and APK datasets, along with
canonical train/dev/test splits and the Section 10 example incident fixture.

Safety Rule 4 Compliance:
- Phone numbers: strictly in reserved range +91 99999 00000 - +91 99999 99999
- Domains: strictly RFC 2606 reserved .test TLD
- UPI handles: fictional handles (*@fakebank, *@trustpay)
- Brand names: purely fictional or synthetic
"""
import json
import random
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
SYNTHETIC_DIR = ROOT_DIR / "data" / "synthetic"
SPLITS_DIR = ROOT_DIR / "data" / "splits"
FIXTURES_DIR = ROOT_DIR / "backend" / "tests" / "fixtures"

SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
SPLITS_DIR.mkdir(parents=True, exist_ok=True)
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42


def generate_sms_dataset(n_samples: int = 400) -> List[Dict[str, Any]]:
    """Generate synthetic SMS messages (benign and suspicious)."""
    random.seed(RANDOM_SEED)

    benign_templates = [
        "Hi, are we still meeting for lunch today at 1 PM?",
        "Your OTP for secure login is 584920. Valid for 10 minutes. Do not share.",
        "Team meeting has been rescheduled to tomorrow at 10 AM.",
        "Your order #48291 has been shipped and will arrive by Friday.",
        "Thanks for catching up yesterday! Let's talk again soon.",
        "Happy Birthday! Wishing you a fantastic year ahead.",
        "Reminder: Dentist appointment tomorrow at 4:30 PM.",
        "Hey, can you send over the project notes when you get a chance?",
        "Your electricity bill of Rs 1,450 for the month has been paid successfully.",
        "Welcome to the portal. Your registration is complete.",
    ]

    suspicious_templates = [
        "URGENT: Your KYC is expiring today. Update immediately at https://kyc-update.example-bank-secure.test/verify to avoid account suspension. Call +91 99999 {num:05d}.",
        "Dear customer, Rs 45,000 debited from account ending {acct:04d} via UPI. If not requested, cancel immediately at https://secure-cancel.trustpay.test/revert or call +91 99999 {num:05d}.",
        "Important notification from ExampleBank: Your netbanking access is locked due to pending PAN linking. Reactivate here: https://login.example-bank-secure.test/pan-update",
        "Congratulations! You won a cash reward of Rs 25,000 on FastUPI. Claim your prize immediately: https://claim-bonus.fastupi.test/reward",
        "Electricity Department: Your power connection will be disconnected tonight at 9:30 PM due to unpaid bill. Immediately contact officer at +91 99999 {num:05d}.",
        "Dear user, your credit card points worth Rs 8,500 will expire tonight. Redeem to cash instantly: https://points-redeem.example-bank-secure.test/cash",
        "Security Alert: Unauthorized login attempt from foreign device on your bank account. Secure account now: https://verify-identity.securebank.test/auth",
        "Your loan of Rs 2,00,000 is approved with zero documentation! Download app immediately: https://files.example-bank-secure.test/loan-app.apk",
    ]

    samples = []
    # Generate balanced set
    for i in range(n_samples // 2):
        # Benign
        text_b = random.choice(benign_templates)
        samples.append({
            "id": f"sms_b_{i+1:04d}",
            "text": text_b,
            "label": 0,
            "category": "benign"
        })

        # Suspicious
        num = random.randint(1, 99999)
        acct = random.randint(1000, 9999)
        tpl = random.choice(suspicious_templates)
        text_s = tpl.format(num=num, acct=acct)
        samples.append({
            "id": f"sms_s_{i+1:04d}",
            "text": text_s,
            "label": 1,
            "category": "suspicious"
        })

    random.shuffle(samples)
    return samples


def generate_url_dataset(n_samples: int = 400) -> List[Dict[str, Any]]:
    """Generate synthetic URLs with held-out template family for test split."""
    random.seed(RANDOM_SEED)

    benign_urls = [
        "https://examplebank.test/personal-banking/accounts",
        "https://examplebank.test/about-us/careers",
        "https://examplebank.test/contact-support",
        "https://securebank.test/customer-service/faq",
        "https://trustpay.test/terms-and-conditions",
        "https://fastupi.test/merchant/directory",
        "https://news-portal.test/technology/cybersecurity-tips",
        "https://public-library.test/books/catalog?genre=science",
        "https://community-blog.test/post/2026/03/software-engineering",
        "https://examplebank.in/services/netbanking",
    ]

    # Standard training suspicious templates
    train_suspicious_templates = [
        "https://kyc-update.example-bank-secure.test/verify?step=1&user_id={uid}",
        "https://login.example-bank-secure.test/signin?redirect=kyc&utm_source=sms",
        "https://claim-bonus.fastupi.test/reward?code={code}",
        "https://secure-cancel.trustpay.test/revert?ref={ref}",
        "https://points-redeem.example-bank-secure.test/cash?token={tok}",
        "https://files.example-bank-secure.test/app.apk",
        "http://192.168.1.100:8080/examplebank-login/verification.html",
        "https://verify-identity.securebank.test/auth/login",
    ]

    # Held-out suspicious template family (reserved for test split)
    held_out_suspicious_templates = [
        "https://urgent-kyc-reactivate.example-bank-secure.test/portal/otp-confirm?session={uid}",
        "https://refund-claim-desk.trustpay.test/dispute/instant-payout?case={ref}",
    ]

    samples = []
    # Benign URLs
    for i in range(n_samples // 2):
        base_u = random.choice(benign_urls)
        samples.append({
            "id": f"url_b_{i+1:04d}",
            "url": f"{base_u}?id={i+100}",
            "label": 0,
            "category": "benign",
            "family": "benign_standard"
        })

    # Suspicious URLs (first 75% standard, last 25% held-out family)
    n_susp = n_samples // 2
    n_held_out = n_susp // 4
    n_standard = n_susp - n_held_out

    for i in range(n_standard):
        tpl = random.choice(train_suspicious_templates)
        u = tpl.format(uid=random.randint(1000, 9999), code=random.randint(10000, 99999), ref=random.randint(100, 999), tok=random.randint(1000, 9999))
        samples.append({
            "id": f"url_s_{i+1:04d}",
            "url": u,
            "label": 1,
            "category": "suspicious",
            "family": "train_standard"
        })

    for i in range(n_held_out):
        tpl = random.choice(held_out_suspicious_templates)
        u = tpl.format(uid=random.randint(1000, 9999), ref=random.randint(100, 999))
        samples.append({
            "id": f"url_s_{n_standard+i+1:04d}",
            "url": u,
            "label": 1,
            "category": "suspicious",
            "family": "held_out_family"
        })

    return samples


def generate_apk_dataset(n_samples: int = 400) -> List[Dict[str, Any]]:
    """Generate synthetic APK metadata (permissions, SDKs, declared components, certificate hashes)."""
    random.seed(RANDOM_SEED)

    benign_packages = [
        "com.simple.calculator",
        "org.productivity.quicknotes",
        "net.weather.forecast.daily",
        "com.reader.simplepdf",
        "com.tools.flashlight",
        "org.open.clock.timer",
    ]

    suspicious_packages = [
        "com.fake.kycupdate",
        "com.examplebank.quickloan.assist",
        "net.trustpay.security.agent",
        "com.android.system.service.update",
        "org.fastupi.instantcash.reward",
        "com.device.support.accessibility.service",
    ]

    benign_perm_pool = [
        "android.permission.INTERNET",
        "android.permission.ACCESS_NETWORK_STATE",
        "android.permission.ACCESS_WIFI_STATE",
        "android.permission.VIBRATE",
        "android.permission.WAKE_LOCK",
        "android.permission.POST_NOTIFICATIONS",
        "android.permission.BLUETOOTH",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.SET_ALARM",
    ]

    samples = []
    for i in range(n_samples // 2):
        # Benign APK
        pkg = random.choice(benign_packages) + f".v{i+1}"
        k_b = random.randint(2, 7)
        perms = random.sample(benign_perm_pool, k=min(k_b, len(benign_perm_pool)))

        samples.append({
            "id": f"apk_b_{i+1:04d}",
            "package_name": pkg,
            "min_sdk": random.choice([19, 21, 23, 24, 26]),
            "target_sdk": random.choice([30, 31, 32, 33, 34]),
            "requested_permissions": perms,
            "activities": [f"{pkg}.MainActivity"],
            "services": [f"{pkg}.SyncService"] if random.random() > 0.5 else [],
            "receivers": [f"{pkg}.BootReceiver"] if random.random() > 0.5 else [],
            "cert_sha256": f"b00000000000000000000000000000000000000000000000000000000000{i+1:04d}",
            "label": 0,
            "category": "benign"
        })

        # Suspicious APK
        s_pkg = random.choice(suspicious_packages) + f".v{i+1}"
        base_benign = random.sample(["android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE"], k=random.randint(1, 2))
        
        # Inject high-risk permissions
        high_risk_choices = [
            "android.permission.READ_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.SEND_SMS",
            "android.permission.BIND_ACCESSIBILITY_SERVICE",
            "android.permission.REQUEST_INSTALL_PACKAGES",
            "android.permission.SYSTEM_ALERT_WINDOW",
            "android.permission.READ_CONTACTS",
            "android.permission.CALL_PHONE",
        ]
        s_perms = base_benign + random.sample(high_risk_choices, k=random.randint(2, 5))

        samples.append({
            "id": f"apk_s_{i+1:04d}",
            "package_name": s_pkg,
            "min_sdk": random.choice([19, 21, 23, 24, 26]),
            "target_sdk": random.choice([30, 31, 32, 33, 34]),
            "requested_permissions": list(set(s_perms)),
            "activities": [f"{s_pkg}.MainActivity", f"{s_pkg}.LureActivity"],
            "services": [f"{s_pkg}.AccessibilitySpy"] if random.random() > 0.3 else [],
            "receivers": [f"{s_pkg}.SmsReceiver"] if random.random() > 0.3 else [],
            "cert_sha256": f"a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef{i%5}",
            "label": 1,
            "category": "suspicious"
        })

    random.shuffle(samples)
    return samples


def create_splits(records: List[Dict[str, Any]], prefix: str, train_ratio=0.7, dev_ratio=0.15) -> Dict[str, List[str]]:
    """Create train/dev/test split IDs (preserving held-out family strictly in test for URLs)."""
    if prefix == "url":
        # Keep held-out family strictly in test split, with balanced benign samples
        held_out_susp = [r["id"] for r in records if r.get("family") == "held_out_family"]
        standard_susp = [r["id"] for r in records if r.get("family") == "train_standard"]
        benign = [r["id"] for r in records if r.get("category") == "benign"]

        random.seed(RANDOM_SEED)
        random.shuffle(standard_susp)
        random.shuffle(benign)

        # Split benign into train, dev, test
        n_benign_test = len(held_out_susp)
        benign_test = benign[:n_benign_test]
        benign_rem = benign[n_benign_test:]

        n_b_train = int(len(benign_rem) * 0.8)
        benign_train = benign_rem[:n_b_train]
        benign_dev = benign_rem[n_b_train:]

        n_s_train = int(len(standard_susp) * 0.8)
        susp_train = standard_susp[:n_s_train]
        susp_dev = standard_susp[n_s_train:]

        train_ids = benign_train + susp_train
        dev_ids = benign_dev + susp_dev
        test_ids = benign_test + held_out_susp
    else:
        all_ids = [r["id"] for r in records]
        random.seed(RANDOM_SEED)
        random.shuffle(all_ids)
        n_total = len(all_ids)
        n_train = int(n_total * train_ratio)
        n_dev = int(n_total * dev_ratio)

        train_ids = all_ids[:n_train]
        dev_ids = all_ids[n_train:n_train+n_dev]
        test_ids = all_ids[n_train+n_dev:]

    splits = {
        "train": train_ids,
        "dev": dev_ids,
        "test": test_ids,
    }
    return splits


def generate_example_scenario_fixture():
    """Generate Section 10 example scenario fixture file."""
    fixture_data = {
        "case_title": "Synthetic KYC scam incident",
        "description": "Multimodal investigation into targeted bank KYC impersonation and SMS/APK lure campaign.",
        "evidence_items": [
            {
                "id": "E1",
                "type": "sms",
                "source_timestamp": "2026-03-10 10:00:00",
                "timestamp_source": "user_entered",
                "uploader": "investigator",
                "text": "Your KYC is expiring. Update now at https://kyc-update.example-bank-secure.test/verify to avoid account block. Call +91 99999 00001.",
                "original_filename": "E1_sms.txt",
                "sender_id": "AD-EXAMPLEBK",
            },
            {
                "id": "E2",
                "type": "chat",
                "source_timestamp": "2026-03-10 10:03:00",
                "timestamp_source": "user_entered",
                "uploader": "investigator",
                "text": "Dear customer, complete KYC here: https://kyc-update.example-bank-secure.test/verify and download the app: https://files.example-bank-secure.test/app.apk",
                "original_filename": "E2_chat.txt",
                "sender_phone": "+919999900001",
            },
            {
                "id": "E3",
                "type": "url",
                "source_timestamp": "2026-03-10 10:05:00",
                "timestamp_source": "user_entered",
                "uploader": "investigator",
                "text": "https://login.example-bank-secure.test/signin?utm_source=sms",
                "original_filename": "E3_url.txt",
            },
            {
                "id": "E4",
                "type": "apk",
                "source_timestamp": "2026-03-10 10:08:00",
                "timestamp_source": "user_entered",
                "uploader": "investigator",
                "original_filename": "E4_app.apk",
                "apk_metadata": {
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
            },
            {
                "id": "E5",
                "type": "sms",
                "source_timestamp": "2026-03-10 10:15:00",
                "timestamp_source": "user_entered",
                "uploader": "investigator",
                "text": "Rs 25,000 debited from your account ending 1234 via UPI. If not you, call +91 99999 00002.",
                "original_filename": "E5_sms.txt",
                "sender_id": "AD-EXAMPLEBK",
            }
        ]
    }

    out_file = FIXTURES_DIR / "example_scenario.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(fixture_data, f, indent=2)


def main():
    """Execute synthetic data generation and save split indexes."""
    print("Generating synthetic datasets (Safety Rule 4 compliant)...")

    # 1. SMS
    sms_data = generate_sms_dataset(400)
    with open(SYNTHETIC_DIR / "sms_dataset.json", "w", encoding="utf-8") as f:
        json.dump(sms_data, f, indent=2)
    sms_splits = create_splits(sms_data, "sms")
    with open(SPLITS_DIR / "sms_splits.json", "w", encoding="utf-8") as f:
        json.dump(sms_splits, f, indent=2)

    # 2. URL
    url_data = generate_url_dataset(400)
    with open(SYNTHETIC_DIR / "url_dataset.json", "w", encoding="utf-8") as f:
        json.dump(url_data, f, indent=2)
    url_splits = create_splits(url_data, "url")
    with open(SPLITS_DIR / "url_splits.json", "w", encoding="utf-8") as f:
        json.dump(url_splits, f, indent=2)

    # 3. APK
    apk_data = generate_apk_dataset(400)
    with open(SYNTHETIC_DIR / "apk_dataset.json", "w", encoding="utf-8") as f:
        json.dump(apk_data, f, indent=2)
    apk_splits = create_splits(apk_data, "apk")
    with open(SPLITS_DIR / "apk_splits.json", "w", encoding="utf-8") as f:
        json.dump(apk_splits, f, indent=2)

    # 4. Example scenario fixture
    generate_example_scenario_fixture()

    print(f"Generated:")
    print(f"  - SMS records: {len(sms_data)} (train: {len(sms_splits['train'])}, dev: {len(sms_splits['dev'])}, test: {len(sms_splits['test'])})")
    print(f"  - URL records: {len(url_data)} (train: {len(url_splits['train'])}, dev: {len(url_splits['dev'])}, test: {len(url_splits['test'])})")
    print(f"  - APK records: {len(apk_data)} (train: {len(apk_splits['train'])}, dev: {len(apk_splits['dev'])}, test: {len(apk_splits['test'])})")
    print(f"  - Fixture: backend/tests/fixtures/example_scenario.json")


if __name__ == "__main__":
    main()

