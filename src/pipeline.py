"""End-to-end bank statement processing pipeline."""

import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from src.classifier import classify_rows
from src.extractors import (
    PasswordRequired,
    TesseractNotFound,
    WrongPassword,
    detect_page_types,
    extract_words_mixed,
    get_last_ocr_confidence,
)
from src.parsers import parse_account_details, parse_table
from src.validators import validate


class InvalidPDF(Exception):
    """Raised when the input file is not a valid PDF or is corrupted."""


class NoTransactionsFound(Exception):
    """Raised when no valid transaction rows can be extracted from the PDF."""


def generate_category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Generate summary of transactions per category: total debit, total credit, count, sorted by total debit desc."""
    if df.empty or "category" not in df.columns:
        return pd.DataFrame(columns=["category", "total_debit", "total_credit", "count"])

    summary = (
        df.groupby("category", as_index=False)
        .agg(
            total_debit=("debit", "sum"),
            total_credit=("credit", "sum"),
            count=("date", "count"),
        )
        .sort_values(by="total_debit", ascending=False)
        .reset_index(drop=True)
    )
    summary["total_debit"] = summary["total_debit"].round(2)
    summary["total_credit"] = summary["total_credit"].round(2)
    return summary


def process_pdf(
    file_bytes: bytes | str | Path,
    password: str | None = None,
) -> dict[str, Any]:
    """Execute end-to-end statement processing pipeline on PDF bytes or file path."""
    if isinstance(file_bytes, (str, Path)):
        p = Path(file_bytes)
        if not p.is_file():
            raise InvalidPDF(f"PDF file not found: {p}")
        raw_bytes = p.read_bytes()
    elif isinstance(file_bytes, bytes):
        raw_bytes = file_bytes
    else:
        raise InvalidPDF("Input must be PDF bytes or a valid file path")

    # Fast header validation
    if len(raw_bytes) < 4 or (not raw_bytes.startswith(b"%PDF") and b"%PDF" not in raw_bytes[:1024]):
        raise InvalidPDF("The provided input is not a valid PDF document")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = Path(tmp.name)

    try:
        try:
            page_types = detect_page_types(tmp_path, password=password)
        except (PasswordRequired, WrongPassword):
            raise
        except Exception as exc:
            raise InvalidPDF(f"Failed to inspect PDF structure: {exc}") from exc

        try:
            words = extract_words_mixed(tmp_path, password=password)
        except (PasswordRequired, WrongPassword, TesseractNotFound):
            raise
        except Exception as exc:
            raise InvalidPDF(f"Failed to extract words from PDF: {exc}") from exc

        account_details = parse_account_details(words)
        transactions, unparsed_lines = parse_table(words, return_unparsed=True)

        if not transactions:
            raise NoTransactionsFound("No transactions could be parsed from the PDF")

        validated_rows, summary = validate(transactions)
        classified_rows = classify_rows(validated_rows)

        warnings: list[str] = []

        # Check OCR confidence if scanned pages were present
        if "scanned" in page_types:
            mean_conf = get_last_ocr_confidence()
            if mean_conf < 90.0:
                warnings.append(f"Low OCR confidence (mean {mean_conf:.0f}%)")

        # Check unparsed lines containing amounts
        if unparsed_lines > 0:
            warnings.append(
                f"{unparsed_lines} lines contained amounts but could not be parsed into rows"
            )

        # Check balance chain continuity
        possible_missing = summary.get("possible_missing_rows", 0)
        if possible_missing > 0:
            warnings.append(
                f"Balance chain broken {possible_missing} times; some rows may be missing"
            )

        df_transactions = pd.DataFrame(classified_rows)
        cols = [
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
        df_transactions = df_transactions.reindex(columns=cols)

        category_summary = generate_category_summary(df_transactions)

        return {
            "pdf_types": page_types,
            "page_types": page_types,
            "account": account_details,
            "account_details": account_details,
            "transactions": df_transactions,
            "summary": summary,
            "category_summary": category_summary,
            "warnings": warnings,
        }
    finally:
        tmp_path.unlink(missing_ok=True)


def process_statement(
    pdf_path: str | Path,
    password: str | None = None,
) -> dict[str, Any]:
    """Execute end-to-end statement processing on a file path (kept for backwards compatibility)."""
    return process_pdf(pdf_path, password=password)
