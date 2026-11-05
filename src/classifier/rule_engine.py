"""Rule-based transaction classification engine based on keyword specificity and direction constraints."""

import re
from pathlib import Path
from typing import Any

import yaml

_RULES_CACHE: list[dict[str, Any]] | None = None


def load_rules(rules_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load and cache categorization rules sorted by specificity (longer pattern wins)."""
    global _RULES_CACHE
    if _RULES_CACHE is not None and rules_path is None:
        return _RULES_CACHE

    path = Path(rules_path) if rules_path else Path(__file__).parent / "rules.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rules: list[dict[str, Any]] = data.get("rules", [])
    # Sort by pattern length descending: longest / most specific keyword first
    rules.sort(key=lambda r: len(r.get("pattern", "")), reverse=True)

    if rules_path is None:
        _RULES_CACHE = rules
    return rules


def classify(description: str, is_credit: bool = False) -> tuple[str, float] | None:
    """Classify description using rule specificity. Return (category, 1.0) or None."""
    rules = load_rules()
    norm = description.strip().lower()
    if not norm:
        return None

    for r in rules:
        pattern = r.get("pattern", "").lower()
        if not pattern:
            continue

        rule_type = r.get("type")
        if rule_type == "credit" and not is_credit:
            continue
        if rule_type == "debit" and is_credit:
            continue

        # Check word-boundary match (accepting spaces, slashes, dashes, dots, underscores as boundaries)
        regex = r"(?<![a-zA-Z0-9])" + re.escape(pattern) + r"(?![a-zA-Z0-9])"
        if re.search(regex, norm):
            return r["category"], 1.0

    return None
