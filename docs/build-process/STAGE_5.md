# STAGE 5: Classification engine (no LLM)

Read AGENT_RULES.md first. Do ONLY this stage. No LLM or external API anywhere.

## Categories (use exactly these)
Salary, Food & Dining, Shopping, Groceries, Transport, Bills & Utilities, Rent, EMI & Loans, Investments, Entertainment, Health, Travel, ATM Withdrawal, Transfer, Cash Deposit, Interest, Fees & Charges, Refund, Other.

## Tasks
1. `src/classifier/cleaner.py`: lowercase, remove long digit strings and reference IDs, detect the channel (UPI, NEFT, IMPS, ATM, POS, ACH, CHQ) and extract merchant text. Example: `UPI/412345678901/SWIGGY/okaxis` gives channel `upi`, merchant `swiggy`.
2. `src/classifier/rules.yaml`: keywords per category (about 100-150 total, Indian context: swiggy, zomato, amazon, flipkart, myntra, uber, ola, irctc, jio, airtel, bescom, lic, sip, mutual fund, netflix, apollo, salary, rent, emi, atm wdl, int.pd, chrg, refund, reversal, ...). Each rule can have an optional `type: credit` or `type: debit` (for example "salary" only applies to credits).
3. `src/classifier/rule_engine.py`: `classify(description, is_credit) -> (category, confidence) or None`. First match by specificity (longer keyword wins).
4. `src/classifier/train.py`:
   - Generate `data/training_data.csv` (300+ labelled descriptions) from templates + the keywords with realistic noise (different channels, random reference numbers, case changes, extra words).
   - Train TF-IDF (character n-grams 2-4) + LogisticRegression, hold out 20% for testing, print accuracy, save `models/classifier.pkl` with joblib.
5. `src/classifier/ml_classifier.py`: load model once, `predict(description) -> (category, probability)`.
6. `src/classifier/hybrid.py`: `classify_rows(rows)`: rule first (`method="rule"`, confidence 1.0); else ML if probability >= 0.5 (`method="ml"`, confidence = probability); else `category="Other"`, `method="none"`. If the model file is missing, train it automatically.

## Tests (`tests/test_classifier.py`)
- At least 20 hand-written descriptions with expected categories (rule cases and ML cases with unseen merchants).
- A credit with "salary" gives Salary; a debit with "salary" does not.
- Fallback gives "Other" for gibberish.
- Print and report the real held-out ML accuracy; do not inflate.

## Done when
Tests pass, `ruff check .` clean, `models/classifier.pkl` and `data/training_data.csv` exist, Stage 5 entry added. Then STOP.
