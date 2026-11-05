"""Machine learning inference engine for transaction classification."""

from pathlib import Path
from typing import Any

import joblib
import numpy as np

from src.classifier.cleaner import clean_description
from src.classifier.train import train_model

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "classifier.pkl"
_MODEL: Any = None


def load_model(model_path: str | Path | None = None) -> Any:
    """Load model once from disk; train automatically if missing."""
    global _MODEL
    if _MODEL is not None and model_path is None:
        return _MODEL

    path = Path(model_path) if model_path else MODEL_PATH
    if not path.exists():
        train_model(model_path=path)

    loaded = joblib.load(path)
    if model_path is None:
        _MODEL = loaded
    return loaded


def predict(
    description: str,
    model_path: str | Path | None = None,
) -> tuple[str, float]:
    """Predict transaction category and associated probability using character n-gram TF-IDF model."""
    model = load_model(model_path=model_path)
    cleaned = clean_description(description)["cleaned"]
    if not cleaned:
        return "Other", 0.0

    probs = model.predict_proba([cleaned])[0]
    best_idx = int(np.argmax(probs))
    category = str(model.classes_[best_idx])
    probability = float(probs[best_idx])

    return category, probability
