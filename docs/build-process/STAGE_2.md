# STAGE 2: Text PDF extraction + parsing (most important stage)

Read AGENT_RULES.md first. Do ONLY this stage. Work in 3 parts and run tests after each part.

## Part A: detector + extractor
- `src/extractors/pdf_detector.py`: for each page count extractable characters with pdfplumber; below a threshold (put it in a constant) means `"scanned"`, else `"text"`. Return a list like `["text", "text"]`. If the PDF is password-protected raise a clear custom error `PasswordRequired`; wrong password raises `WrongPassword`. Support an optional `password` argument.
- `src/extractors/text_extractor.py`: return a list of words in the common word format (see AGENT_RULES.md) for the given pages.

## Part B: utils
- `src/parsers/utils.py`:
  - `parse_date(s)` supports `01/04/2025`, `01-04-2025`, `01-Apr-25`, `01 Apr 2025`, `2025-04-01` (day-first for ambiguous numeric dates). Returns `YYYY-MM-DD` or None.
  - `parse_amount(s)` strips commas, `₹`, `Rs`, spaces; handles `Dr`/`Cr` suffix and negative values; returns `(amount: float, direction: "dr"|"cr"|None)`; empty string returns 0.0.
- Unit tests in `tests/test_parsers.py` for at least 10 date and 10 amount cases.

## Part C: table + account parser
- `src/parsers/table_parser.py` (will be reused by the OCR path, so it must only depend on the common word format):
  - Find the header row (Date, Description/Narration/Particulars, Debit/Withdrawal, Credit/Deposit, Balance, or a single Amount column) and derive column x-ranges from it. Repeat on every page.
  - Group words into rows by `top` (small tolerance), assign words to columns by x-position.
  - A row with no valid date continues the previous description (multi-line).
  - Skip repeated page headers/footers and opening/closing balance rows.
  - Support separate Debit/Credit columns AND a single amount column with Dr/Cr or sign (use balance change to decide direction when unclear).
  - Output rows in the common transaction schema (category fields empty for now).
- `src/parsers/account_parser.py`: regex for IFSC `[A-Z]{4}0[A-Z0-9]{6}`, account number, holder name, statement period; bank name from header text or IFSC prefix. Return the account details dict; missing values are empty strings.

## Done when (golden test)
- `tests/test_parsers.py` has a golden test that, for each of the 4 text sample PDFs, runs detector + extractor + table parser and compares with `*_expected.csv`: same row count, and same date, debit, credit, balance on every row (descriptions compared after whitespace normalisation).
- All 4 pass. Show the pytest output.
- Account details are correct for all 4 PDFs.
- PROGRESS.md has the Stage 2 entry. Then STOP.
