from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

CLS_TOKEN_INDEX = 0


@dataclass
class SpanPrediction:
    example_id: str
    question: str
    title: str
    gold_texts: list[str] = field(default_factory=list)
    predicted_text: str = ""
    best_span_text: str = ""
    best_span_score: float = 0.0
    null_score: float = 0.0
    score_diff: float = 0.0

    @property
    def is_answerable(self) -> bool:
        return len(self.gold_texts) > 0


def apply_null_threshold(
    predictions: list[SpanPrediction],
    null_score_diff_threshold: float,
) -> list[SpanPrediction]:
    for prediction in predictions:
        prediction.predicted_text = (
            "" if prediction.score_diff > null_score_diff_threshold else prediction.best_span_text
        )
    return predictions


def postprocess_qa_predictions(
    examples,
    features,
    start_logits: np.ndarray,
    end_logits: np.ndarray,
    postprocessing_config: dict[str, Any],
) -> list[SpanPrediction]:
    n_best_size = postprocessing_config["n_best_size"]
    max_answer_length = postprocessing_config["max_answer_length"]
    null_score_diff_threshold = postprocessing_config["null_score_diff_threshold"]

    example_index_by_id = {example_id: index for index, example_id in enumerate(examples["id"])}
    feature_indices_by_example = defaultdict(list)
    for feature_index, example_id in enumerate(features["example_id"]):
        feature_indices_by_example[example_index_by_id[example_id]].append(feature_index)

    contexts = examples["context"]
    questions = examples["question"]
    titles = examples["title"]
    answers = examples["answers"]
    offset_mappings = features["offset_mapping"]

    predictions: list[SpanPrediction] = []

    for example_index, example_id in enumerate(examples["id"]):
        context = contexts[example_index]
        min_null_score = None
        best_span_score = -np.inf
        best_span_text = ""

        for feature_index in feature_indices_by_example[example_index]:
            feature_start_logits = start_logits[feature_index]
            feature_end_logits = end_logits[feature_index]
            offsets = offset_mappings[feature_index]

            null_score = float(
                feature_start_logits[CLS_TOKEN_INDEX] + feature_end_logits[CLS_TOKEN_INDEX]
            )
            if min_null_score is None or null_score < min_null_score:
                min_null_score = null_score

            start_candidates = np.argsort(feature_start_logits)[-1 : -n_best_size - 1 : -1]
            end_candidates = np.argsort(feature_end_logits)[-1 : -n_best_size - 1 : -1]

            for start_index in start_candidates:
                for end_index in end_candidates:
                    if start_index >= len(offsets) or end_index >= len(offsets):
                        continue
                    if offsets[start_index] is None or offsets[end_index] is None:
                        continue
                    if end_index < start_index:
                        continue
                    if end_index - start_index + 1 > max_answer_length:
                        continue
                    score = float(feature_start_logits[start_index] + feature_end_logits[end_index])
                    if score > best_span_score:
                        best_span_score = score
                        best_span_text = context[offsets[start_index][0] : offsets[end_index][1]]

        if min_null_score is None:
            min_null_score = 0.0
        if best_span_score == -np.inf:
            best_span_score = min_null_score

        score_diff = min_null_score - best_span_score
        predictions.append(
            SpanPrediction(
                example_id=example_id,
                question=questions[example_index],
                title=titles[example_index],
                gold_texts=list(answers[example_index]["text"]),
                predicted_text="" if score_diff > null_score_diff_threshold else best_span_text,
                best_span_text=best_span_text,
                best_span_score=best_span_score,
                null_score=min_null_score,
                score_diff=score_diff,
            )
        )

    return predictions
