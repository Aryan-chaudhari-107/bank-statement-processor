# Bank Statement Processing & Classification System

A privacy-first, production-grade system to extract, reconcile, classify, and export bank statement transactions from digital and scanned PDFs — **100% local, with zero external LLM dependencies**.

Built with **Python, Streamlit, pdfplumber, PyMuPDF, Tesseract OCR, OpenCV, scikit-learn, and openpyxl**.

---

## 1. What It Does

Converts unstandardized Indian bank statements (bordered, borderless, single Dr/Cr columns, wrapped multiline descriptions, or scanned phone images) into clean, structured financial data:
1. **Extracts data** from digital text and scanned PDFs.
2. **Reconciles balances mathematically** to catch missing or corrupted rows.
3. **Categorizes transactions** into 19 spending categories using a hybrid Rule + ML engine.
4. **Interactive UI** to review, edit categories, view expense charts, and export to CSV or 3-sheet Excel.

---

## 2. Architecture & Pipeline

```text
[PDF Upload]
     │
     ▼
1. Detect Page Type  ──► Digital Text (pdfplumber) OR Scanned Image (OpenCV + Tesseract)
     │
     ▼
2. Dynamic Parser    ──► Derives column boundaries from headers; merges multiline narratives
     │
     ▼
3. Balance Validator ──► Mathematical check: Prev_Balance + Credit - Debit == Curr_Balance
     │
     ▼
4. Hybrid Classifier ──► Stage 1: Deterministic Rules (Regex)
                         Stage 2: Fallback to ML (Char n-gram Logistic Regression)
     │
     ▼
5. Review & Export   ──► Streamlit UI (editable grid) ──► CSV & Multi-sheet Excel (.xlsx)
```

---

## 3. Core Modules Explained (How It Works)

| Module | File | What it does |
|---|---|---|
| **Page Detector** | `src/extractors/pdf_detector.py` | Counts characters per page ($\ge 50$ = digital text, $< 50$ = scanned image). Handles encrypted PDF passwords. |
| **Unified Extractor** | `src/extractors/text_extractor.py`<br>`src/extractors/ocr_extractor.py` | Converts both digital pages and deskewed/binarized OCR images into the exact same word coordinate schema `(text, x0, x1, top, bottom)`. |
| **Table Parser** | `src/parsers/table_parser.py` | Finds header words dynamically (no hardcoded coordinates), sets column boundaries from midpoints, ignores unknown columns, and merges multiline descriptions. |
| **Balance Validator** | `src/validators/balance_validator.py` | Validates running balance arithmetic. Flags missing rows, inverted Dr/Cr signs, and duplicate transactions. |
| **Hybrid Classifier** | `src/classifier/hybrid.py`<br>`src/classifier/rule_engine.py`<br>`src/classifier/ml_classifier.py` | **Rules first**: Regex matching with directional priority (Credit rules evaluated first for credits).<br>**ML fallback**: TF-IDF Character 2-4 n-grams + Logistic Regression ($\ge 0.25$ threshold; novel noise defaults safely to `"Other"`). |
| **UI & Exporters** | `app.py`<br>`src/exporters.py` | Single-page Streamlit review app (`st.data_editor`), expense charts, and 3-sheet Excel export (Transactions with flagged rows in yellow, Account Details, Category Summary). |

---

## 4. Testing & Accuracy Benchmarks

Testing is split into two distinct areas: **Data Extraction Accuracy** (getting numbers/tables right) and **ML Classification Accuracy** (predicting the right spending category).

### A. Data Extraction & Parsing Accuracy
Evaluated against ground-truth CSVs across diverse statement formats:
- **Digital Text PDFs (6 benchmark statements, 174 total rows)**:
  - **100% Extraction Accuracy (174/174 rows)** — Every single transaction row, date, debit, credit, and running balance matched ground-truth perfectly with **0 reconciliation errors**.
- **Scanned Document OCR (56 total rows)**:
  - **100% Extraction Accuracy (56/56 rows)** on standard 300 DPI scanned statements (`scanned_bordered.pdf` and `scanned_drcr.pdf`).
- **Heavily Degraded Scans (Hard tilt, blur, JPEG compression)**:
  - Automatically flags degraded quality with explicit warnings (`Low OCR confidence (82%)`, `Balance chain broken`) instead of producing silent data errors.

### B. ML Classification Testing Accuracy (19 Categories)
- **Held-out Test Set (Synthetic Data Split)**: **100% Accuracy** on training/validation test split.
- **Unseen Real-World Benchmark (`tests/unseen_eval.csv`, 74 hand-written rows with zero training overlap)**:
  - **ML Model Accuracy**: **70.3%** (52/74 rows correctly predicted).
  - **Hybrid (Rules + ML) Accuracy**: **64.9%** (48/74 rows).
  - **Safe Fallback to `"Other"`**: **24.3%** (18/74 novel merchants defaulted to `"Other"` to avoid false guesses).
  - **High-Confidence Error Rate**: Only **1.4%** (1/74 rows was wrongly predicted with high confidence).

### C. Automated Test Suite
- **98 automated tests (`pytest`)** passing across extraction, arithmetic reconciliation, rule specificity, model inference, and export integrity.

---

## 5. Project Structure

```text
bank-statement-processor/
├── app.py                      # Streamlit UI
├── requirements.txt            # Python dependencies
├── packages.txt                # System packages for cloud deployment (tesseract-ocr)
├── src/
│   ├── pipeline.py             # Master orchestrator (process_pdf)
│   ├── exporters.py            # CSV & 3-sheet Excel exports
│   ├── extractors/             # Page detection, text & OCR extraction
│   ├── parsers/               # Header detection, dynamic table parsing, account metadata
│   ├── validators/             # Running balance arithmetic validation
│   └── classifier/             # Rules, ML model, cleaning & hybrid logic
├── data/
│   └── training_data.csv       # 676 labelled banking transactions
├── models/
│   └── classifier.pkl          # Trained TF-IDF + Logistic Regression model (~770 KB)
├── sample_data/                # Synthetic PDFs (bordered, borderless, Dr/Cr, multiline, scanned)
└── tests/                      # 98 unit and integration tests (pytest)
```

---

## 6. Quick Start & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Tesseract OCR

### Installation & Run (Windows)
```powershell
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the application
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

### Run Tests
```powershell
# Run code linter
ruff check .

# Run full test suite (98 tests)
pytest
```

---

## 7. Key Assumptions & Limitations

- **Assumptions**: Denominated in INR (₹) or standard two-decimal formats; horizontal left-to-right tables; tilt within $\pm 10^\circ$.
- **Limitations**: Severely blurred/compressed scans can drop words (system alerts the user explicitly). Novel merchant names without clear keywords fall back to `"Other"` for manual one-click review in the UI.
