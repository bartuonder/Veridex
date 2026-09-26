from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import mlflow
import torch
from transformers import (
    AutoModelForQuestionAnswering,
    AutoTokenizer,
    Trainer,
    TrainerCallback,
    TrainingArguments,
    default_data_collator,
)

from training.config import (
    apply_overrides,
    flatten_for_logging,
    load_config,
    resolve_path,
    set_global_seed,
)
from training.data import build_eval_features, build_train_features, load_cuad_splits
from training.metrics import collect_error_samples, compute_all_metrics
from training.postprocess import postprocess_qa_predictions

POSTPROCESSING_ONLY_COLUMNS = ["example_id", "offset_mapping"]
MASTER_WEIGHT_DTYPE = torch.float32


class MlflowLoggingCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if not logs or mlflow.active_run() is None:
            return
        numeric_logs = {
            key: float(value)
            for key, value in logs.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        if numeric_logs:
            mlflow.log_metrics(numeric_logs, step=state.global_step)


class QuestionAnsweringTrainer(Trainer):
    def __init__(self, *args, eval_examples=None, eval_features=None, post_process_function=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.eval_examples = eval_examples
        self.eval_features = eval_features
        self.post_process_function = post_process_function
        self.latest_predictions = None

    def evaluate(self, eval_dataset=None, ignore_keys=None, metric_key_prefix="eval"):
        dataset = eval_dataset if eval_dataset is not None else self.eval_dataset
        dataloader = self.get_eval_dataloader(dataset)

        original_compute_metrics = self.compute_metrics
        self.compute_metrics = None
        try:
            output = self.evaluation_loop(
                dataloader,
                description="Evaluation",
                prediction_loss_only=False,
                ignore_keys=ignore_keys,
                metric_key_prefix=metric_key_prefix,
            )
        finally:
            self.compute_metrics = original_compute_metrics

        metrics = dict(output.metrics or {})
        if self.post_process_function is not None:
            predictions, span_metrics = self.post_process_function(
                self.eval_examples, self.eval_features, output.predictions
            )
            self.latest_predictions = predictions
            for key, value in span_metrics.items():
                metrics[f"{metric_key_prefix}_{key}"] = value

        self.log(metrics)
        self.control = self.callback_handler.on_evaluate(self.args, self.state, self.control, metrics)
        return metrics


SQLITE_URI_PREFIX = "sqlite:///"


def resolve_tracking_uri(tracking_uri: str) -> str:
    if not tracking_uri.startswith(SQLITE_URI_PREFIX):
        return tracking_uri
    database_path = tracking_uri[len(SQLITE_URI_PREFIX) :]
    if Path(database_path).is_absolute():
        return tracking_uri
    return SQLITE_URI_PREFIX + resolve_path(database_path).as_posix()


def configure_mlflow(mlflow_config: dict[str, Any]) -> None:
    mlflow.set_tracking_uri(resolve_tracking_uri(mlflow_config["tracking_uri"]))
    experiment_name = mlflow_config["experiment_name"]
    if mlflow.get_experiment_by_name(experiment_name) is None:
        artifact_root = resolve_path(mlflow_config["artifact_location"])
        artifact_root.mkdir(parents=True, exist_ok=True)
        mlflow.create_experiment(experiment_name, artifact_location=artifact_root.as_uri())
    mlflow.set_experiment(experiment_name)


def resolve_precision_flags(requested: str) -> dict[str, bool]:
    if not torch.cuda.is_available():
        return {}
    if requested == "bf16" or (requested == "auto" and torch.cuda.is_bf16_supported()):
        return {"bf16": True}
    if requested in ("fp16", "auto"):
        return {"fp16": True}
    return {}


def build_training_arguments(config: dict[str, Any], run_name: str) -> TrainingArguments:
    training_config = dict(config["training"])
    precision_flags = resolve_precision_flags(training_config.pop("precision"))
    return TrainingArguments(
        run_name=run_name,
        seed=config["seed"],
        load_best_model_at_end=True,
        report_to=[],
        remove_unused_columns=True,
        **training_config,
        **precision_flags,
    )


def make_post_process_function(config: dict[str, Any]):
    def post_process(examples, features, raw_predictions):
        start_logits, end_logits = raw_predictions[0], raw_predictions[1]
        predictions = postprocess_qa_predictions(
            examples, features, start_logits, end_logits, config["postprocessing"]
        )
        return predictions, compute_all_metrics(predictions, config["metrics"])

    return post_process


def log_error_artifacts(predictions, config: dict[str, Any], artifact_name: str) -> None:
    if not config["mlflow"]["log_error_artifacts"]:
        return
    errors = collect_error_samples(predictions, config["mlflow"]["max_error_samples"])
    artifact_path = resolve_path(config["training"]["output_dir"]) / artifact_name
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(errors, handle, indent=2, ensure_ascii=False)
    mlflow.log_artifact(str(artifact_path), artifact_path="error_analysis")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune Veridex clause extraction model on CUAD")
    parser.add_argument("--config", default=None)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--override", nargs="*", default=[])
    arguments = parser.parse_args()

    config = apply_overrides(load_config(arguments.config), arguments.override)
    set_global_seed(config["seed"])

    run_name = arguments.run_name or f"deberta-v3-base-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    tokenizer = AutoTokenizer.from_pretrained(config["model"]["base_checkpoint"])
    splits = load_cuad_splits(config["dataset"], config["seed"])

    train_features = build_train_features(
        splits["train"], tokenizer, config["model"], config["preprocessing"], config["seed"]
    )
    eval_features = build_eval_features(
        splits["validation"], tokenizer, config["model"], config["preprocessing"]
    )
    model_input_eval_features = eval_features.remove_columns(POSTPROCESSING_ONLY_COLUMNS)

    model = AutoModelForQuestionAnswering.from_pretrained(
        config["model"]["base_checkpoint"], dtype=MASTER_WEIGHT_DTYPE
    )

    training_arguments = build_training_arguments(config, run_name)
    trainer = QuestionAnsweringTrainer(
        model=model,
        args=training_arguments,
        train_dataset=train_features,
        eval_dataset=model_input_eval_features,
        processing_class=tokenizer,
        data_collator=default_data_collator,
        callbacks=[MlflowLoggingCallback()],
        eval_examples=splits["validation"],
        eval_features=eval_features,
        post_process_function=make_post_process_function(config),
    )

    configure_mlflow(config["mlflow"])

    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(flatten_for_logging(config))
        mlflow.log_params(
            {
                "train_examples": len(splits["train"]),
                "train_features": len(train_features),
                "validation_examples": len(splits["validation"]),
                "validation_features": len(eval_features),
                "precision": "bf16" if training_arguments.bf16 else ("fp16" if training_arguments.fp16 else "fp32"),
                "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
            }
        )
        mlflow.log_artifact(str(resolve_path("training/config.yaml")), artifact_path="config")

        trainer.train()

        final_metrics = trainer.evaluate()
        mlflow.log_metrics({f"best_{key}": value for key, value in final_metrics.items() if isinstance(value, (int, float))})
        log_error_artifacts(trainer.latest_predictions, config, "validation_error_samples.json")

        best_model_directory = resolve_path(config["training"]["output_dir"]) / "best-model"
        trainer.save_model(str(best_model_directory))
        tokenizer.save_pretrained(str(best_model_directory))

        metrics_path = best_model_directory / "validation_metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as handle:
            json.dump(final_metrics, handle, indent=2)
        mlflow.log_artifact(str(metrics_path), artifact_path="metrics")

        print(json.dumps(final_metrics, indent=2))


if __name__ == "__main__":
    main()
