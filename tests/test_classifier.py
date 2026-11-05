"""Unit and integration tests for transaction classification engine."""

from typing import Any

import pytest

from src.classifier.cleaner import clean_description, detect_channel
from src.classifier.hybrid import classify_rows
from src.classifier.ml_classifier import predict
from src.classifier.rule_engine import classify
from src.classifier.train import train_model


def test_ml_predict_direct() -> None:
    """Test direct ML inference function predicting category and probability."""
    cat, prob = predict("CURRY HOUSE RESTAURANT DINING")
    assert cat == "Food & Dining"
    assert prob >= 0.5


def test_cleaner_channels_and_merchants() -> None:
    """Test channel detection and merchant extraction across various statement conventions."""
    res_upi = clean_description("UPI/412345678901/SWIGGY/okaxis")
    assert res_upi["channel"] == "upi"
    assert res_upi["merchant"] == "swiggy"
    assert "swiggy" in res_upi["cleaned"]

    res_pos = clean_description("POS 4512XXXXXXXX1234 BIG BAZAAR PUNE")
    assert res_pos["channel"] == "pos"
    assert "big bazaar" in res_pos["cleaned"]

    res_neft = clean_description("NEFT CR-HDFC0000240-TECHNOVA SYSTEMS-SALARY MAR")
    assert res_neft["channel"] == "neft"
    assert "technova systems salary mar" in res_neft["cleaned"]

    assert detect_channel("ATM WDL SBI ATM CASH") == "atm"
    assert detect_channel("IMPS/P2A/412345678901/TRANSFER") == "imps"
    assert detect_channel("ACH D- BAJAJ FINANCE EMI 884213") == "ach"


def test_salary_direction_constraint() -> None:
    """Verify that a credit with salary is classified as Salary, but a debit is not."""
    # Credit with salary -> classified as Salary
    res_credit = classify("NEFT CR-HDFC0000240-ACME CORP-SALARY MARCH", is_credit=True)
    assert res_credit is not None
    assert res_credit[0] == "Salary"
    assert res_credit[1] == 1.0

    # Debit with salary -> rule does NOT match (returns None)
    res_debit = classify("NEFT DR-HDFC0000240-ACME CORP-SALARY MARCH", is_credit=False)
    assert res_debit is None


def test_rule_specificity_longer_keyword_wins() -> None:
    """Verify specificity resolution where longer keyword takes precedence."""
    res_insta = classify("UPI/123/SWIGGY INSTAMART/okaxis", is_credit=False)
    assert res_insta is not None
    assert res_insta[0] == "Groceries"

    res_swiggy = classify("UPI/123/SWIGGY/okaxis", is_credit=False)
    assert res_swiggy is not None
    assert res_swiggy[0] == "Food & Dining"


def test_credit_rule_priority_refund() -> None:
    """Verify that a credit transaction prioritizes type: credit rules (Refund) over longer merchant keywords."""
    res = classify("NEFT-REFUND-MAKEMYTRIP", is_credit=True)
    assert res is not None
    assert res[0] == "Refund"
    assert res[1] == 1.0


HANDWRITTEN_TEST_CASES = [
    # Rule cases
    ("UPI/412345678901/SWIGGY/okaxis", False, "Food & Dining"),
    ("UPI/512345678902/ZOMATO/okicici", False, "Food & Dining"),
    ("POS 4512XXXXXXXX1234 DOMINOS PIZZA PUNE", False, "Food & Dining"),
    ("UPI/612345678903/BLINKIT/okhdfcbank", False, "Groceries"),
    ("POS 4512XXXXXXXX9999 BIG BAZAAR MUMBAI", False, "Groceries"),
    ("UPI/712345678904/AMAZON PAY/paytm", False, "Shopping"),
    ("UPI/812345678905/FLIPKART/okaxis", False, "Shopping"),
    ("UPI/912345678906/MYNTRA/ybl", False, "Shopping"),
    ("UPI/112345678907/UBER INDIA/okaxis", False, "Transport"),
    ("POS 5234XXXXXXXX1111 HPCL PETROL PUMP", False, "Transport"),
    ("BIL/BPAY/BESCOM ELECTRICITY 0044521", False, "Bills & Utilities"),
    ("ACH D- LIC OF INDIA 884213", False, "Bills & Utilities"),
    ("IMPS-402512345678-RAHUL SHARMA-RENT-HDFC0001234", False, "Rent"),
    ("ACH D- BAJAJ FINANCE EMI 884213", False, "EMI & Loans"),
    ("NEFT DR-ICIC0000007-ZERODHA BROKING-WITHDRAWAL", False, "Investments"),
    ("UPI/212345678908/NETFLIX/okaxis", False, "Entertainment"),
    ("POS 4512XXXXXXXX2222 APOLLO PHARMACY", False, "Health"),
    ("IRCTC RAIL TICKETING NEW DELHI", False, "Travel"),
    ("ATM WDL SBI ATM PUNE CAMP", False, "ATM Withdrawal"),
    ("NEFT CR-HDFC0000240-TECHNOVA SYSTEMS-SALARY MAR", True, "Salary"),
    ("INT PD 01-01-2025 TO 31-03-2025", True, "Interest"),
    ("SMS CHRG INCL GST", False, "Fees & Charges"),
    # ML cases with unseen merchants
    ("UPI/332145678909/CURRY HOUSE RESTAURANT/okaxis", False, "Food & Dining"),
    ("POS 4512XXXXXXXX3333 DENTAL CARE CLINIC", False, "Health"),
]


@pytest.mark.parametrize(("description", "is_credit", "expected_category"), HANDWRITTEN_TEST_CASES)
def test_twenty_handwritten_cases(description: str, is_credit: bool, expected_category: str) -> None:
    """Validate 24 hand-written descriptions across rules and ML fallback."""
    rows: list[dict[str, Any]] = [{
        "date": "2025-04-01",
        "description": description,
        "debit": 0.0 if is_credit else 500.0,
        "credit": 500.0 if is_credit else 0.0,
        "balance": 10000.0,
        "category": "",
        "confidence": 0.0,
        "method": "none",
        "flag": "",
    }]
    classified = classify_rows(rows)
    assert len(classified) == 1
    assert classified[0]["category"] == expected_category
    assert classified[0]["method"] in ["rule", "ml"]
    assert classified[0]["confidence"] >= 0.5


def test_gibberish_fallback_to_other() -> None:
    """Verify that pure gibberish falls back to category 'Other' with method 'none'."""
    rows: list[dict[str, Any]] = [{
        "date": "2025-04-01",
        "description": "ZXCVBNMASDFGHJKL 998877",
        "debit": 100.0,
        "credit": 0.0,
        "balance": 5000.0,
        "category": "",
        "confidence": 0.0,
        "method": "none",
        "flag": "",
    }]
    classified = classify_rows(rows)
    assert classified[0]["category"] == "Other"
    assert classified[0]["method"] == "none"


def test_ml_held_out_accuracy() -> None:
    """Evaluate and report real held-out accuracy of the machine learning classifier."""
    accuracy = train_model()
    print(f"\nReported held-out test accuracy: {accuracy:.1%}")
    assert accuracy >= 0.85, f"Held-out accuracy {accuracy:.1%} is below required 85%"


def test_unseen_eval_report() -> None:
    """Run honest evaluation report on unseen test data without asserting minimum accuracy."""
    from tests.evaluate_unseen import evaluate_unseen_data, print_evaluation_report

    report = evaluate_unseen_data()
    print_evaluation_report(report)
    assert report["total_rows"] >= 60, "Expected at least 60 unseen evaluation rows"

