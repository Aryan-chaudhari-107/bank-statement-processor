# STAGE 6: Pipeline + exporters

Read AGENT_RULES.md first. Do ONLY this stage.

## Tasks
1. `src/pipeline.py`: `process_pdf(file_bytes: bytes, password: str | None = None) -> dict` returning:
   `{"pdf_types": [...], "account": {...}, "transactions": DataFrame, "summary": {...}, "category_summary": DataFrame}`
   Flow: detect, extract (text or OCR per page), parse account, parse table, validate, classify.
   Raise clear errors (reuse `PasswordRequired`, `WrongPassword`, `TesseractNotFound`) plus `NoTransactionsFound` when nothing can be parsed, and `InvalidPDF` for non-PDF/corrupt input.
2. `category_summary`: per category total debit, total credit, count, sorted by total debit descending.
3. `src/exporters.py`:
   - `to_csv(df) -> bytes`
   - `to_excel(account, df, category_summary) -> bytes` with 3 sheets: **Transactions** (all columns including category), **Account Details**, **Category Summary**. Readable column widths, header row bold, amounts with 2 decimals, flagged rows shaded light yellow.
4. `tests/test_pipeline.py`: run the full pipeline on every sample PDF (text and scanned; skip scanned if Tesseract is missing) and assert: expected columns exist, row count matches the expected CSV (allow the OCR tolerance), every row has a category, CSV and Excel bytes are valid (re-open Excel with openpyxl and check the 3 sheet names). Also test: a non-PDF input raises `InvalidPDF`, an empty PDF raises `NoTransactionsFound`.

## Done when
All tests pass, `ruff check .` clean, Stage 6 entry added. Then STOP.
