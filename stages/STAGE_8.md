# STAGE 8: Final checks, README, deployment prep

Read AGENT_RULES.md first. Do ONLY this stage. No new features.

## Tasks
1. Run `pytest`, `ruff check .` and `vulture src/ --min-confidence 80`. Fix everything that is real; explain anything vulture reports that you keep. Remove unused code and files.
2. Fresh-clone check: in a new temporary venv run `pip install -r requirements.txt`, then `pytest`, then confirm `streamlit run app.py` starts. Report the result. `models/classifier.pkl` must be present in the repo, or trained automatically on first run.
3. `requirements.txt` pinned; `packages.txt` contains `tesseract-ocr`.
4. `README.md` (clear, not long) with sections:
   - What it does + screenshot placeholder
   - Features
   - Setup on Windows (Python, venv, `pip install`, Tesseract install and `TESSERACT_CMD`) and on Linux/Mac
   - How to run (`streamlit run app.py`) and how to run tests
   - Architecture: simple text pipeline diagram `Upload -> Detect -> Extract (text/OCR) -> Parse -> Validate -> Classify -> Review -> Export` and one line per module
   - How PDF type detection works
   - How classification works (rules first, ML fallback, confidence, user override)
   - How to add a new bank layout and how to add a new rule
   - Assumptions, limitations (handwriting, very poor scans, unusual layouts, Indian formats), future improvements (bank-specific templates, learning from user corrections, more languages)
   - Real accuracy numbers from the tests (text parsing, OCR, ML) taken from PROGRESS.md
5. Give me exact copy-paste commands to: `git init`, commit, create a GitHub repo, push; and step-by-step instructions to deploy on **Streamlit Community Cloud** (main file `app.py`).
6. Final report in PROGRESS.md: list of all files with one line each, test results, known limitations, and the 5 most important design decisions in simple words.

## Done when
Everything above is done and shown with real command output. Stage 8 entry added. Then STOP.
