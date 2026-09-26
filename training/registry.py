from __future__ import annotations

from pathlib import Path
from typing import Any

import mlflow
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

LOGGED_MODEL_NAME = "model"
MODEL_ARTIFACT_KEY = "model_directory"
SELECTION_METRIC_TAG = "eval_f1"
INFERENCE_MAX_SEQ_LENGTH = 384
INFERENCE_DOC_STRIDE = 128
CONTEXT_SEQUENCE_ID = 1


class VeridexClauseExtractor(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        import torch
        from transformers import AutoModelForQuestionAnswering, AutoTokenizer

        directory = context.artifacts[MODEL_ARTIFACT_KEY]
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(directory)
        self.model = AutoModelForQuestionAnswering.from_pretrained(directory, dtype=torch.float32).eval()

    def predict(self, context, model_input, params=None):
        import pandas as pd

        records = (
            model_input.to_dict("records") if hasattr(model_input, "to_dict") else list(model_input)
        )
        return pd.DataFrame(
            [self._extract_clause(record["question"], record["context"]) for record in records]
        )

    def _extract_clause(self, question: str, contract_text: str) -> dict[str, Any]:
        encodings = self.tokenizer(
            question,
            contract_text,
            truncation="only_second",
            max_length=INFERENCE_MAX_SEQ_LENGTH,
            stride=INFERENCE_DOC_STRIDE,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            padding="max_length",
            return_tensors="pt",
        )
        window_sequence_ids = [
            encodings.sequence_ids(index) for index in range(len(encodings["input_ids"]))
        ]
        offset_mapping = encodings.pop("offset_mapping")
        encodings.pop("overflow_to_sample_mapping")

        with self.torch.no_grad():
            outputs = self.model(**encodings)

        best_score = -float("inf")
        best_text = ""
        null_score = float("inf")

        for window_index in range(outputs.start_logits.shape[0]):
            start_logits = outputs.start_logits[window_index]
            end_logits = outputs.end_logits[window_index]
            null_score = min(null_score, float(start_logits[0] + end_logits[0]))

            sequence_ids = window_sequence_ids[window_index]
            candidate_positions = [
                position
                for position, sequence_id in enumerate(sequence_ids)
                if sequence_id == CONTEXT_SEQUENCE_ID
            ]
            if not candidate_positions:
                continue

            for start_position in self._top_positions(start_logits, candidate_positions):
                for end_position in self._top_positions(end_logits, candidate_positions):
                    if end_position < start_position:
                        continue
                    score = float(start_logits[start_position] + end_logits[end_position])
                    if score > best_score:
                        best_score = score
                        character_start = int(offset_mapping[window_index][start_position][0])
                        character_end = int(offset_mapping[window_index][end_position][1])
                        best_text = contract_text[character_start:character_end]

        has_clause = best_score > null_score
        return {
            "clause_text": best_text if has_clause else "",
            "clause_found": has_clause,
            "span_score": best_score,
            "null_score": null_score,
        }

    def _top_positions(self, logits, candidate_positions: list[int], top_k: int = 20) -> list[int]:
        scores = [(float(logits[position]), position) for position in candidate_positions]
        scores.sort(reverse=True)
        return [position for _, position in scores[:top_k]]


def register_best_model(
    model_directory: Path,
    metrics: dict[str, float],
    mlflow_config: dict[str, Any],
) -> str | None:
    if mlflow.active_run() is None:
        raise RuntimeError("register_best_model requires an active MLflow run")

    registered_name = mlflow_config["registered_model_name"]
    alias = mlflow_config["staging_alias"]
    selection_metric = float(metrics.get("eval_f1", 0.0))

    logged_model = mlflow.pyfunc.log_model(
        name=LOGGED_MODEL_NAME,
        python_model=VeridexClauseExtractor(),
        artifacts={MODEL_ARTIFACT_KEY: str(model_directory)},
        pip_requirements=["torch", "transformers", "sentencepiece", "protobuf", "pandas"],
    )

    client = MlflowClient()
    model_version = mlflow.register_model(model_uri=logged_model.model_uri, name=registered_name)

    client.set_model_version_tag(
        registered_name, model_version.version, SELECTION_METRIC_TAG, selection_metric
    )
    for metric_name, metric_value in metrics.items():
        if isinstance(metric_value, (int, float)):
            client.set_model_version_tag(
                registered_name,
                model_version.version,
                f"metric.{metric_name}",
                round(float(metric_value), 4),
            )

    incumbent_score = _alias_metric(client, registered_name, alias)
    if incumbent_score is not None and incumbent_score > selection_metric:
        client.set_model_version_tag(registered_name, model_version.version, "promotion_skipped", "true")
        return None

    client.set_registered_model_alias(registered_name, alias, model_version.version)
    return model_version.version


def _alias_metric(client: MlflowClient, registered_name: str, alias: str) -> float | None:
    try:
        aliased_version = client.get_model_version_by_alias(registered_name, alias)
    except MlflowException:
        return None
    raw_value = aliased_version.tags.get(SELECTION_METRIC_TAG)
    if raw_value is None:
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def load_registered_model(registered_name: str, alias: str):
    return mlflow.pyfunc.load_model(f"models:/{registered_name}@{alias}")


def main() -> None:
    import argparse
    import json

    from training.config import load_config, resolve_path
    from training.tracking import configure_mlflow

    parser = argparse.ArgumentParser(
        description="Register an existing Veridex checkpoint in the MLflow Model Registry"
    )
    parser.add_argument("--config", default=None)
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--metrics-file", default=None)
    parser.add_argument("--run-name", default=None)
    arguments = parser.parse_args()

    config = load_config(arguments.config)
    configure_mlflow(config["mlflow"])

    model_directory = resolve_path(
        arguments.model_path or Path(config["training"]["output_dir"]) / "best-model"
    )
    metrics_path = (
        Path(arguments.metrics_file)
        if arguments.metrics_file
        else model_directory / "validation_metrics.json"
    )
    metrics: dict[str, float] = {}
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as handle:
            metrics = json.load(handle)

    with mlflow.start_run(run_name=arguments.run_name or f"register-{model_directory.name}"):
        mlflow.log_param("registered_from", str(model_directory))
        mlflow.log_metrics({key: value for key, value in metrics.items() if isinstance(value, (int, float))})
        version = register_best_model(model_directory, metrics, config["mlflow"])

    if version is None:
        print("Existing staging model has a higher eval_f1, alias left unchanged")
    else:
        print(
            f"Registered {config['mlflow']['registered_model_name']} version {version} "
            f"with alias {config['mlflow']['staging_alias']}"
        )


if __name__ == "__main__":
    main()
