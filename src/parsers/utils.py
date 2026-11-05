"""Parser utility functions for dates and amounts."""

import re
from datetime import datetime


def parse_date(s: str | None) -> str | None:
    """Parse date string into ISO YYYY-MM-DD format (day-first for ambiguous numeric dates)."""
    if not s or not s.strip():
        return None

    cleaned = s.strip()
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d %b %y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%y",
        "%d-%m-%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def parse_amount(s: str | None) -> tuple[float, str | None]:
    """Strip currency symbols, commas, and whitespace; return (amount, direction)."""
    if not s or not s.strip():
        return (0.0, None)

    cleaned = s.strip()
    direction: str | None = None

    # Parentheses indicate debit (accounting negative)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        direction = "dr"
        cleaned = cleaned[1:-1].strip()

    # Leading or trailing minus sign indicates debit
    if cleaned.startswith("-"):
        direction = "dr"
        cleaned = cleaned[1:].strip()
    elif cleaned.endswith("-"):
        direction = "dr"
        cleaned = cleaned[:-1].strip()

    # Check for Dr/Cr suffix or word
    if re.search(r"(?i)\bdr\.?\b", cleaned) or cleaned.lower().endswith("dr"):
        direction = "dr"
        cleaned = re.sub(r"(?i)\bdr\.?\b", "", cleaned)
        if cleaned.lower().endswith("dr"):
            cleaned = cleaned[:-2]
    elif re.search(r"(?i)\bcr\.?\b", cleaned) or cleaned.lower().endswith("cr"):
        direction = "cr"
        cleaned = re.sub(r"(?i)\bcr\.?\b", "", cleaned)
        if cleaned.lower().endswith("cr"):
            cleaned = cleaned[:-2]

    # Strip currency symbols, commas, INR/Rs prefixes, spaces
    cleaned = re.sub(r"[₹,\s]", "", cleaned)
    cleaned = re.sub(r"(?i)rs\.?|inr", "", cleaned)

    try:
        val = float(cleaned)
        return (round(abs(val), 2), direction)
    except ValueError:
        return (0.0, direction)
