"""Unit and integration tests for balance validator."""

from pathlib import Path
from typing import Any

import pytest

from src.extractors import extract_words
from src.parsers import parse_table
from src.validators import validate

SAMPLE_DIR = Path("sample_data")


def test_clean_data() -> None:
    """Test validation on clean, mathematically consistent transaction rows."""
    rows: list[dict[str, Any]] = [
        {"date": "2025-04-01", "description": "SALARY", "debit": 0.0, "credit": 50000.0, "balance": 100000.0, "flag": ""},
        {"date": "2025-04-02", "description": "GROCERIES", "debit": 2000.0, "credit": 0.0, "balance": 98000.0, "flag": ""},
        {"date": "2025-04-03", "description": "INTEREST", "debit": 0.0, "credit": 500.0, "balance": 98500.0, "flag": ""},
    ]
    validated_rows, summary = validate(rows, opening_balance=50000.0)

    assert summary["total_rows"] == 3
    assert summary["flagged_rows"] == 0
    assert summary["opening_balance"] == 50000.0
    assert summary["closing_balance"] == 98500.0
    assert summary["total_debit"] == 2000.0
    assert summary["total_credit"] == 50500.0
    assert all(r["flag"] == "" for r in validated_rows)


def test_balance_mismatch() -> None:
    """Test that deliberately incorrect balance triggers a balance mismatch flag."""
    rows: list[dict[str, Any]] = [
        {"date": "2025-04-01", "description": "TXN 1", "debit": 0.0, "credit": 1000.0, "balance": 6000.0, "flag": ""},
        # Expected: 6000 - 500 = 5500, but recorded as 5400 (difference 100 unexplained by debit 500)
        {"date": "2025-04-02", "description": "TXN 2", "debit": 500.0, "credit": 0.0, "balance": 5400.0, "flag": ""},
        {"date": "2025-04-03", "description": "TXN 3", "debit": 200.0, "credit": 0.0, "balance": 5200.0, "flag": ""},
    ]
    validated_rows, summary = validate(rows, opening_balance=5000.0)

    assert summary["flagged_rows"] == 1
    assert summary["possible_missing_rows"] == 1
    assert validated_rows[0]["flag"] == ""
    assert validated_rows[1]["flag"] == "balance mismatch (rows may be missing)"
    assert validated_rows[2]["flag"] == ""


def test_balance_mismatch_explained_by_row() -> None:
    """Test that balance mismatch explained by row's own debit/credit doesn't flag missing rows."""
    rows: list[dict[str, Any]] = [
        {"date": "2025-04-01", "description": "TXN 1", "debit": 0.0, "credit": 1000.0, "balance": 6000.0, "flag": ""},
        # Debit 500 was added instead of subtracted (inverted sign: 6000 + 500 = 6500)
        {"date": "2025-04-02", "description": "TXN 2", "debit": 500.0, "credit": 0.0, "balance": 6500.0, "flag": ""},
    ]
    validated_rows, summary = validate(rows, opening_balance=5000.0)

    assert summary["flagged_rows"] == 1
    assert summary["possible_missing_rows"] == 0
    assert validated_rows[1]["flag"] == "balance mismatch"


def test_duplicate_row() -> None:
    """Test that duplicate rows are flagged."""
    rows: list[dict[str, Any]] = [
        {"date": "2025-04-01", "description": "SWIGGY", "debit": 450.0, "credit": 0.0, "balance": 9550.0, "flag": ""},
        {"date": "2025-04-01", "description": "SWIGGY", "debit": 450.0, "credit": 0.0, "balance": 9550.0, "flag": ""},
    ]
    validated_rows, summary = validate(rows, opening_balance=10000.0)

    assert summary["flagged_rows"] == 1
    assert validated_rows[0]["flag"] == ""
    assert "possible duplicate" in validated_rows[1]["flag"]


def test_invalid_date_and_missing_balance() -> None:
    """Test flagging of unparseable dates and missing balance fields."""
    rows: list[dict[str, Any]] = [
        {"date": "invalid-date", "description": "TEST 1", "debit": 100.0, "credit": 0.0, "balance": 4900.0, "flag": ""},
        {"date": "2025-04-02", "description": "TEST 2", "debit": 100.0, "credit": 0.0, "balance": None, "flag": ""},
    ]
    validated_rows, summary = validate(rows, opening_balance=5000.0)

    assert summary["flagged_rows"] == 2
    assert "invalid date" in validated_rows[0]["flag"]
    assert "missing balance" in validated_rows[1]["flag"]


def test_multiple_flags() -> None:
    """Test that multiple issues on a single row are joined with semicolon."""
    rows: list[dict[str, Any]] = [
        {"date": "2025-04-01", "description": "TXN 1", "debit": 0.0, "credit": 1000.0, "balance": 6000.0, "flag": ""},
        # Both invalid date and balance mismatch (6000 - 100 != 5000)
        {"date": "not-a-date", "description": "TXN 2", "debit": 100.0, "credit": 0.0, "balance": 5000.0, "flag": ""},
    ]
    validated_rows, summary = validate(rows, opening_balance=5000.0)

    assert summary["flagged_rows"] == 1
    assert "invalid date" in validated_rows[1]["flag"]
    assert "balance mismatch" in validated_rows[1]["flag"]
    assert "; " in validated_rows[1]["flag"]


@pytest.mark.parametrize(
    "pdf_name",
    [
        "text_bordered.pdf",
        "text_borderless.pdf",
        "text_drcr.pdf",
        "text_multiline.pdf",
        "independent/test_A_landscape_extra_cols.pdf",
        "independent/test_B_portrait_boxed.pdf",
    ],
)
def test_validator_on_sample_pdfs(pdf_name: str) -> None:
    """Ensure zero validation flags on all parsed synthetic and test PDFs."""
    pdf_path = SAMPLE_DIR / pdf_name
    words = extract_words(pdf_path)
    parsed_rows = parse_table(words)

    validated_rows, summary = validate(parsed_rows)

    assert summary["total_rows"] > 0
    assert summary["flagged_rows"] == 0, f"Unexpected flags in {pdf_name}: {[r for r in validated_rows if r['flag']]}"
    assert all(r["flag"] == "" for r in validated_rows)
