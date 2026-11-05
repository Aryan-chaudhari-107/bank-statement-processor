# Bank Statement Processing & Classification System

A clean, robust system to parse, validate, and classify bank statement transactions from PDF and image files into structured financial data.

## Setup Instructions (Windows / PowerShell)

1. **Create and Activate Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
   *Note: On Linux / Streamlit Cloud, install system packages listed in `packages.txt` (e.g. `tesseract-ocr`).*

3. **Generate Sample Data**:
   ```powershell
   python sample_data/generate_samples.py
   ```

4. **Run Tests and Quality Checks**:
   ```powershell
   pytest
   ruff check .
   ```
