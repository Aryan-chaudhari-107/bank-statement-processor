"""End-to-end bank statement processing pipeline."""

from pathlib import Path
from typing import Any

from src.classifier import classify_rows
from src.extractors import (
    detect_page_types,
    extract_words_mixed,
    get_last_ocr_confidence,
)
from src.parsers import parse_account_details, parse_table
from src.validators import validate


def process_statement(
    pdf_path: str | Path,
    password: str | None = None,
) -> dict[str, Any]:
    """Execute end-to-end statement processing: detection, extraction, parsing, validation, and warnings."""
    path = Path(pdf_path)
    page_types = detect_page_types(path, password=password)

    words = extract_words_mixed(path, password=password)
    account_details = parse_account_details(words)

    transactions, unparsed_lines = parse_table(words, return_unparsed=True)
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

    return {
        "page_types": page_types,
        "account_details": account_details,
        "transactions": classified_rows,
        "summary": summary,
        "warnings": warnings,
    }
