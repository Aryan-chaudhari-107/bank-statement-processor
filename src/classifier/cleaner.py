"""Text cleaner, channel detector, and merchant extractor for bank transaction descriptions."""

import re
from typing import Any

CHANNELS: list[str] = ["upi", "neft", "imps", "atm", "pos", "ach", "chq", "bil"]


def detect_channel(text: str) -> str:
    """Detect payment channel from raw transaction description."""
    norm = text.lower()
    for ch in CHANNELS:
        if re.search(r"(?:\b|_|-|/)" + ch + r"(?:\b|_|-|/)", norm):
            return ch
    return ""


def clean_description(raw_desc: str) -> dict[str, Any]:
    """Clean transaction description, extract payment channel and merchant text."""
    channel = detect_channel(raw_desc)
    text = raw_desc.strip()

    # Normalize delimiters
    text_norm = re.sub(r"[/|\\_-]+", " ", text)

    # Remove standard channel markers
    text_clean = re.sub(r"\b(upi|neft|imps|atm|pos|ach|chq|bil|bpay|clearing|wdl|dep|p2a)\b", " ", text_norm, flags=re.IGNORECASE)

    # Remove direction indicators
    text_clean = re.sub(r"\b(cr|dr)\b", " ", text_clean, flags=re.IGNORECASE)

    # Remove masked card numbers (e.g. 4512XXXXXXXX1234)
    text_clean = re.sub(r"\b\d{4}[xX*]+\d{4}\b", " ", text_clean)

    # Remove IFSC codes (e.g. HDFC0001234, ICIC0000001)
    text_clean = re.sub(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", " ", text_clean, flags=re.IGNORECASE)

    # Remove VPA handles / emails (e.g. @okaxis, @icici, user@bank)
    text_clean = re.sub(r"\S*@\S*", " ", text_clean)

    # Remove common UPI PSP handle suffixes (e.g. okaxis, okhdfcbank, oksbi, okicici, paytm, ybl, axl, ibl)
    text_clean = re.sub(r"\b(okaxis|okhdfcbank|oksbi|okicici|okbizaxis|paytm|ybl|axl|ibl|apl|upi)\b", " ", text_clean, flags=re.IGNORECASE)

    # Remove long digit strings (5 or more digits like reference IDs, dates, account numbers)
    text_clean = re.sub(r"\b\d{5,}\b", " ", text_clean)

    # Remove standalone small numbers
    text_clean = re.sub(r"\b\d+\b", " ", text_clean)

    # Collapse multiple whitespace and lowercase
    cleaned = re.sub(r"\s+", " ", text_clean).strip().lower()

    # Extract primary merchant candidate (first 1-3 meaningful words)
    words = cleaned.split()
    merchant = " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else "")

    return {
        "channel": channel,
        "merchant": merchant,
        "cleaned": cleaned,
    }
