"""Export utilities for banking transactions and summary reports to CSV and Excel."""

import io
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def to_csv(df: pd.DataFrame) -> bytes:
    """Export transactions DataFrame to UTF-8 encoded CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")


def to_excel(
    account: dict[str, Any],
    df: pd.DataFrame,
    category_summary: pd.DataFrame,
) -> bytes:
    """Export statement details to an Excel workbook with 3 formatted sheets."""
    wb = Workbook()

    # 1. Sheet: Transactions
    ws_tx = wb.active
    ws_tx.title = "Transactions"

    bold_font = Font(bold=True)
    yellow_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    amount_format = "#,##0.00"

    headers = list(df.columns)
    ws_tx.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws_tx.cell(row=1, column=col_idx)
        cell.font = bold_font
        cell.alignment = Alignment(horizontal="center")

    debit_col_idx = headers.index("debit") + 1 if "debit" in headers else None
    credit_col_idx = headers.index("credit") + 1 if "credit" in headers else None
    balance_col_idx = headers.index("balance") + 1 if "balance" in headers else None
    flag_col_idx = headers.index("flag") + 1 if "flag" in headers else None

    for row_idx, row in enumerate(df.itertuples(index=False), start=2):
        row_values = list(row)
        ws_tx.append(row_values)

        is_flagged = bool(str(row_values[flag_col_idx - 1]).strip()) if flag_col_idx else False

        for col_idx in range(1, len(headers) + 1):
            cell = ws_tx.cell(row=row_idx, column=col_idx)
            if is_flagged:
                cell.fill = yellow_fill

            if col_idx in (debit_col_idx, credit_col_idx, balance_col_idx):
                cell.number_format = amount_format

    # Auto-adjust column widths for Transactions
    for col in ws_tx.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_tx.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 50)

    # 2. Sheet: Account Details
    ws_acc = wb.create_sheet(title="Account Details")
    ws_acc.append(["Field", "Value"])
    ws_acc.cell(row=1, column=1).font = bold_font
    ws_acc.cell(row=1, column=2).font = bold_font

    standard_keys = [
        ("Account Holder", account.get("account_holder", "")),
        ("Account Number", account.get("account_number", "")),
        ("IFSC Code", account.get("ifsc", "")),
        ("Bank Name", account.get("bank_name", "")),
        ("Statement Period", account.get("statement_period", "")),
    ]

    for label, val in standard_keys:
        ws_acc.append([label, str(val or "")])

    for k, v in account.items():
        if k not in ["account_holder", "account_number", "ifsc", "bank_name", "statement_period"]:
            label = str(k).replace("_", " ").title()
            ws_acc.append([label, str(v or "")])

    for col in ws_acc.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_acc.column_dimensions[col_letter].width = min(max(max_len + 3, 15), 50)

    # 3. Sheet: Category Summary
    ws_cat = wb.create_sheet(title="Category Summary")
    cat_headers = list(category_summary.columns)
    ws_cat.append(cat_headers)
    for col_idx in range(1, len(cat_headers) + 1):
        cell = ws_cat.cell(row=1, column=col_idx)
        cell.font = bold_font
        cell.alignment = Alignment(horizontal="center")

    tot_deb_idx = cat_headers.index("total_debit") + 1 if "total_debit" in cat_headers else None
    tot_crd_idx = cat_headers.index("total_credit") + 1 if "total_credit" in cat_headers else None

    for row_idx, row in enumerate(category_summary.itertuples(index=False), start=2):
        row_values = list(row)
        ws_cat.append(row_values)
        for col_idx in range(1, len(cat_headers) + 1):
            cell = ws_cat.cell(row=row_idx, column=col_idx)
            if col_idx in (tot_deb_idx, tot_crd_idx):
                cell.number_format = amount_format

    for col in ws_cat.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_cat.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
