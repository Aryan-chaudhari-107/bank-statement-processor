"""Streamlit UI for bank statement extraction, validation, and categorization."""

from typing import Any

import streamlit as st

from src.exporters import to_csv, to_excel
from src.pipeline import (
    InvalidPDF,
    NoTransactionsFound,
    PasswordRequired,
    TesseractNotFound,
    WrongPassword,
    generate_category_summary,
    process_pdf,
)

CATEGORIES = [
    "Salary",
    "Food & Dining",
    "Shopping",
    "Groceries",
    "Transport",
    "Bills & Utilities",
    "Rent",
    "EMI & Loans",
    "Investments",
    "Entertainment",
    "Health",
    "Travel",
    "ATM Withdrawal",
    "Transfer",
    "Cash Deposit",
    "Interest",
    "Fees & Charges",
    "Refund",
    "Other",
]


@st.cache_data(show_spinner=False)
def run_pipeline(file_bytes: bytes, password: str | None = None) -> dict[str, Any]:
    """Execute cached pipeline processing on statement bytes."""
    return process_pdf(file_bytes, password=password)


def main() -> None:
    """Render the single-page bank statement processing application."""
    st.set_page_config(page_title="Bank Statement Processor", layout="centered")

    st.title("Bank Statement Processor")
    st.caption("Extract, validate, categorize, and export bank statement transactions.")

    uploaded_file = st.file_uploader("Upload bank statement (PDF)", type=["pdf"])
    if uploaded_file is None:
        return

    # Reset password state when a new file is uploaded
    current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get("file_id") != current_file_id:
        st.session_state["file_id"] = current_file_id
        st.session_state["needs_password"] = False

    password: str | None = None
    if st.session_state.get("needs_password", False):
        password = st.text_input("Enter statement password", type="password")
        if not password:
            st.info("This statement is password protected. Enter the password above to proceed.")
            return

    file_bytes = uploaded_file.getvalue()

    try:
        with st.spinner("Processing bank statement..."):
            result = run_pipeline(file_bytes, password=password)
    except PasswordRequired:
        st.session_state["needs_password"] = True
        st.rerun()
    except WrongPassword:
        st.error("Incorrect password provided. Please verify and try again.")
        return
    except InvalidPDF:
        st.error("The uploaded file is not a valid or supported PDF.")
        return
    except NoTransactionsFound:
        st.warning("No transactions could be found or parsed from this statement.")
        return
    except TesseractNotFound:
        st.error(
            "Tesseract OCR is not installed or not found on PATH. "
            "Please install Tesseract-OCR to process scanned statements."
        )
        return
    except (RuntimeError, ValueError, OSError) as exc:
        st.error(f"Failed to process statement: {exc}")
        return

    # 1. Page types breakdown
    page_types = result["pdf_types"]
    text_count = page_types.count("text")
    scanned_count = page_types.count("scanned")
    st.caption(f"{len(page_types)} pages: {text_count} text, {scanned_count} scanned")

    # 2. Account details card
    account = result["account"]
    st.markdown("#### Account Details")
    col_a1, col_a2, col_a3 = st.columns(3)
    col_a1.write(f"**Holder:** {account.get('account_holder') or '—'}")
    col_a1.write(f"**Account:** {account.get('account_number') or '—'}")
    col_a2.write(f"**IFSC:** {account.get('ifsc') or '—'}")
    col_a2.write(f"**Bank:** {account.get('bank_name') or '—'}")
    col_a3.write(f"**Period:** {account.get('statement_period') or '—'}")

    # 3. 4 metric tiles
    summary = result["summary"]
    transactions_df = result["transactions"]

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Transactions", len(transactions_df))
    col_m2.metric("Total Debit", f"₹{summary.get('total_debit', 0.0):,.2f}")
    col_m3.metric("Total Credit", f"₹{summary.get('total_credit', 0.0):,.2f}")
    col_m4.metric("Flagged Rows", summary.get("flagged_rows", 0))

    # Display warnings if present
    warnings = result.get("warnings", [])
    for w in warnings:
        st.warning(w)

    # 4. Editable transaction table
    st.markdown("#### Transactions")
    edited_df = st.data_editor(
        transactions_df,
        column_config={
            "category": st.column_config.SelectboxColumn(
                "Category",
                options=CATEGORIES,
                required=True,
            ),
            "debit": st.column_config.NumberColumn("Debit", format="₹%.2f"),
            "credit": st.column_config.NumberColumn("Credit", format="₹%.2f"),
            "balance": st.column_config.NumberColumn("Balance", format="₹%.2f"),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
        },
        disabled=[
            "date",
            "description",
            "debit",
            "credit",
            "balance",
            "confidence",
            "method",
            "flag",
        ],
        hide_index=True,
        use_container_width=True,
        key="tx_editor",
    )

    # 5. Category summary table and chart recomputed from edited_df
    cat_summary = generate_category_summary(edited_df)

    st.markdown("#### Category Summary")
    st.dataframe(cat_summary, hide_index=True, use_container_width=True)

    if not cat_summary.empty and (cat_summary["total_debit"] > 0).any():
        chart_data = (
            cat_summary[cat_summary["total_debit"] > 0]
            .set_index("category")[["total_debit"]]
        )
        st.bar_chart(chart_data, color="#4F46E5")

    # 6. CSV and Excel download buttons
    col_d1, col_d2 = st.columns(2)
    csv_bytes = to_csv(edited_df)
    excel_bytes = to_excel(account, edited_df, cat_summary)

    col_d1.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name="transactions.csv",
        mime="text/csv",
        use_container_width=True,
    )
    col_d2.download_button(
        label="Download Excel",
        data=excel_bytes,
        file_name="statement.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
