"""Table parser that converts word stream into structured transaction rows."""

import difflib
import re
from typing import Any

from src.parsers.utils import parse_amount, parse_date

ROW_TOLERANCE: float = 3.5
HEADER_WORD_GAP_THRESHOLD: float = 10.0

HEADER_SYNONYMS: dict[str, list[str]] = {
    "value_date": ["value date", "value dt", "val date", "val dt"],
    "date": [
        "txn date",
        "transaction date",
        "tran date",
        "post date",
        "posting date",
        "date",
        "txn dt",
        "transaction dt",
    ],
    "description": [
        "description",
        "narration",
        "particulars",
        "transaction details",
        "details",
        "desc",
    ],
    "debit": [
        "withdrawal amt.",
        "withdrawal amt",
        "withdrawals",
        "withdrawal",
        "debit amt.",
        "debit amt",
        "debit",
        "dr.",
        "dr",
    ],
    "credit": [
        "deposit amt.",
        "deposit amt",
        "deposits",
        "deposit",
        "credit amt.",
        "credit amt",
        "credit",
        "cr.",
        "cr",
    ],
    "amount": ["amount", "txn amount"],
    "balance": ["closing balance", "balance", "closing bal", "bal"],
}


GENERIC_HEADER_WORDS = {"date", "amt", "no", "dt", "val", "details"}


def _normalize_header_text(text: str) -> str:
    """Normalize text for header keyword comparison."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9/]", " ", text)).strip().lower()


def _match_keyword(token: str, candidates: list[str], cutoff: float = 0.8) -> bool:
    """Check if token matches any candidate keyword directly or with difflib fuzzy matching."""
    norm = _normalize_header_text(token)
    if not norm:
        return False
    for kw in candidates:
        norm_kw = _normalize_header_text(kw)
        if norm == norm_kw or norm.startswith(norm_kw + " ") or norm.endswith(" " + norm_kw):
            return True
    if len(norm) >= 4:
        norm_candidates = [_normalize_header_text(kw) for kw in candidates]
        if difflib.get_close_matches(norm, norm_candidates, n=1, cutoff=cutoff):
            return True
        single_words = [
            w
            for kw in candidates
            for w in _normalize_header_text(kw).split()
            if len(w) >= 4 and w not in GENERIC_HEADER_WORDS
        ]
        if difflib.get_close_matches(norm, single_words, n=1, cutoff=cutoff):
            return True
    return False


def _classify_token(token: str, assigned_roles: set[str]) -> str | None:
    """Classify a single header token into a semantic role or None if ignored."""
    norm = _normalize_header_text(token)
    if not norm:
        return None

    # Ignore value date / reference columns first
    if "value" in norm or "val" in norm:
        for kw in HEADER_SYNONYMS["value_date"]:
            nkw = _normalize_header_text(kw)
            if norm == nkw or norm.startswith(nkw + " ") or norm.endswith(" " + nkw):
                return None

    # Step 1: Direct / exact matching across all roles
    role_order = ["credit", "debit", "balance", "date", "amount", "description"]
    for role in role_order:
        for kw in HEADER_SYNONYMS[role]:
            nkw = _normalize_header_text(kw)
            if norm == nkw or norm.startswith(nkw + " ") or norm.endswith(" " + nkw):
                if role == "date" and "date" in assigned_roles:
                    return None
                return role

    # Step 2: Fuzzy matching individual header words (cutoff=0.8)
    words = norm.split()
    fuzzy_targets = [
        ("credit", ["deposit", "deposits", "credit"]),
        ("debit", ["withdrawal", "withdrawals", "debit"]),
        ("balance", ["balance", "closing"]),
        ("date", ["transaction", "posting"]),
        ("description", ["description", "narration", "particulars", "details"]),
    ]
    for w in words:
        if len(w) >= 4 and w not in GENERIC_HEADER_WORDS:
            for role, candidates in fuzzy_targets:
                if difflib.get_close_matches(w, candidates, n=1, cutoff=0.8):
                    if role == "date" and "date" in assigned_roles:
                        return None
                    return role

    return None


def _classify_header_cell(cell_text: str, assigned_roles: set[str]) -> str | None:
    """Classify a header cell into a semantic role or None if ignored."""
    return _classify_token(cell_text, assigned_roles)


def _split_fused_header_cell(cell: dict[str, Any]) -> list[dict[str, Any]]:
    """Split a fused header cell (e.g. 'Date Description EO') into individual word cells."""
    words = cell["text"].split()
    if len(words) <= 1:
        return [cell]

    recognized_roles: set[str] = set()
    for w in words:
        r = _classify_token(w, set())
        if r:
            recognized_roles.add(r)

    # Split if cell contains multiple distinct roles or recognized keywords mixed with tokens
    if len(recognized_roles) >= 2 or (recognized_roles and not _classify_token(cell["text"], set())):
        full_text = cell["text"]
        cell_w = cell["x1"] - cell["x0"]
        char_w = cell_w / max(len(full_text), 1)
        split_cells: list[dict[str, Any]] = []
        curr_idx = 0
        for w in words:
            start_pos = full_text.find(w, curr_idx)
            if start_pos == -1:
                start_pos = curr_idx
            w_x0 = round(cell["x0"] + start_pos * char_w, 2)
            w_x1 = round(w_x0 + len(w) * char_w, 2)
            split_cells.append({"text": w, "x0": w_x0, "x1": w_x1})
            curr_idx = start_pos + len(w)
        return split_cells

    return [cell]


def _group_header_cells(
    row_words: list[dict[str, Any]],
    max_word_gap: float = HEADER_WORD_GAP_THRESHOLD,
) -> list[dict[str, Any]]:
    """Group adjacent words in a header row into individual header cells, splitting fused keywords."""
    sorted_words = sorted(row_words, key=lambda w: w["x0"])
    cells: list[list[dict[str, Any]]] = []
    curr: list[dict[str, Any]] = []

    for w in sorted_words:
        if not curr:
            curr.append(w)
        else:
            prev_role = _classify_token(curr[-1]["text"], set())
            curr_role = _classify_token(w["text"], set())
            different_roles = bool(prev_role and curr_role and prev_role != curr_role)

            if not different_roles and (w["x0"] - curr[-1]["x1"] <= max_word_gap):
                curr.append(w)
            else:
                cells.append(curr)
                curr = [w]
    if curr:
        cells.append(curr)

    raw_cells = [
        {
            "text": " ".join(w["text"] for w in c),
            "x0": c[0]["x0"],
            "x1": c[-1]["x1"],
        }
        for c in cells
    ]

    final_cells: list[dict[str, Any]] = []
    for rc in raw_cells:
        final_cells.extend(_split_fused_header_cell(rc))

    return final_cells


def _cluster_words_by_row(
    words: list[dict[str, Any]],
    tolerance: float = ROW_TOLERANCE,
) -> list[list[dict[str, Any]]]:
    """Group words with similar vertical positions into horizontal rows."""
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows: list[list[dict[str, Any]]] = []
    curr_row: list[dict[str, Any]] = []
    curr_top: float | None = None

    for w in sorted_words:
        if curr_top is None or abs(w["top"] - curr_top) <= tolerance:
            curr_row.append(w)
            curr_top = w["top"] if curr_top is None else (curr_top + w["top"]) / 2.0
        else:
            rows.append(curr_row)
            curr_row = [w]
            curr_top = w["top"]

    if curr_row:
        rows.append(curr_row)

    return rows


def parse_table(
    words: list[dict[str, Any]],
    return_unparsed: bool = False,
) -> Any:
    """Parse common word stream into standardized transaction dictionaries."""
    pages: dict[int, list[dict[str, Any]]] = {}
    for w in words:
        pages.setdefault(w["page"], []).append(w)

    transactions: list[dict[str, Any]] = []
    prev_balance: float | None = None
    total_unparsed_lines: int = 0

    for page_num in sorted(pages.keys()):
        page_words = pages[page_num]
        rows = _cluster_words_by_row(page_words)

        header_cells: list[dict[str, Any]] | None = None
        header_row: list[dict[str, Any]] | None = None

        for r in rows:
            cells = _group_header_cells(r)
            assigned_roles: set[str] = set()
            col_map: list[dict[str, Any]] = []

            for c in cells:
                role = _classify_header_cell(c["text"], assigned_roles)
                if role:
                    assigned_roles.add(role)
                col_map.append({"cell": c, "role": role})

            # Check if this row is a valid table header
            has_amount_indicator = (
                "debit" in assigned_roles
                or "amount" in assigned_roles
                or "description" in assigned_roles
            )
            if "date" in assigned_roles and "balance" in assigned_roles and has_amount_indicator:
                header_cells = col_map
                header_row = r
                break

        if not header_cells or not header_row:
            continue

        header_bottom = max(w["bottom"] for w in header_row)

        # Build column x-ranges from each header start to the next header start
        col_ranges: list[dict[str, Any]] = []
        for i, item in enumerate(header_cells):
            start_x = 0.0 if i == 0 else item["cell"]["x0"]
            end_x = 10000.0 if i == len(header_cells) - 1 else header_cells[i + 1]["cell"]["x0"]
            col_ranges.append({"role": item["role"], "start": start_x, "end": end_x})

        # Process words below header and above footer zone
        table_words = [w for w in page_words if w["top"] >= header_bottom and w["top"] <= 780.0]
        data_rows = _cluster_words_by_row(table_words)

        for r in data_rows:
            col_text: dict[str, list[str]] = {}
            for w in r:
                mid_x = (w["x0"] + w["x1"]) / 2.0
                for cr in col_ranges:
                    if cr["start"] <= mid_x < cr["end"]:
                        if cr["role"]:
                            col_text.setdefault(cr["role"], []).append(w["text"])
                        break

            joined_cols = {role: " ".join(toks).strip() for role, toks in col_text.items()}
            row_text_lower = " ".join(joined_cols.values()).lower()

            if any(term in row_text_lower for term in [
                "opening balance",
                "closing balance",
                "brought forward",
                "carried forward",
                "computer generated",
                "page ",
            ]):
                continue

            raw_date = joined_cols.get("date", "")
            parsed_date = parse_date(raw_date)

            if parsed_date:
                desc = joined_cols.get("description", "")
                bal_val, _ = parse_amount(joined_cols.get("balance", ""))

                roles_present = [cr["role"] for cr in col_ranges if cr["role"]]
                if "amount" in roles_present:
                    amt_val, direction = parse_amount(joined_cols.get("amount", ""))
                    if direction == "dr":
                        debit, credit = amt_val, 0.0
                    elif direction == "cr":
                        debit, credit = 0.0, amt_val
                    else:
                        if prev_balance is not None and bal_val < prev_balance:
                            debit, credit = amt_val, 0.0
                        else:
                            debit, credit = 0.0, amt_val
                else:
                    debit, _ = parse_amount(joined_cols.get("debit", ""))
                    credit, _ = parse_amount(joined_cols.get("credit", ""))

                prev_balance = bal_val
                transactions.append({
                    "date": parsed_date,
                    "description": desc,
                    "debit": float(debit),
                    "credit": float(credit),
                    "balance": float(bal_val),
                    "category": "",
                    "confidence": 0.0,
                    "method": "none",
                    "flag": "",
                })
            else:
                # Count unparsed lines: lines after the header containing an amount-like token that produced no row
                line_has_amount = any(
                    re.search(r"\b\d{1,3}(?:,\d{2,3})*\.\d{2}\b", w["text"])
                    or (parse_amount(w["text"])[0] > 0 and "." in w["text"])
                    for w in r
                )
                if line_has_amount:
                    total_unparsed_lines += 1

                if transactions:
                    continuation_desc = joined_cols.get("description", "")
                    if not continuation_desc:
                        continuation_desc = " ".join(v for v in joined_cols.values() if v)
                    if continuation_desc:
                        transactions[-1]["description"] = (
                            transactions[-1]["description"] + " " + continuation_desc
                        ).strip()

    for txn in transactions:
        txn["description"] = re.sub(r"\s+", " ", txn["description"]).strip()

    parse_table.unparsed_lines = total_unparsed_lines  # type: ignore[attr-defined]

    if return_unparsed:
        return transactions, total_unparsed_lines
    return transactions
