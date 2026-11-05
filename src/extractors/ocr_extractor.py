"""OCR word extractor for scanned PDF pages and mixed PDF dispatcher."""

import os
import shutil
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pymupdf
import pytesseract

from src.extractors.pdf_detector import (
    PasswordRequired,
    WrongPassword,
    detect_page_types,
)
from src.extractors.text_extractor import extract_words
from src.parsers.utils import parse_date


class TesseractNotFound(Exception):
    """Raised when Tesseract OCR binary cannot be located on the system."""


_LAST_OCR_CONFIDENCE: float = 0.0


def get_last_ocr_confidence() -> float:
    """Return the mean word confidence percentage from the most recent OCR extraction."""
    return _LAST_OCR_CONFIDENCE


def get_tesseract_cmd() -> str:
    """Resolve Tesseract executable path from environment, PATH, or standard OS install paths."""
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and (Path(env_cmd).is_file() or shutil.which(env_cmd)):
        return env_cmd

    which_cmd = shutil.which("tesseract")
    if which_cmd:
        return which_cmd

    # Standard Windows installation paths (Windows only)
    if os.name == "nt":
        win_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if win_path.exists():
            return str(win_path)

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            win_local = Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe"
            if win_local.exists():
                return str(win_local)

    raise TesseractNotFound(
        "Tesseract OCR is not installed or not found on PATH. "
        "Please install Tesseract (e.g. https://github.com/UB-Mannheim/tesseract/wiki on Windows "
        "or `apt-get install tesseract-ocr` on Linux) and add it to PATH or set TESSERACT_CMD."
    )


def deskew_image(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Deskew a grayscale image using minAreaRect on foreground Otsu threshold."""
    thresh_inv = cv2.bitwise_not(
        cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    )
    pts = np.column_stack(np.where(thresh_inv > 0))
    if len(pts) > 0:
        rect = cv2.minAreaRect(pts)
        angle = float(rect[-1])
        skew = -(90.0 + angle) if angle < -45.0 else (90.0 - angle if angle > 45.0 else -angle)
    else:
        skew = 0.0

    h, w = gray.shape[:2]
    center = (w // 2, h // 2)
    m_rot = cv2.getRotationMatrix2D(center, skew, 1.0)
    rotated = cv2.warpAffine(
        gray,
        m_rot,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    return rotated, skew


def preprocess_image(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Deskew and threshold a grayscale image using OpenCV."""
    denoised = cv2.medianBlur(gray, 3)
    rotated, skew = deskew_image(denoised)
    binary = cv2.adaptiveThreshold(
        rotated, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 71, 15
    )
    return binary, skew


def _count_valid_dates(ocr_data: dict[str, Any]) -> int:
    """Count how many tokens or multi-token sequences in OCR data represent valid dates."""
    texts = [t.strip() for t in ocr_data.get("text", []) if t.strip()]
    count = 0
    i = 0
    n = len(texts)
    while i < n:
        if parse_date(texts[i]):
            count += 1
            i += 1
        elif i + 2 < n and parse_date(f"{texts[i]} {texts[i+1]} {texts[i+2]}"):
            count += 1
            i += 3
        elif i + 1 < n and parse_date(f"{texts[i]} {texts[i+1]}"):
            count += 1
            i += 2
        else:
            i += 1
    return count


def extract_words_ocr(
    pdf_path: str | Path,
    pages: list[int] | None = None,
    password: str | None = None,
    dpi: int = 300,
) -> list[dict[str, Any]]:
    """Extract words in the common format from specified 1-based scanned PDF pages using OCR."""
    global _LAST_OCR_CONFIDENCE

    tess_cmd = get_tesseract_cmd()
    pytesseract.pytesseract.tesseract_cmd = tess_cmd

    words: list[dict[str, Any]] = []
    all_confs: list[float] = []

    doc = pymupdf.open(str(pdf_path))
    try:
        if doc.is_encrypted:
            if not password:
                raise PasswordRequired("Password required to open encrypted PDF")
            if not doc.authenticate(password):
                raise WrongPassword("Incorrect password provided for PDF")

        target_pages = set(pages) if pages is not None else set(range(1, len(doc) + 1))

        for page_idx, page in enumerate(doc, start=1):
            if page_idx not in target_pages:
                continue

            pix = page.get_pixmap(dpi=dpi)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n >= 3:
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            else:
                gray = arr[:, :, 0]

            # Deskew and denoise
            rotated, _ = deskew_image(gray)
            denoised = cv2.medianBlur(rotated, 3)

            # Two preprocessing variants: Adaptive threshold and Otsu threshold
            var_adaptive = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 71, 15
            )
            _, var_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

            # Run OCR on both variants with --psm 6
            data_adapt = pytesseract.image_to_data(
                var_adaptive, config="--psm 6", output_type=pytesseract.Output.DICT
            )
            data_otsu = pytesseract.image_to_data(
                var_otsu, config="--psm 6", output_type=pytesseract.Output.DICT
            )

            # Select variant with more valid dates (prefer Otsu on tie)
            c_adapt = _count_valid_dates(data_adapt)
            c_otsu = _count_valid_dates(data_otsu)
            data = data_otsu if c_otsu >= c_adapt else data_adapt

            # Collect confidence for non-empty alphanumeric words
            for i in range(len(data["text"])):
                w_text = data["text"][i].strip()
                if w_text and any(c.isalnum() for c in w_text):
                    c_val = float(data["conf"][i])
                    if c_val >= 0:
                        all_confs.append(c_val)

            # Convert image pixels back to PDF points (72 DPI)
            scale_x = page.rect.width / float(pix.width)
            scale_y = page.rect.height / float(pix.height)

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text = data["text"][i].strip()
                if not text or not any(c.isalnum() for c in text):
                    continue

                left = float(data["left"][i])
                top_px = float(data["top"][i])
                width = float(data["width"][i])
                height = float(data["height"][i])

                x0 = round(left * scale_x, 2)
                top = round(top_px * scale_y, 2)
                x1 = round((left + width) * scale_x, 2)
                bottom = round((top_px + height) * scale_y, 2)

                words.append({
                    "text": text,
                    "x0": x0,
                    "x1": x1,
                    "top": top,
                    "bottom": bottom,
                    "page": page_idx,
                })
    finally:
        doc.close()

    _LAST_OCR_CONFIDENCE = round(sum(all_confs) / len(all_confs), 1) if all_confs else 0.0
    return words


def extract_words_mixed(
    pdf_path: str | Path,
    pages: list[int] | None = None,
    password: str | None = None,
) -> list[dict[str, Any]]:
    """Extract words from mixed PDF, dispatching text pages to text extraction and scanned pages to OCR."""
    page_types = detect_page_types(pdf_path, password=password)
    target_pages = pages if pages is not None else list(range(1, len(page_types) + 1))

    text_pages = [p for p in target_pages if page_types[p - 1] == "text"]
    scanned_pages = [p for p in target_pages if page_types[p - 1] == "scanned"]

    all_words: list[dict[str, Any]] = []

    if text_pages:
        all_words.extend(extract_words(pdf_path, pages=text_pages, password=password))

    if scanned_pages:
        all_words.extend(extract_words_ocr(pdf_path, pages=scanned_pages, password=password))

    all_words.sort(key=lambda w: (w["page"], w["top"], w["x0"]))
    return all_words
