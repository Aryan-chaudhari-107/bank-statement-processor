"""Honest evaluation of classification engine against tests/unseen_eval.csv."""

import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.classifier.hybrid import classify_rows
from src.classifier.ml_classifier import predict as ml_predict
from src.classifier.rule_engine import classify as rule_classify

EVAL_CSV = Path(__file__).parent / "unseen_eval.csv"


def evaluate_unseen_data(csv_path: Path | None = None) -> dict[str, Any]:
    """Run honest evaluation on unseen descriptions and return metrics and misclassifications."""
    path = csv_path or EVAL_CSV
    df = pd.read_csv(path)

    rule_matches = 0
    rule_correct = 0
    for _, r in df.iterrows():
        is_cr = float(r["credit"]) > 0.0
        res = rule_classify(str(r["description"]), is_credit=is_cr)
        if res is not None:
            rule_matches += 1
            if res[0] == r["expected_category"]:
                rule_correct += 1

    rule_acc = (rule_correct / rule_matches) if rule_matches > 0 else 0.0

    ml_correct = 0
    for _, r in df.iterrows():
        pred_cat, _ = ml_predict(str(r["description"]))
        if pred_cat == r["expected_category"]:
            ml_correct += 1

    ml_acc = ml_correct / len(df)

    rows = [
        {
            "date": "2025-04-01",
            "description": str(r["description"]),
            "debit": float(r["debit"]),
            "credit": float(r["credit"]),
            "balance": 10000.0,
            "category": "",
            "confidence": 0.0,
            "method": "none",
            "flag": "",
        }
        for _, r in df.iterrows()
    ]
    classified = classify_rows(rows)

    hybrid_correct = 0
    fallback_other_count = 0
    misclassified: list[dict[str, Any]] = []

    for c_row, (_, e_row) in zip(classified, df.iterrows(), strict=True):
        if c_row["category"] == "Other" and c_row["method"] == "none":
            fallback_other_count += 1

        if c_row["category"] == e_row["expected_category"]:
            hybrid_correct += 1
        else:
            misclassified.append({
                "description": c_row["description"],
                "expected": e_row["expected_category"],
                "predicted": c_row["category"],
                "method": c_row["method"],
                "confidence": c_row["confidence"],
            })

    hybrid_acc = hybrid_correct / len(df)
    fallback_pct = fallback_other_count / len(df)

    report = {
        "total_rows": len(df),
        "rule_matches": rule_matches,
        "rule_coverage": round(rule_matches / len(df), 3),
        "rule_accuracy": round(rule_acc, 3),
        "ml_accuracy": round(ml_acc, 3),
        "hybrid_accuracy": round(hybrid_acc, 3),
        "fallback_other_count": fallback_other_count,
        "fallback_other_pct": round(fallback_pct, 3),
        "misclassified": misclassified,
    }
    return report


def print_evaluation_report(report: dict[str, Any]) -> None:
    """Print structured summary of unseen evaluation metrics."""
    print("=" * 65)
    print("HONEST EVALUATION REPORT ON UNSEEN DATA (tests/unseen_eval.csv)")
    print("=" * 65)
    print(f"Total Evaluation Rows: {report['total_rows']}")
    print(
        f"Rules Alone Coverage: {report['rule_matches']}/{report['total_rows']} "
        f"({report['rule_coverage']:.1%})"
    )
    matches = report["rule_matches"]
    r_acc = report["rule_accuracy"]
    print(f"Rules Alone Accuracy (on matched rows): {round(r_acc * matches)}/{matches} ({r_acc:.1%})")
    print(f"ML Alone Accuracy (all rows): {report['ml_accuracy']:.1%}")
    print(f"Hybrid Accuracy (all rows): {report['hybrid_accuracy']:.1%}")
    print(f"Fallback to 'Other' (method=none): {report['fallback_other_count']}/{report['total_rows']} ({report['fallback_other_pct']:.1%})")
    print(f"Misclassified Rows Count: {len(report['misclassified'])}")
    print("-" * 65)
    print("Misclassified Rows Details:")
    for m in report["misclassified"]:
        print(
            f"  - [{m['method']}, conf={m['confidence']}] {m['description']}\n"
            f"      Expected:  {m['expected']}\n"
            f"      Predicted: {m['predicted']}"
        )
    print("=" * 65)


if __name__ == "__main__":
    rep = evaluate_unseen_data()
    print_evaluation_report(rep)
