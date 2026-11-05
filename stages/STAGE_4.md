# STAGE 4: OCR path (scanned PDFs)

Read AGENT_RULES.md first. Do ONLY this stage. The parser from Stage 2 must NOT be rewritten; only fed with OCR words.

## Tasks
1. Extend `sample_data/generate_samples.py` to also create 2 scanned PDFs: render `text_bordered.pdf` and `text_drcr.pdf` to images (PyMuPDF), add slight rotation (about 1-2 degrees) and light noise, and save as image-only PDFs `scanned_bordered.pdf` and `scanned_drcr.pdf`. Reuse the existing `*_expected.csv` files (copy under the new names).
2. `src/extractors/ocr_extractor.py`:
   - Render each scanned page at 300 DPI with PyMuPDF.
   - Preprocess with OpenCV: grayscale, deskew, adaptive threshold.
   - Run `pytesseract.image_to_data` and return words in the SAME common word format as `text_extractor` (coordinates in a consistent unit so `table_parser` works unchanged).
   - Tesseract path: use env var `TESSERACT_CMD` if set, otherwise rely on PATH. If Tesseract is missing raise a clear custom error `TesseractNotFound` with install instructions.
3. Mixed PDFs: a function that, given the detector result, uses text extraction for text pages and OCR for scanned pages and returns one combined word list.
4. Tests: `tests/test_parsers.py` additions:
   - OCR golden test on the 2 scanned PDFs: at least 90% of rows match expected (date, debit, credit, balance). Report the real number.
   - Rows that do not match must be caught by the balance validator (assert that every mismatching row is flagged, or report honestly if not).
   - If Tesseract is not installed, the OCR tests are skipped with a clear reason (not failed).

## Done when
- Tests pass (or are skipped only because Tesseract is missing, and tell me clearly if so).
- The real OCR accuracy figure is written in PROGRESS.md.
- `ruff check .` clean. Stage 4 entry added. Then STOP.

If OCR accuracy is below 90% after reasonable effort (two attempts at tuning preprocessing), do NOT keep hacking. Write the real number in PROGRESS.md, mark the stage PARTIAL and stop.
