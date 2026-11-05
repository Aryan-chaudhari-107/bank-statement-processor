"""Text word extractor from PDF pages."""

from pathlib import Path
from typing import Any

from src.extractors.pdf_detector import _open_pdf


def extract_words(
    pdf_path: str | Path,
    pages: list[int] | None = None,
    password: str | None = None,
    x_tolerance: float = 0.6,
) -> list[dict[str, Any]]:
    """Extract words in the common format from specified 1-based PDF pages."""
    words: list[dict[str, Any]] = []
    with _open_pdf(pdf_path, password=password) as pdf:
        target_pages = set(pages) if pages is not None else set(range(1, len(pdf.pages) + 1))
        for page_idx, page in enumerate(pdf.pages, start=1):
            if page_idx not in target_pages:
                continue
            raw_words = page.extract_words(x_tolerance=x_tolerance)
            for w in raw_words:
                words.append({
                    "text": str(w["text"]),
                    "x0": round(float(w["x0"]), 2),
                    "x1": round(float(w["x1"]), 2),
                    "top": round(float(w["top"]), 2),
                    "bottom": round(float(w["bottom"]), 2),
                    "page": page_idx,
                })
    return words
