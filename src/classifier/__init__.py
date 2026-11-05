"""Classifier package."""

from src.classifier.cleaner import clean_description, detect_channel
from src.classifier.hybrid import classify_rows
from src.classifier.ml_classifier import predict
from src.classifier.rule_engine import classify
from src.classifier.train import train_model

__all__ = [
    "classify",
    "classify_rows",
    "clean_description",
    "detect_channel",
    "predict",
    "train_model",
]
