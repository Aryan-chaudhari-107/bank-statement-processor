"""Rule-based transaction classification engine based on keyword specificity and direction constraints."""

import re
from pathlib import Path
from typing import Any

import yaml

_RULES_CACHE: list[dict[str, Any]] | None = None
_CREDIT_RULES_CACHE: list[dict[str, Any]] | None = None
_DEBIT_RULES_CACHE: list[dict[str, Any]] | None = None


def load_rules(rules_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load and cache categorization rules sorted by specificity (longer pattern wins)."""
    global _CREDIT_RULES_CACHE, _DEBIT_RULES_CACHE, _RULES_CACHE
    if _RULES_CACHE is not None and rules_path is None:
        return _RULES_CACHE

    path = Path(rules_path) if rules_path else Path(__file__).parent / "rules.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rules: list[dict[str, Any]] = data.get("rules", [])
    # Sort by pattern length descending: longest / most specific keyword first
    rules.sort(key=lambda r: len(r.get("pattern", "")), reverse=True)

    credit_specific = [r for r in rules if r.get("type") == "credit"]
    general_rules = [r for r in rules if not r.get("type")]
    debit_specific = [r for r in rules if r.get("type") == "debit"]

    credit_order = credit_specific + general_rules
    debit_order = debit_specific + general_rules

    if rules_path is None:
        _RULES_CACHE = rules
        _CREDIT_RULES_CACHE = credit_order
        _DEBIT_RULES_CACHE = debit_order

    return rules


def classify(description: str, is_credit: bool = False) -> tuple[str, float] | None:
    """Classify description using rule specificity. Return (category, 1.0) or None."""
    load_rules()
    norm = description.strip().lower()
    if not norm:
        return None

    rules_to_check = _CREDIT_RULES_CACHE if is_credit else _DEBIT_RULES_CACHE
    if rules_to_check is None:
        rules = load_rules()
        if is_credit:
            rules_to_check = [r for r in rules if r.get("type") == "credit"] + [
                r for r in rules if not r.get("type")
            ]
        else:
            rules_to_check = [r for r in rules if r.get("type") == "debit"] + [
                r for r in rules if not r.get("type")
            ]

    for r in rules_to_check:
        pattern = r.get("pattern", "").lower()
        if not pattern:
            continue

        # Check word-boundary match (accepting spaces, slashes, dashes, dots, underscores as boundaries)
        regex = r"(?<![a-zA-Z0-9])" + re.escape(pattern) + r"(?![a-zA-Z0-9])"
        if re.search(regex, norm):
            return r["category"], 1.0

    return None
