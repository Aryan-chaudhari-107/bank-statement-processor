# Bank Statement Processing & Classification System

A production-grade, privacy-first system to extract, reconcile, categorize, review, and export bank statement transactions from digital text PDFs and scanned document images. Built with Python, Streamlit, pdfplumber, PyMuPDF, pytesseract, OpenCV, scikit-learn, and openpyxl without external LLM dependencies.

---

## 1. What It Does

This system transforms unstandardized Indian bank statement PDFs (including bordered tables, borderless tables, single Dr/Cr indicator columns, wrapped multiline narratives, and scanned page images) into structured, mathematically validated financial records. Transactions are categorized across 19 standard spending categories using a deterministic rule engine paired with an n-gram machine learning classifier, presented in an interactive Streamlit UI for review and exported to formatted CSV and multi-sheet Excel files.

---

## 2. Key Features

- **Mixed Document Support**: Automatically detects digital text pages versus scanned images on a per-page basis and routes each page to native text extraction or an OCR pipeline.
- **Robust Table Parser**: Dynamically derives column coordinate boundaries from header tokens, correctly groups unknown columns, and reconstructs multiline descriptions.
- **Mathematical Balance Reconciliation**: Validates running balance arithmetic ($B_{prev} \pm \Delta = B_{curr}$), detects sign inversions, and surfaces warnings if balance continuity breaks.
- **Hybrid Categorization**: High-precision deterministic regex rules take precedence; an n-gram character TF-IDF Logistic Regression model serves as an intelligent fallback.
- **Honest Degradation Alerts**: Low-confidence OCR words, unparsed lines containing amounts, and broken balance chains trigger explicit user warnings rather than silently corrupting data.
- **Interactive Streamlit Review UI**: Single-page minimal web interface featuring account details, summary metric cards, an editable transaction grid (`st.data_editor`) with a 19-category dropdown, expenditure bar charts, and one-click CSV/Excel downloads.
- **Comprehensive Excel Exporter**: Formatted 3-sheet workbook (`Transactions`, `Account Details`, `Category Summary`) with bold headers, `#,#00.00` currency formatting, and flagged rows highlighted in light yellow.

---

## 3. Architecture

```text
Upload -> Detect -> Extract (Text/OCR) -> Parse -> Validate -> Classify -> Review -> Export
```

### Module Responsibilities

- **`src/extractors/pdf_detector.py`**: Inspects character density per page to classify pages as `"text"` or `"scanned"`, and handles encrypted PDF password exceptions.
- **`src/extractors/text_extractor.py`**: Extracts word tokens with bounding-box coordinates from native text pages using `pdfplumber`.
- **`src/extractors/ocr_extractor.py`**: Renders scanned pages to high-DPI images, applies deskewing and adaptive/Otsu binarization, and extracts word coordinates with confidence scores via Tesseract.
- **`src/parsers/account_parser.py`**: Extracts account holder name, account number, IFSC code, bank name, and statement period from narrative header text.
- **`src/parsers/table_parser.py`**: Locates table headers, defines horizontal column boundaries, tracks continuation lines, and extracts structured transaction rows.
- **`src/validators/balance_validator.py`**: Reconciles transaction deltas against running balances, detects inverted debit/credit signs, and flags missing row breaks.
- **`src/classifier/cleaner.py`**: Strips reference numbers and VPA handles from transaction descriptions and detects transaction channels (`UPI`, `NEFT`, `IMPS`, `POS`, `ATM`, `ACH`, `CHQ`).
- **`src/classifier/rule_engine.py`**: Evaluates regex keyword rules by specificity (longer pattern wins), prioritizing `type: credit` rules when processing credit transactions.
- **`src/classifier/ml_classifier.py`**: Evaluates descriptions using a sublinear TF-IDF character n-gram Logistic Regression classifier.
- **`src/classifier/hybrid.py`**: Implements two-stage categorization: rules first (confidence 1.0), ML fallback if probability $\ge 0.25$, defaulting low-confidence novel inputs to `"Other"`.
- **`src/pipeline.py`**: Orchestrates end-to-end processing (`process_pdf`) from raw bytes to transactions, summary metrics, and warnings.
- **`src/exporters.py`**: Exports data to UTF-8 CSV bytes and formatted 3-sheet Excel workbooks via `openpyxl`.
- **`app.py`**: Streamlit single-page UI managing upload state, password decryption, interactive category editing, charts, and file downloads.

---

## 4. Project Structure

```text
bank-statement-processor/
├── app.py                      # Single-page Streamlit web application
├── packages.txt                # System packages for Streamlit Cloud (tesseract-ocr)
├── requirements.txt            # Pinned Python package dependencies
├── README.md                   # System documentation and operational guides
├── .gitignore                  # Git exclusions for venv, caches, and personal PDFs
├── .streamlit/
│   └── config.toml             # Theme settings (#4F46E5 accent) and server limits
├── docs/
│   ├── PROGRESS.md             # Stage-wise implementation progression log
│   └── build-process/          # Incremental stage build plans & execution rules
│       ├── AGENT_RULES.md
│       └── STAGE_1.md .. STAGE_8.md
├── src/
│   ├── __init__.py
│   ├── pipeline.py             # End-to-end orchestration (process_pdf)
│   ├── exporters.py            # Formatted CSV and 3-sheet Excel exports
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── pdf_detector.py     # Text vs. scanned density detection
│   │   ├── text_extractor.py   # pdfplumber native text word extraction
│   │   └── ocr_extractor.py    # Multi-variant Tesseract OCR extractor
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── account_parser.py   # Account metadata parser
│   │   ├── table_parser.py     # Dynamic column table parsing
│   │   └── utils.py            # Date and currency amount utilities
│   ├── validators/
│   │   ├── __init__.py
│   │   └── balance_validator.py# Running balance arithmetic reconciliation
│   └── classifier/
│       ├── __init__.py
│       ├── cleaner.py          # Narrative cleaning & channel identification
│       ├── rules.yaml          # Deterministic keyword rules per category
│       ├── rule_engine.py      # Specificity matching with credit priority
│       ├── ml_classifier.py    # TF-IDF char n-gram Logistic Regression
│       ├── hybrid.py           # Two-stage hybrid classification logic
│       └── train.py            # Training dataset generator & model trainer
├── data/
│   └── training_data.csv       # Curated synthetic training dataset (676 samples)
├── models/
│   └── classifier.pkl          # Serialized scikit-learn classifier pipeline
├── sample_data/
│   ├── generate_samples.py     # Realistic synthetic PDF generator
│   ├── text_*.pdf / expected CSVs
│   ├── scanned_*.pdf / expected CSVs
│   ├── hard/                   # Degraded scan robustness test PDFs
│   └── independent/            # Independent benchmark PDF callsets
└── tests/
    ├── __init__.py
    ├── test_parsers.py         # Parsing and metadata unit/golden tests
    ├── test_validator.py       # Arithmetic validation unit tests
    ├── test_classifier.py      # Classification unit and specificity tests
    ├── test_pipeline.py        # End-to-end pipeline and export integration tests
    ├── unseen_eval.csv         # Hand-written unseen benchmark dataset (74 rows)
    └── evaluate_unseen.py      # Honest evaluation runner and reporting script
```

The stage-wise build log is in [`docs/PROGRESS.md`](docs/PROGRESS.md) and the incremental stage build plan is in [`docs/build-process/`](docs/build-process/).

---

## 5. How PDF Type Detection Works

Page classification is performed in `src/extractors/pdf_detector.py`:
1. Each page is opened with `pdfplumber` and stripped text characters are counted.
2. If character count $\ge 50$ (`TEXT_CHAR_THRESHOLD = 50`), the page is marked `"text"`.
3. If character count $< 50$, the page is marked `"scanned"` and routed to the Tesseract OCR engine.

---

## 6. How Classification Works

Categorization runs across 19 categories:
`Salary`, `Food & Dining`, `Shopping`, `Groceries`, `Transport`, `Bills & Utilities`, `Rent`, `EMI & Loans`, `Investments`, `Entertainment`, `Health`, `Travel`, `ATM Withdrawal`, `Transfer`, `Cash Deposit`, `Interest`, `Fees & Charges`, `Refund`, `Other`.

1. **Stage 1 (Deterministic Rules)**:
   - Matched against `src/classifier/rules.yaml`.
   - Longest matching keyword wins (e.g. `swiggy instamart` $\rightarrow$ `Groceries`, while `swiggy` $\rightarrow$ `Food & Dining`).
   - For credit transactions, rules marked `type: credit` (Salary, Refund, Interest, Cash Deposit) take evaluation priority over generic merchant keywords.
   - Successful rule hits assign confidence `1.0` and `method="rule"`.
2. **Stage 2 (Machine Learning Fallback)**:
   - When no rule matches, the text is cleaned and passed to the trained model (`models/classifier.pkl`).
   - Feature extraction uses sublinear character 2-4 n-grams (`char_wb`), capturing OCR typos and sub-word roots.
   - If top class probability $\ge 0.25$ (`ML_THRESHOLD = 0.25`), the predicted category is assigned with `method="ml"`.
   - If top probability $< 0.25$, the transaction safely defaults to `"Other"` with `method="none"`.
3. **Stage 3 (User Override in UI)**:
   - In the Streamlit web app, users can change any transaction category via the dropdown editor.
   - Category summary tables, debit charts, and exported spreadsheets instantly recompute from the user's edits.

---

## 7. Real Benchmark Numbers

All metrics are taken directly from recorded test runs in [`docs/PROGRESS.md`](docs/PROGRESS.md):

- **Text PDF Parsing (6 Golden Statements, 174 rows)**:
  - Row match accuracy: **100.0%** (174/174)
  - Date, debit, credit, and balance exact match: **100.0%**
  - Balance reconciliation errors: **0**
- **OCR Scanned Statements**:
  - `scanned_bordered.pdf`: **100.0%** (28/28 rows matched)
  - `scanned_drcr.pdf`: **100.0%** (28/28 rows matched)
- **Heavy Image Degradation (Hard Scans with tilt, blur, JPEG 60 compression)**:
  - `hard_multiline.pdf`: 89.8% mean confidence, **100.0%** rows matched, warning surfaced: `"Low OCR confidence (mean 90%)"`.
  - `hard_landscape_extra_cols.pdf`: 82.4% mean confidence, 8 balance breaks flagged, warnings surfaced: `"Low OCR confidence"`, `"14 lines contained amounts but could not be parsed into rows"`, `"Balance chain broken 8 times; some rows may be missing"`.
- **Honest Classification on Unseen Data (`tests/unseen_eval.csv`, 74 hand-written rows with zero training overlap)**:
  - Rules Alone Coverage: **12.2%** (9/74)
  - Rules Alone Accuracy (on matched rows): **100.0%** (9/9)
  - ML Alone Accuracy: **70.3%** (52/74)
  - Hybrid Accuracy ($\ge 0.25$ threshold): **64.9%** (48/74)
  - Fallback to `"Other"`: **24.3%** (18/74)
  - High-confidence errors: **1 row** (`CREDIT BALANCE COMPENSATION PAYOUT` predicted as Salary).

---

## 8. Setup & Installation (Windows)

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Tesseract OCR (v5.x recommended)

### Step 1: Install Tesseract OCR
1. Download the Windows installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install to the default directory (`C:\Program Files\Tesseract-OCR`).
3. If installed to a non-standard path, set the environment variable:
   ```powershell
   [System.Environment]::SetEnvironmentVariable("TESSERACT_CMD", "C:\path\to\tesseract.exe", "User")
   ```

### Step 2: Clone & Set Up Virtual Environment
```powershell
git clone <repo-url>
cd bank-statement-processor

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 9. Running the Application & Tests

### Start the Streamlit Web UI
```powershell
.\venv\Scripts\activate
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

### Run Quality Checks & Unit Tests
```powershell
# Run linting and code quality checks
ruff check .

# Run full test suite (98 unit and integration tests)
pytest
```

---

## 10. How to Add a New Rule or Bank

### Adding a Categorization Rule
Open `src/classifier/rules.yaml` and append a rule block under `rules`:
```yaml
  - pattern: "freshworks"
    category: "Salary"
    type: "credit"

  - pattern: "cult pass"
    category: "Health"
```
Rules are automatically cached and loaded on first classification.

### Adding a New Bank Layout / Synonym
If a new bank statement uses alternate column headers or metadata labels:
1. **Column headers**: Open `src/parsers/table_parser.py` and add the synonym to `HEADER_SYNONYMS`:
   ```python
   "debit": ["withdrawal", "debit", "dr", "debit amount", "withdrawals", "dr."]
   ```
2. **Account labels**: Open `src/parsers/account_parser.py` and add regex variations to `ACCOUNT_PATTERNS`.

---

## 11. Assumptions & Limitations

### Assumptions
- Statements are denominated in Indian Rupee (INR) or standard two-decimal numeric formats.
- Table columns progress horizontally left-to-right with dates formatted in standard DD/MM/YYYY, YYYY-MM-DD, or DD-Mon-YYYY notations.
- Document pages are predominantly upright (skew within $\pm 10^\circ$).

### Limitations
- **Severely Degraded Scans**: Low-resolution, heavily skewed, or compressed scans can lose characters. The system surfaces explicit warnings rather than producing silent errors.
- **Unseen Merchants**: ML classification trained on synthetic banking patterns achieves ~65% accuracy on novel merchant descriptions with 24% defaulting to `"Other"`. Users can review and correct categories directly in the UI.
- **Format Specialization**: Geared towards Indian banking terminology (`NEFT`, `RTGS`, `IMPS`, `UPI`, `FASTAG`, `BPAY`).

### Future Improvements
- Template-based parser library for bank-specific statement formats.
- Feedback loop enabling the ML classifier to retrain on user corrections from `st.data_editor`.
- Multi-currency extraction and support for regional language OCR.

---

## 12. Git Commands & GitHub Push

```bash
# Add all files (excluding virtualenvs, caches, and personal PDFs)
git add .

# Commit changes
git commit -m "stage 8: final checks, documentation, and deployment prep"

# Rename default branch and link remote
git branch -M main
git remote add origin https://github.com/<your-username>/bank-statement-processor.git

# Push to GitHub
git push -u origin main
```

---

## 13. Deployment on Streamlit Community Cloud

1. Push your repository to GitHub.
2. Sign in to [share.streamlit.io](https://share.streamlit.io) using your GitHub account.
3. Click **"New app"**.
4. Configure application settings:
   - **Repository**: `<your-username>/bank-statement-processor`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Click **"Deploy"**.

> **Note**: Streamlit Community Cloud automatically reads `packages.txt` and installs `tesseract-ocr` via `apt-get` during the container build, enabling the OCR extraction pipeline without additional configuration.
