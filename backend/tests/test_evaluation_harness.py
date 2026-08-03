from __future__ import annotations
import pytest
from app.evaluation.calibration import (
    compute_ece,
    evaluate_verdict_precision_recall,
    evaluate_evidence_relevance,
)

def test_compute_ece_empty_db():
    ece = compute_ece("scrutin.db")
    assert isinstance(ece, float)
    assert 0.0 <= ece <= 1.0

def test_evaluate_verdict_precision_recall():
    predictions = [
        ("true", "true"),
        ("false", "false"),
        ("true", "false"),
        ("misleading", "misleading"),
    ]
    metrics = evaluate_verdict_precision_recall(predictions)
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert metrics["accuracy"] == 0.75

def test_evaluate_evidence_relevance():
    claim = "The Eiffel Tower was built in Paris in 1889."
    evidence = [
        "The Eiffel Tower is a landmark in Paris constructed for the 1889 Exposition.",
        "Random unrelated text snippet about dogs.",
    ]
    relevance = evaluate_evidence_relevance(claim, evidence)
    assert 0.0 <= relevance <= 1.0
    assert relevance > 0.2
