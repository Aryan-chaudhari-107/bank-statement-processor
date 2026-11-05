"""PDF type detector (text vs scanned) and password exception handling."""

from pathlib import Path
from typing import Any

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect

TEXT_CHAR_THRESHOLD: int = 50


class PasswordRequired(Exception):
    """Raised when an encrypted PDF is opened without a password."""


class WrongPassword(Exception):
    """Raised when an encrypted PDF is opened with an invalid password."""


def _open_pdf(pdf_path: str | Path, password: str | None = None) -> Any:
    """Open a PDF with pdfplumber and map password errors to custom exceptions."""
    kwargs: dict[str, Any] = {}
    if password is not None:
        kwargs["password"] = password

    try:
        return pdfplumber.open(str(pdf_path), **kwargs)
    except Exception as exc:
        is_pw_err = isinstance(exc, PDFPasswordIncorrect) or any(
            isinstance(arg, PDFPasswordIncorrect) for arg in getattr(exc, "args", [])
        )
        if is_pw_err:
            if not password:
                raise PasswordRequired("Password required to open encrypted PDF") from exc
            raise WrongPassword("Incorrect password provided for PDF") from exc
        raise


def detect_page_types(pdf_path: str | Path, password: str | None = None) -> list[str]:
    """Detect whether each page in the PDF is 'text' or 'scanned'."""
    page_types: list[str] = []
    with _open_pdf(pdf_path, password=password) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if len(text.strip()) >= TEXT_CHAR_THRESHOLD:
                page_types.append("text")
            else:
                page_types.append("scanned")
    return page_types
