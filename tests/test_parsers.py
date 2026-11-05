"""Tests for statement parsers, utility functions, and end-to-end golden parser runs."""

import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
import pymupdf
import pytest

from src.extractors import (
    PasswordRequired,
    TesseractNotFound,
    WrongPassword,
    detect_page_types,
    extract_words,
    extract_words_mixed,
    extract_words_ocr,
)
from src.extractors.ocr_extractor import get_tesseract_cmd
from src.parsers import parse_account_details, parse_amount, parse_date, parse_table
from src.validators import validate

SAMPLE_DIR = Path("sample_data")


@pytest.mark.parametrize(
    ("raw_date", "expected"),
    [
        ("01/04/2025", "2025-04-01"),
        ("01-04-2025", "2025-04-01"),
        ("01-Apr-25", "2025-04-01"),
        ("01 Apr 2025", "2025-04-01"),
        ("2025-04-01", "2025-04-01"),
        ("28/04/2025", "2025-04-28"),
        ("15-May-2025", "2025-05-15"),
        ("31 Dec 2024", "2024-12-31"),
        ("2025/12/25", "2025-12-25"),
        ("05/11/24", "2024-11-05"),
        ("invalid-date", None),
        ("", None),
    ],
)
def test_parse_date(raw_date: str, expected: str | None) -> None:
    """Test date parsing across multiple formats."""
    assert parse_date(raw_date) == expected


@pytest.mark.parametrize(
    ("raw_amount", "expected_amount", "expected_direction"),
    [
        ("500.00", 500.0, None),
        ("1,250.50", 1250.5, None),
        ("500.00 Dr", 500.0, "dr"),
        ("65,000.00 Cr", 65000.0, "cr"),
        ("-2,499.00", 2499.0, "dr"),
        ("(3,500.00)", 3500.0, "dr"),
        ("₹ 1850.50", 1850.5, None),
        ("Rs. 4,210.00", 4210.0, None),
        ("17.70dr", 17.7, "dr"),
        ("1250.00 CR", 1250.0, "cr"),
        ("", 0.0, None),
        ("0.00", 0.0, None),
    ],
)
def test_parse_amount(raw_amount: str, expected_amount: float, expected_direction: str | None) -> None:
    """Test amount parsing across multiple formatting conventions."""
    amount, direction = parse_amount(raw_amount)
    assert amount == expected_amount
    assert direction == expected_direction


@pytest.mark.parametrize(
    ("pdf_rel_path", "csv_rel_path"),
    [
        ("text_bordered.pdf", "text_bordered_expected.csv"),
        ("text_borderless.pdf", "text_borderless_expected.csv"),
        ("text_drcr.pdf", "text_drcr_expected.csv"),
        ("text_multiline.pdf", "text_multiline_expected.csv"),
        ("independent/test_A_landscape_extra_cols.pdf", "independent/test_A_expected.csv"),
        ("independent/test_B_portrait_boxed.pdf", "independent/test_B_expected.csv"),
    ],
)
def test_golden_table_parser(pdf_rel_path: str, csv_rel_path: str) -> None:
    """Golden test verifying detector + extractor + table parser matches expected CSV across all 6 PDFs."""
    pdf_path = SAMPLE_DIR / pdf_rel_path
    csv_path = SAMPLE_DIR / csv_rel_path

    # 1. Detector
    page_types = detect_page_types(pdf_path)
    assert all(pt == "text" for pt in page_types)

    # 2. Extractor
    words = extract_words(pdf_path)
    assert len(words) > 0

    # 3. Table parser
    parsed_rows = parse_table(words)
    expected_df = pd.read_csv(csv_path)

    # 4. Assert row count and row contents match 100%
    assert len(parsed_rows) == len(expected_df), f"Row count mismatch in {pdf_rel_path}"

    for idx, (p_row, (_, e_row)) in enumerate(zip(parsed_rows, expected_df.iterrows(), strict=True)):
        assert p_row["date"] == str(e_row["date"]), f"Date mismatch in {pdf_rel_path} row {idx}"
        assert p_row["debit"] == pytest.approx(float(e_row["debit"])), f"Debit mismatch in {pdf_rel_path} row {idx}"
        assert p_row["credit"] == pytest.approx(float(e_row["credit"])), f"Credit mismatch in {pdf_rel_path} row {idx}"
        assert p_row["balance"] == pytest.approx(float(e_row["balance"])), f"Balance mismatch in {pdf_rel_path} row {idx}"

        # Compare descriptions after removing all whitespace to handle mid-word wrapped lines
        p_desc = re.sub(r"\s+", "", p_row["description"])
        e_desc = re.sub(r"\s+", "", str(e_row["description"]))
        assert p_desc == e_desc, f"Description mismatch in {pdf_rel_path} row {idx}"


@pytest.mark.parametrize(
    ("pdf_rel_path", "expected_details"),
    [
        (
            "text_bordered.pdf",
            {
                "account_holder": "RAJESH SHARMA",
                "account_number": "10293847561",
                "ifsc": "SBIN0001234",
                "bank_name": "STATE BANK OF INDIA",
                "statement_period": "01/04/2025 to 28/04/2025",
            },
        ),
        (
            "text_borderless.pdf",
            {
                "account_holder": "PRIYA PATEL",
                "account_number": "50100234567890",
                "ifsc": "HDFC0000456",
                "bank_name": "HDFC BANK",
                "statement_period": "2025-04-01 to 2025-04-28",
            },
        ),
        (
            "text_drcr.pdf",
            {
                "account_holder": "AMIT VERMA",
                "account_number": "001105001234",
                "ifsc": "ICIC0000789",
                "bank_name": "ICICI BANK",
                "statement_period": "01/04/2025 to 28/04/2025",
            },
        ),
        (
            "text_multiline.pdf",
            {
                "account_holder": "SNEHA REDDY",
                "account_number": "912010045678123",
                "ifsc": "UTIB0000321",
                "bank_name": "AXIS BANK",
                "statement_period": "01-Apr-2025 to 28-Apr-2025",
            },
        ),
        (
            "independent/test_A_landscape_extra_cols.pdf",
            {
                "account_holder": "MR. ANIL KUMAR VERMA",
                "account_number": "50100234567891",
                "ifsc": "HDFC0001234",
                "bank_name": "HDFC BANK",
                "statement_period": "01/03/25 to 31/03/25",
            },
        ),
        (
            "independent/test_B_portrait_boxed.pdf",
            {
                "account_holder": "Priya Nair",
                "account_number": "31245678901",
                "ifsc": "SBIN0004567",
                "bank_name": "STATE BANK OF INDIA",
                "statement_period": "01 Mar 2025 to 31 Mar 2025",
            },
        ),
    ],
)
def test_golden_account_details(pdf_rel_path: str, expected_details: dict[str, Any]) -> None:
    """Golden test verifying account details extraction across all 6 sample PDFs."""
    pdf_path = SAMPLE_DIR / pdf_rel_path
    words = extract_words(pdf_path, pages=[1])
    parsed_details = parse_account_details(words)

    for field, expected_val in expected_details.items():
        assert parsed_details[field] == expected_val, f"{field} mismatch in {pdf_rel_path}"


def test_password_protection(tmp_path: Path) -> None:
    """Test PasswordRequired and WrongPassword exceptions on encrypted PDFs."""
    enc_path = tmp_path / "encrypted.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), "Encrypted Statement")
    doc.save(str(enc_path), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret123", owner_pw="owner123")
    doc.close()

    with pytest.raises(PasswordRequired):
        detect_page_types(enc_path)

    with pytest.raises(WrongPassword):
        detect_page_types(enc_path, password="wrong_password")

    with pytest.raises(PasswordRequired):
        extract_words(enc_path)

    with pytest.raises(WrongPassword):
        extract_words(enc_path, password="wrong_password")

    # Correct password succeeds
    types = detect_page_types(enc_path, password="secret123")
    assert types == ["scanned"]
    words = extract_words(enc_path, password="secret123")
    assert len(words) == 2


def _check_tesseract() -> bool:
    """Return True if Tesseract binary is available, False otherwise."""
    try:
        get_tesseract_cmd()
        return True
    except TesseractNotFound:
        return False


requires_tesseract = pytest.mark.skipif(
    not _check_tesseract(),
    reason="Tesseract OCR is not installed or not found on PATH.",
)


def test_tesseract_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that TesseractNotFound is raised when no tesseract binary exists."""
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr("src.extractors.ocr_extractor.Path.exists", lambda _: False)

    with pytest.raises(TesseractNotFound, match="Tesseract OCR is not installed"):
        get_tesseract_cmd()


@requires_tesseract
@pytest.mark.parametrize(
    ("pdf_rel_path", "csv_rel_path"),
    [
        ("scanned_bordered.pdf", "scanned_bordered_expected.csv"),
        ("scanned_drcr.pdf", "scanned_drcr_expected.csv"),
    ],
)
def test_golden_ocr(pdf_rel_path: str, csv_rel_path: str) -> None:
    """OCR golden test on scanned PDFs asserting >= 90% row match and validator catching mismatches."""
    pdf_path = SAMPLE_DIR / pdf_rel_path
    csv_path = SAMPLE_DIR / csv_rel_path

    page_types = detect_page_types(pdf_path)
    assert all(pt == "scanned" for pt in page_types)

    words = extract_words_ocr(pdf_path)
    assert len(words) > 0

    parsed_rows = parse_table(words)
    validated_rows, _ = validate(parsed_rows)

    expected_df = pd.read_csv(csv_path)
    assert len(parsed_rows) == len(expected_df)

    matches = 0
    mismatches = 0
    for idx, (p_row, (_, e_row)) in enumerate(zip(validated_rows, expected_df.iterrows(), strict=True)):
        d_match = p_row["date"] == str(e_row["date"])
        dr_match = abs(p_row["debit"] - float(e_row["debit"])) < 0.05
        cr_match = abs(p_row["credit"] - float(e_row["credit"])) < 0.05
        bal_match = abs(p_row["balance"] - float(e_row["balance"])) < 0.05

        if d_match and dr_match and cr_match and bal_match:
            matches += 1
        else:
            mismatches += 1
            # Any mismatching row must be caught and flagged by the balance validator
            assert p_row.get("flag", "") != "", f"Mismatching row {idx} in {pdf_rel_path} was not flagged"

    accuracy = matches / len(expected_df)
    assert accuracy >= 0.90, f"OCR accuracy {accuracy:.1%} is below required 90% threshold for {pdf_rel_path}"


@requires_tesseract
def test_mixed_pdf_extraction(tmp_path: Path) -> None:
    """Test mixed PDF containing both text and scanned pages."""
    text_pdf_path = SAMPLE_DIR / "text_bordered.pdf"
    scanned_pdf_path = SAMPLE_DIR / "scanned_bordered.pdf"

    doc_text = pymupdf.open(str(text_pdf_path))
    doc_scan = pymupdf.open(str(scanned_pdf_path))

    mixed_doc = pymupdf.open()
    mixed_doc.insert_pdf(doc_text, from_page=0, to_page=0)
    mixed_doc.insert_pdf(doc_scan, from_page=1, to_page=1)

    mixed_path = tmp_path / "mixed_test.pdf"
    mixed_doc.save(str(mixed_path))
    mixed_doc.close()
    doc_text.close()
    doc_scan.close()

    page_types = detect_page_types(mixed_path)
    assert page_types == ["text", "scanned"]

    words = extract_words_mixed(mixed_path)
    assert len(words) > 0

    parsed_rows = parse_table(words)
    expected_df = pd.read_csv(SAMPLE_DIR / "text_bordered_expected.csv")
    assert len(parsed_rows) == len(expected_df)

    matches = sum(
        1
        for p_row, (_, e_row) in zip(parsed_rows, expected_df.iterrows(), strict=True)
        if p_row["date"] == str(e_row["date"])
        and abs(p_row["debit"] - float(e_row["debit"])) < 0.05
        and abs(p_row["credit"] - float(e_row["credit"])) < 0.05
        and abs(p_row["balance"] - float(e_row["balance"])) < 0.05
    )
    assert matches / len(expected_df) >= 0.90


@requires_tesseract
def test_medium_difficulty_ocr(tmp_path: Path) -> None:
    """Medium-difficulty OCR test (200 DPI, 2 deg tilt, mild blur, JPEG 80) targeting >= 85% matches."""
    src_pdf = SAMPLE_DIR / "text_multiline.pdf"
    doc_src = pymupdf.open(str(src_pdf))
    doc_med = pymupdf.open()

    for page in doc_src:
        pix = page.get_pixmap(dpi=200)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        h, w = img.shape[:2]
        m = cv2.getRotationMatrix2D((w // 2, h // 2), 2.0, 1.0)
        rotated = cv2.warpAffine(img, m, (w, h), borderValue=(255, 255, 255))
        blurred = cv2.GaussianBlur(rotated, (3, 3), 0.5)

        _, enc = cv2.imencode(".jpg", blurred, [cv2.IMWRITE_JPEG_QUALITY, 80])
        img_jpg = cv2.imdecode(enc, cv2.IMREAD_COLOR)

        _, enc_png = cv2.imencode(".png", img_jpg)
        med_page = doc_med.new_page(width=page.rect.width, height=page.rect.height)
        med_page.insert_image(med_page.rect, stream=enc_png.tobytes())

    med_path = tmp_path / "medium_multiline.pdf"
    doc_med.save(str(med_path))
    doc_med.close()
    doc_src.close()

    words = extract_words_ocr(med_path)
    parsed_rows = parse_table(words)
    expected_df = pd.read_csv(SAMPLE_DIR / "text_multiline_expected.csv")

    matches = 0
    for p_row, (_, e_row) in zip(parsed_rows, expected_df.iterrows(), strict=False):
        d_match = p_row["date"] == str(e_row["date"])
        dr_match = abs(p_row["debit"] - float(e_row["debit"])) < 0.05
        cr_match = abs(p_row["credit"] - float(e_row["credit"])) < 0.05
        bal_match = abs(p_row["balance"] - float(e_row["balance"])) < 0.05
        if d_match and dr_match and cr_match and bal_match:
            matches += 1

    accuracy = matches / len(expected_df)
    assert accuracy >= 0.85, f"Medium OCR accuracy {accuracy:.1%} is below required 85% threshold"


@requires_tesseract
def test_hard_scanned_warnings() -> None:
    """Verify on hard scanned PDFs that warnings list is non-empty as expected."""
    from src.pipeline import process_statement

    hard_dir = SAMPLE_DIR / "hard"
    hard_pdf_1 = hard_dir / "hard_multiline.pdf"
    hard_pdf_2 = hard_dir / "hard_landscape_extra_cols.pdf"

    if hard_pdf_1.exists():
        res1 = process_statement(hard_pdf_1)
        assert len(res1["warnings"]) > 0, f"Expected non-empty warnings for {hard_pdf_1.name}"

    if hard_pdf_2.exists():
        res2 = process_statement(hard_pdf_2)
        assert len(res2["warnings"]) > 0, f"Expected non-empty warnings for {hard_pdf_2.name}"

