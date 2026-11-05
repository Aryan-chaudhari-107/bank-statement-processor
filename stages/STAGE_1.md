# STAGE 1: Setup + synthetic sample data

Read AGENT_RULES.md first. Do ONLY this stage.

## Tasks
1. Create the full folder structure from AGENT_RULES.md (empty `__init__.py` files where needed; other files can be created in later stages).
2. Create venv instructions, `requirements.txt` (pinned versions after installing), `.gitignore` (venv, __pycache__, .pytest_cache, .ruff_cache, *.xlsx outputs), and install everything. Create `PROGRESS.md` if missing.
3. Write `sample_data/generate_samples.py` that generates **fake data only** (never real personal data):
   - 4 text PDFs, each with 25+ transactions spread over 2 pages, header block with account details (name, account number, IFSC, bank name, period), and a repeated page header/footer:
     1. `text_bordered.pdf`: bordered table, separate Debit / Credit columns, date `01/04/2025`
     2. `text_borderless.pdf`: borderless table, separate Debit / Credit columns, date `2025-04-01`
     3. `text_drcr.pdf`: single amount column with `Dr` / `Cr` suffix
     4. `text_multiline.pdf`: date `01-Apr-25`, descriptions that wrap onto 2 lines
   - A matching `*_expected.csv` for each (columns: date, description, debit, credit, balance) with the TRUE values. Balances must be arithmetically consistent.
   - Descriptions must look Indian and realistic: `UPI/412345678901/SWIGGY/okaxis`, `NEFT-SALARY-ACME CORP`, `ATM WDL 1234`, `IMPS/…`, `POS AMAZON`, `ACH D- LIC PREMIUM`, `INT.PD`, `CHRG SMS`.
   - Do NOT generate scanned PDFs yet (that is Stage 4).
4. Add `reportlab` generated files to `sample_data/`.

## Done when
- `python sample_data/generate_samples.py` runs without error and creates 4 PDFs + 4 expected CSVs.
- Open-check: print the first 5 rows of each expected CSV in the terminal and show them.
- `ruff check .` is clean.
- PROGRESS.md has the Stage 1 entry.

Then STOP.
