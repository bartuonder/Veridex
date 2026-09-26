from __future__ import annotations

import math
import re
import string
from collections import Counter
from typing import Any

from training.postprocess import SpanPrediction


def normalize_answer(text: str) -> str:
    text = text.lower()
    text = "".join(character for character in text if character not in set(string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def compute_exact(prediction: str, gold: str) -> float:
    return float(normalize_answer(prediction) == normalize_answer(gold))


def compute_token_f1(prediction: str, gold: str) -> float:
    prediction_tokens = normalize_answer(prediction).split()
    gold_tokens = normalize_answer(gold).split()
    if not prediction_tokens or not gold_tokens:
        return float(prediction_tokens == gold_tokens)
    common = Counter(prediction_tokens) & Counter(gold_tokens)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(prediction_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def best_score_against_golds(prediction: str, gold_texts: list[str], scorer) -> float:
    if not gold_texts:
        return float(prediction.strip() == "")
    return max(scorer(prediction, gold) for gold in gold_texts)


def compute_squad_metrics(predictions: list[SpanPrediction]) -> dict[str, float]:
    exact_scores: list[float] = []
    f1_scores: list[float] = []
    answerable_exact: list[float] = []
    answerable_f1: list[float] = []
    unanswerable_exact: list[float] = []

    for prediction in predictions:
        exact = best_score_against_golds(prediction.predicted_text, prediction.gold_texts, compute_exact)
        f1 = best_score_against_golds(prediction.predicted_text, prediction.gold_texts, compute_token_f1)
        exact_scores.append(exact)
        f1_scores.append(f1)
        if prediction.is_answerable:
            answerable_exact.append(exact)
            answerable_f1.append(f1)
        else:
            unanswerable_exact.append(exact)

    return {
        "exact_match": _percentage(exact_scores),
        "f1": _percentage(f1_scores),
        "has_answer_exact_match": _percentage(answerable_exact),
        "has_answer_f1": _percentage(answerable_f1),
        "no_answer_accuracy": _percentage(unanswerable_exact),
        "answerable_count": float(len(answerable_f1)),
        "unanswerable_count": float(len(unanswerable_exact)),
    }


def compute_recall_at_high_precision(
    predictions: list[SpanPrediction],
    target_precision: float,
    span_match_f1_threshold: float,
) -> dict[str, float]:
    scored = [
        (
            prediction.score_diff if math.isfinite(prediction.score_diff) else math.inf,
            prediction.is_answerable
            and best_score_against_golds(prediction.best_span_text, prediction.gold_texts, compute_token_f1)
            >= span_match_f1_threshold,
        )
        for prediction in predictions
    ]
    total_answerable = sum(1 for prediction in predictions if prediction.is_answerable)
    if total_answerable == 0:
        return {
            "recall_at_high_precision": 0.0,
            "recall_at_high_precision_threshold": 0.0,
            "precision_at_high_precision_point": 0.0,
        }

    scored.sort(key=lambda item: item[0])

    best_recall = 0.0
    best_threshold = 0.0
    best_precision = 0.0
    true_positives = 0

    for position, (score_diff, is_correct_span) in enumerate(scored, start=1):
        true_positives += int(is_correct_span)
        precision = true_positives / position
        recall = true_positives / total_answerable
        if precision >= target_precision and recall > best_recall:
            best_recall = recall
            best_threshold = float(score_diff)
            best_precision = precision

    return {
        "recall_at_high_precision": round(best_recall * 100.0, 4),
        "recall_at_high_precision_threshold": round(best_threshold, 4),
        "precision_at_high_precision_point": round(best_precision * 100.0, 4),
    }


def compute_all_metrics(
    predictions: list[SpanPrediction],
    metrics_config: dict[str, Any],
) -> dict[str, float]:
    metrics = compute_squad_metrics(predictions)
    metrics.update(
        compute_recall_at_high_precision(
            predictions,
            metrics_config["high_precision_target"],
            metrics_config["span_match_f1_threshold"],
        )
    )
    return metrics


def collect_error_samples(predictions: list[SpanPrediction], limit: int) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for prediction in predictions:
        f1 = best_score_against_golds(prediction.predicted_text, prediction.gold_texts, compute_token_f1)
        if f1 >= 1.0:
            continue
        errors.append(
            {
                "example_id": prediction.example_id,
                "contract": prediction.title,
                "clause_question": prediction.question,
                "gold_text": prediction.gold_texts[0] if prediction.gold_texts else "",
                "predicted_text": prediction.predicted_text,
                "best_span_text": prediction.best_span_text,
                "token_f1": round(f1, 4),
                "score_diff": round(prediction.score_diff, 4),
                "error_type": _classify_error(prediction, f1),
            }
        )
    errors.sort(key=lambda item: item["token_f1"])
    return errors[:limit]


def _classify_error(prediction: SpanPrediction, f1: float) -> str:
    if prediction.is_answerable and prediction.predicted_text.strip() == "":
        return "missed_clause"
    if not prediction.is_answerable and prediction.predicted_text.strip() != "":
        return "false_clause"
    if f1 == 0.0:
        return "wrong_span"
    return "partial_span"


def _percentage(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return round(100.0 * sum(scores) / len(scores), 4)
