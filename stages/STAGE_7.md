# STAGE 7: Streamlit UI (clean and minimal)

Read AGENT_RULES.md first. Do ONLY this stage. UI calls `src/pipeline.py` and `src/exporters.py` only; no business logic in `app.py`.

## Layout (single page, centered)
1. Title + one-line description.
2. File uploader (PDF only). A password field appears only when the PDF is encrypted (catch `PasswordRequired`).
3. After processing show:
   - Detected type per page (for example "3 pages: 2 text, 1 scanned").
   - Account details in a simple card (holder, account number, IFSC, bank, period).
   - 4 metric tiles: Transactions, Total Debit, Total Credit, Flagged rows.
   - Editable table with `st.data_editor`: category column is a dropdown of the 19 categories; flagged rows are visually marked (a "flag" column is enough if row styling is not supported).
   - Category summary: one small table and one bar chart (debit per category).
   - Two download buttons, CSV and Excel, which use the user-edited data. Recompute the category summary from the edited data.
4. Friendly messages (no stack traces) for: not a PDF, no transactions found, missing Tesseract (explain how to install), wrong password.
5. Use `st.spinner` while processing and cache the result with `st.cache_data` so editing the table does not re-run extraction.

## Design (minimal color)
- Light theme only. White background, greys for everything else, ONE accent color indigo `#4F46E5`. No gradients, no emojis (at most none), no extra colors except a light yellow for flagged rows.
- `.streamlit/config.toml`: `primaryColor="#4F46E5"`, `backgroundColor="#FFFFFF"`, `secondaryBackgroundColor="#F5F6F8"`, `textColor="#1F2937"`, `font="sans serif"`, and `[server] maxUploadSize = 20`.
- Generous spacing, short labels, `layout="centered"` or a modest wide layout.

## Done when
- `streamlit run app.py` starts without errors.
- Agent verifies by running the app and feeding each of the 6 sample PDFs through the same code path (a short script is fine), and reports the results. Also explain in 3 lines how the user should manually test it in the browser.
- `ruff check .` clean, all tests still pass, Stage 7 entry added. Then STOP.
