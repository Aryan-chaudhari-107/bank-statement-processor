"""Unit and integration tests for the statement processing pipeline and exporters."""

import io
from pathlib import Path

import openpyxl
import pandas as pd
import pymupdf
import pytest

from src.exporters import to_csv, to_excel
from src.extractors.ocr_extractor import TesseractNotFound, get_tesseract_cmd
from src.pipeline import (
    InvalidPDF,
    NoTransactionsFound,
    process_pdf,
    process_statement,
)

SAMPLE_DIR = Path("sample_data")

EXPECTED_COLUMNS = [
    "date",
    "description",
    "debit",
    "credit",
    "balance",
    "category",
    "confidence",
    "method",
    "flag",
]

TEXT_TEST_CASES = [
    ("text_bordered.pdf", "text_bordered_expected.csv"),
    ("text_borderless.pdf", "text_borderless_expected.csv"),
    ("text_drcr.pdf", "text_drcr_expected.csv"),
    ("text_multiline.pdf", "text_multiline_expected.csv"),
    ("independent/test_A_landscape_extra_cols.pdf", "independent/test_A_expected.csv"),
    ("independent/test_B_portrait_boxed.pdf", "independent/test_B_expected.csv"),
]

SCANNED_TEST_CASES = [
    ("scanned_bordered.pdf", "scanned_bordered_expected.csv"),
    ("scanned_drcr.pdf", "scanned_drcr_expected.csv"),
]


def test_pipeline_text_statement() -> None:
    """Test process_statement on a clean text statement producing structured output and no warnings."""
    pdf_path = SAMPLE_DIR / "text_bordered.pdf"
    result = process_statement(pdf_path)

    assert result["page_types"] == ["text", "text"]
    assert "account_holder" in result["account_details"]
    assert len(result["transactions"]) == 28
    assert result["summary"]["total_rows"] == 28
    assert result["summary"]["flagged_rows"] == 0
    assert result["warnings"] == []


@pytest.mark.parametrize(("pdf_rel", "csv_rel"), TEXT_TEST_CASES)
def test_process_pdf_text_samples(pdf_rel: str, csv_rel: str) -> None:
    """Run full pipeline on text PDF samples and verify columns, row counts, categories, and exports."""
    pdf_path = SAMPLE_DIR / pdf_rel
    csv_path = SAMPLE_DIR / csv_rel

    file_bytes = pdf_path.read_bytes()
    result = process_pdf(file_bytes)

    # Check top-level result structure
    assert "pdf_types" in result
    assert "account" in result
    assert "transactions" in result
    assert "summary" in result
    assert "category_summary" in result

    df = result["transactions"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == EXPECTED_COLUMNS

    expected_df = pd.read_csv(csv_path)
    assert len(df) == len(expected_df), f"Row count mismatch on {pdf_rel}"

    # Verify every row has a non-empty category
    assert (df["category"].astype(str).str.strip() != "").all()

    # Verify category summary structure and ordering
    cat_summary = result["category_summary"]
    assert isinstance(cat_summary, pd.DataFrame)
    assert list(cat_summary.columns) == ["category", "total_debit", "total_credit", "count"]
    if len(cat_summary) > 1:
        debit_vals = list(cat_summary["total_debit"])
        assert debit_vals == sorted(debit_vals, reverse=True), "Category summary not sorted by total debit desc"

    # Verify CSV export
    csv_bytes = to_csv(df)
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0
    reloaded_csv = pd.read_csv(io.BytesIO(csv_bytes))
    assert len(reloaded_csv) == len(df)

    # Verify Excel export and 3 sheet names
    excel_bytes = to_excel(result["account"], df, cat_summary)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    assert wb.sheetnames == ["Transactions", "Account Details", "Category Summary"]


@pytest.mark.parametrize(("pdf_rel", "csv_rel"), SCANNED_TEST_CASES)
def test_process_pdf_scanned_samples(pdf_rel: str, csv_rel: str) -> None:
    """Run full pipeline on scanned PDF samples within OCR tolerance and verify exports."""
    try:
        get_tesseract_cmd()
    except TesseractNotFound:
        pytest.skip("Tesseract OCR binary not found on system")

    pdf_path = SAMPLE_DIR / pdf_rel
    csv_path = SAMPLE_DIR / csv_rel

    file_bytes = pdf_path.read_bytes()
    result = process_pdf(file_bytes)

    df = result["transactions"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == EXPECTED_COLUMNS

    expected_df = pd.read_csv(csv_path)
    assert len(df) >= int(0.90 * len(expected_df)), f"OCR row match below 90% tolerance on {pdf_rel}"

    # Verify all parsed rows have a category
    assert (df["category"].astype(str).str.strip() != "").all()

    # Verify exports
    csv_bytes = to_csv(df)
    assert len(csv_bytes) > 0

    excel_bytes = to_excel(result["account"], df, result["category_summary"])
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    assert wb.sheetnames == ["Transactions", "Account Details", "Category Summary"]


def test_invalid_pdf_handling() -> None:
    """Verify that non-PDF, empty, or corrupted inputs raise InvalidPDF."""
    with pytest.raises(InvalidPDF):
        process_pdf(b"THIS IS NOT A VALID PDF FILE")

    with pytest.raises(InvalidPDF):
        process_pdf(b"")

    with pytest.raises(InvalidPDF):
        process_pdf(b"%PDF-corrupted-content-without-valid-pdf-structures-0000000000")


def test_empty_pdf_no_transactions() -> None:
    """Verify that a valid PDF with no transaction table raises NoTransactionsFound."""
    doc = pymupdf.open()
    doc.new_page()
    blank_bytes = doc.tobytes()
    doc.close()

    with pytest.raises(NoTransactionsFound):
        process_pdf(blank_bytes)
