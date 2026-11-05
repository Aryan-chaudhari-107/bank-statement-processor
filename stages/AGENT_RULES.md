# AGENT_RULES.md (read this first, follow it in every stage)

You are building a small, clean, WORKING prototype: a Bank Statement Processing & Classification System.
The work is split into stage files (STAGE_1.md, STAGE_2.md, ...). I will give you one stage at a time.

## Rules
1. **Keep it simple.** No over-engineering, no extra features, no extra libraries, no files outside the folder structure below.
2. **Only do the current stage.** Do not start the next stage. When done, STOP and wait.
3. **Never claim something works unless you ran it** and saw the output. If a test fails, fix the code. Never delete or weaken tests to make them pass.
4. **Smallest change that works.** Do not rewrite files that already pass tests.
5. Before coding, give a 3-5 line summary of what you will do in this stage.
6. Environment: **Windows + PowerShell**. Use `venv\Scripts\activate`, never `source`. Use `pathlib` for paths.
7. Short functions, clear names, type hints, one-line docstrings. No dead code, no unused imports.
8. At the end of every stage run `pytest` and `ruff check .` and show the real output.

## PROGRESS.md (mandatory)
Keep a file `PROGRESS.md` in the project root. At the end of every stage, APPEND one entry in exactly this format (never delete old entries, never paste full source code):

```
## Stage N: <title>  (status: DONE / PARTIAL / BLOCKED)
- What I built: (3-6 lines, simple words)
- Files created/changed: (list with one line each)
- Commands run and results: (pytest summary line, ruff result, anything else; paste real output lines)
- Design decisions and why: (2-4 bullets, so the user can explain them in an interview)
- Problems faced and how I fixed them:
- Known limitations / not done:
- Next stage needs: (anything the next stage depends on)
```

## Tech stack (only these)
Python 3.10+, streamlit, pdfplumber, pymupdf, pytesseract, opencv-python-headless, pillow, pandas, openpyxl, scikit-learn, joblib, pyyaml, reportlab. Dev: pytest, ruff, vulture.

## Folder structure (create exactly this, nothing more)
```
bank-statement-processor/
├── app.py
├── requirements.txt
├── packages.txt                 # tesseract-ocr (Streamlit Cloud)
├── README.md
├── PROGRESS.md
├── .gitignore
├── .streamlit/config.toml
├── src/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── extractors/  (__init__.py, pdf_detector.py, text_extractor.py, ocr_extractor.py)
│   ├── parsers/     (__init__.py, account_parser.py, table_parser.py, utils.py)
│   ├── validators/  (__init__.py, balance_validator.py)
│   ├── classifier/  (__init__.py, cleaner.py, rules.yaml, rule_engine.py, ml_classifier.py, hybrid.py, train.py)
│   └── exporters.py
├── data/training_data.csv
├── models/classifier.pkl
├── sample_data/generate_samples.py
└── tests/ (test_parsers.py, test_validator.py, test_classifier.py, test_pipeline.py)
```
Keep the stage files and AGENT_RULES.md in a `stages/` folder (do not commit-list them in the README).

## Common data schema
Transaction row fields, exactly: `date` (YYYY-MM-DD), `description`, `debit` (float, 0 if none), `credit` (float, 0 if none), `balance` (float), `category`, `confidence` (0-1), `method` (rule/ml/none), `flag` (empty or short reason).
Account details: `account_holder`, `account_number`, `ifsc`, `bank_name`, `statement_period`.
Words from any extractor (text or OCR) use ONE format: `{"text": str, "x0": float, "x1": float, "top": float, "bottom": float, "page": int}`.
