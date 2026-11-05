# STAGE 3: Balance validator

Read AGENT_RULES.md first. Do ONLY this stage. Small stage, keep it small.

## Tasks
`src/validators/balance_validator.py` with a function `validate(rows) -> (rows, summary)`:
1. For each row check `prev_balance + credit - debit == balance` (tolerance 0.01). On failure set `flag = "balance mismatch"`. The first row is checked against the opening balance if known, otherwise skipped.
2. Flag exact duplicate rows (same date, description, debit, credit, balance) with `flag = "possible duplicate"`.
3. Flag rows with an unparseable date or missing balance with `flag = "invalid date"` / `"missing balance"`.
4. If a row has several problems, join the reasons with `; `.
5. `summary` is a dict: `total_rows`, `flagged_rows`, `opening_balance`, `closing_balance`, `total_debit`, `total_credit`.

## Tests (`tests/test_validator.py`)
- Clean data: zero flags.
- One deliberately wrong balance: exactly that row is flagged.
- Duplicate row: flagged.
- Invalid date: flagged.
- Summary numbers correct.
- Run the validator on the 4 parsed sample PDFs: zero flags expected.

## Done when
All tests pass, `ruff check .` clean, PROGRESS.md has the Stage 3 entry. Then STOP.
