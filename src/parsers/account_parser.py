"""Account details parser from bank statement extracted words or text."""

import re
from typing import Any

BANK_IFSC_PREFIXES: dict[str, str] = {
    "SBIN": "STATE BANK OF INDIA",
    "HDFC": "HDFC BANK",
    "ICIC": "ICICI BANK",
    "UTIB": "AXIS BANK",
    "KKBK": "KOTAK MAHINDRA BANK",
    "PUNB": "PUNJAB NATIONAL BANK",
    "BARB": "BANK OF BARODA",
    "CNRB": "CANARA BANK",
    "UBIN": "UNION BANK OF INDIA",
    "IDIB": "INDIAN BANK",
}


def parse_account_details(words_or_text: list[dict[str, Any]] | str) -> dict[str, str]:
    """Extract account holder, account number, IFSC, bank name, and statement period."""
    if isinstance(words_or_text, str):
        full_text = words_or_text
    else:
        line_buckets: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for w in words_or_text:
            b = round(w["top"] / 3.0) * 3
            line_buckets.setdefault((w["page"], b), []).append(w)

        lines: list[str] = []
        for k in sorted(line_buckets.keys()):
            line = " ".join(w["text"] for w in sorted(line_buckets[k], key=lambda x: x["x0"]))
            lines.append(line)
        full_text = "\n".join(lines)

    details: dict[str, str] = {
        "account_holder": "",
        "account_number": "",
        "ifsc": "",
        "bank_name": "",
        "statement_period": "",
    }

    # IFSC: 4 letters, '0', then 6 alphanumeric characters
    ifsc_match = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", full_text)
    if ifsc_match:
        details["ifsc"] = ifsc_match.group(1).strip()

    # Account Number: 9 to 18 digits after keywords or isolated
    acc_match = re.search(
        r"(?i)(?:account\s*(?:no|number|#)?|a/c\s*(?:no|number|#)?)[:.\s]+([0-9]{9,18})",
        full_text,
    )
    if acc_match:
        details["account_number"] = acc_match.group(1).strip()

    # Account Holder Name: Account Holder, Account Name, Name, Customer Name, A/c Name
    holder_match = re.search(
        r"(?i)(?:account\s*holder(?:\s*name)?|customer\s*name|account\s*name|a/c\s*name|\bname)[:.\s]+([A-Za-z\s.]+?)(?=\s*(?:Bank|Account|IFSC|Statement|Branch|Number|Period|From|To|Date|$|\n))",
        full_text,
    )
    if holder_match:
        details["account_holder"] = holder_match.group(1).strip()

    # Statement Period: Statement From ... To ..., From ... To ..., Statement Period ..., Period ...
    from_to_match = re.search(
        r"(?i)(?:statement\s*from|\bfrom\b)[:.\s]+(.+?)\s+to[:.\s]+([^\n]+?)(?=\s*(?:Branch|Account|IFSC|Date|Page|$|\n))",
        full_text,
    )
    if from_to_match:
        d1 = from_to_match.group(1).strip()
        d2 = from_to_match.group(2).strip()
        details["statement_period"] = f"{d1} to {d2}"
    else:
        period_match = re.search(
            r"(?i)(?:statement\s*period|period)[:.\s]+(.+?)(?=\s*(?:Branch|Account|IFSC|Date|Page|$|\n))",
            full_text,
        )
        if period_match:
            details["statement_period"] = period_match.group(1).strip()

    # Bank Name
    bank_match = re.search(
        r"(?i)bank\s*name[:.\s]+([A-Za-z\s]+?)(?=\s*(?:Branch|Account|IFSC|Statement|Period|From|To|$|\n))",
        full_text,
    )
    if bank_match:
        details["bank_name"] = bank_match.group(1).strip()
    elif details["ifsc"]:
        prefix = details["ifsc"][:4]
        if prefix in BANK_IFSC_PREFIXES:
            details["bank_name"] = BANK_IFSC_PREFIXES[prefix]

    return details
