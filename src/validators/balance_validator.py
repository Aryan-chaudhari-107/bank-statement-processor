"""Balance validation and transaction reconciliation engine."""

from typing import Any

from src.parsers.utils import parse_date

TOLERANCE: float = 0.01


def _is_explained_by_row(
    prev_balance: float,
    current_balance: float,
    debit: float,
    credit: float,
) -> bool:
    """Check if balance mismatch is explained by row's own debit/credit rather than missing rows."""
    expected_balance = prev_balance + credit - debit
    diff = abs(expected_balance - current_balance)

    # 1. Swapped Dr / Cr (inverted sign)
    if abs((prev_balance + debit - credit) - current_balance) <= TOLERANCE:
        return True

    # 2. Unapplied debit or credit
    if abs(prev_balance - current_balance) <= TOLERANCE:
        return True
    if abs((prev_balance + credit) - current_balance) <= TOLERANCE:
        return True
    if abs((prev_balance - debit) - current_balance) <= TOLERANCE:
        return True

    # 3. Double applied debit or credit
    if abs((prev_balance + credit - 2 * debit) - current_balance) <= TOLERANCE:
        return True
    if abs((prev_balance + 2 * credit - debit) - current_balance) <= TOLERANCE:
        return True

    # 4. Difference magnitude directly matches debit or credit amount
    if debit > 0 and (abs(diff - debit) <= TOLERANCE or abs(diff - 2 * debit) <= TOLERANCE):
        return True

    return bool(credit > 0 and (abs(diff - credit) <= TOLERANCE or abs(diff - 2 * credit) <= TOLERANCE))


def validate(
    rows: list[dict[str, Any]],
    opening_balance: float | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate arithmetic consistency, dates, balances, and duplicates for transaction rows."""
    validated_rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[Any, ...]] = set()
    prev_balance: float | None = opening_balance

    total_debit: float = 0.0
    total_credit: float = 0.0
    possible_missing_rows: int = 0

    for idx, raw_row in enumerate(rows):
        row = dict(raw_row)
        flags: list[str] = []

        date_val = row.get("date")
        if not date_val or parse_date(str(date_val)) is None:
            flags.append("invalid date")

        bal_raw = row.get("balance")
        if bal_raw is None:
            flags.append("missing balance")
            current_balance: float | None = None
        else:
            try:
                current_balance = float(bal_raw)
            except (ValueError, TypeError):
                flags.append("missing balance")
                current_balance = None

        debit = float(row.get("debit", 0.0) or 0.0)
        credit = float(row.get("credit", 0.0) or 0.0)
        total_debit += debit
        total_credit += credit

        # Check balance arithmetic
        if current_balance is not None:
            if idx == 0 and opening_balance is None:
                # First row with unknown opening balance is skipped for mismatch check
                prev_balance = current_balance
            elif prev_balance is not None:
                expected_balance = prev_balance + credit - debit
                if abs(expected_balance - current_balance) > TOLERANCE:
                    if _is_explained_by_row(prev_balance, current_balance, debit, credit):
                        flags.append("balance mismatch")
                    else:
                        flags.append("balance mismatch (rows may be missing)")
                        possible_missing_rows += 1
                prev_balance = current_balance
            else:
                prev_balance = current_balance
        else:
            prev_balance = None

        # Check duplicate
        row_key = (
            row.get("date"),
            row.get("description"),
            round(debit, 2),
            round(credit, 2),
            round(current_balance, 2) if current_balance is not None else None,
        )
        if row_key in seen_keys:
            flags.append("possible duplicate")
        else:
            seen_keys.add(row_key)

        existing_flag = row.get("flag", "")
        if existing_flag:
            flags.insert(0, existing_flag)

        row["flag"] = "; ".join(flags)
        validated_rows.append(row)

    # Inferred opening balance if not explicitly provided
    resolved_opening_balance: float | None = None
    if opening_balance is not None:
        resolved_opening_balance = round(float(opening_balance), 2)
    elif validated_rows and validated_rows[0].get("balance") is not None:
        first_b = float(validated_rows[0]["balance"])
        first_cr = float(validated_rows[0].get("credit", 0.0) or 0.0)
        first_dr = float(validated_rows[0].get("debit", 0.0) or 0.0)
        resolved_opening_balance = round(first_b - first_cr + first_dr, 2)

    resolved_closing_balance: float | None = None
    if validated_rows and validated_rows[-1].get("balance") is not None:
        resolved_closing_balance = round(float(validated_rows[-1]["balance"]), 2)

    summary: dict[str, Any] = {
        "total_rows": len(validated_rows),
        "flagged_rows": sum(1 for r in validated_rows if r.get("flag")),
        "possible_missing_rows": possible_missing_rows,
        "opening_balance": resolved_opening_balance,
        "closing_balance": resolved_closing_balance,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
    }

    return validated_rows, summary
