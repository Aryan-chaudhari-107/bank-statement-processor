"""Hybrid classifier combining deterministic rules with machine learning inference."""

from typing import Any

from src.classifier.ml_classifier import predict
from src.classifier.rule_engine import classify as rule_classify

ML_THRESHOLD = 0.25


def classify_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify transaction rows: rule-first (conf 1.0), ML fallback (conf >= ML_THRESHOLD), else 'Other'."""
    classified: list[dict[str, Any]] = []

    for raw in rows:
        row = dict(raw)
        desc = str(row.get("description", ""))
        is_credit = float(row.get("credit", 0.0) or 0.0) > 0.0

        rule_match = rule_classify(desc, is_credit=is_credit)
        if rule_match is not None:
            cat, conf = rule_match
            row["category"] = cat
            row["confidence"] = conf
            row["method"] = "rule"
        else:
            cat, prob = predict(desc)
            if prob >= ML_THRESHOLD:
                row["category"] = cat
                row["confidence"] = round(prob, 2)
                row["method"] = "ml"
            else:
                row["category"] = "Other"
                row["confidence"] = round(prob, 2)
                row["method"] = "none"

        classified.append(row)

    return classified
