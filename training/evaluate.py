from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
from transformers import AutoModelForQuestionAnswering, AutoTokenizer, default_data_collator

from training.config import apply_overrides, load_config, resolve_path, set_global_seed
from training.data import build_eval_features, load_cuad_splits
from training.metrics import collect_error_samples, compute_all_metrics, compute_squad_metrics
from training.postprocess import SpanPrediction, postprocess_qa_predictions
from training.registry import MODEL_ARTIFACT_KEY
from training.tracking import configure_mlflow

POSTPROCESSING_ONLY_COLUMNS = ["example_id", "offset_mapping"]
CLAUSE_CATEGORY_PATTERN = re.compile(r'"([^"]+)"')
UNKNOWN_CATEGORY = "unknown"


def extract_clause_category(question: str) -> str:
    match = CLAUSE_CATEGORY_PATTERN.search(question)
    return match.group(1) if match else UNKNOWN_CATEGORY


def resolve_model_directory(model_path: str | None, registry_reference: str | None) -> Path:
    if registry_reference:
        downloaded = Path(mlflow.artifacts.download_artifacts(registry_reference))
        candidate = downloaded / "artifacts" / MODEL_ARTIFACT_KEY
        if (candidate / "config.json").exists():
            return candidate
        for config_file in downloaded.rglob("config.json"):
            if (config_file.parent / "model.safetensors").exists():
                return config_file.parent
        raise FileNotFoundError(f"No Hugging Face model directory inside {downloaded}")
    return resolve_path(model_path)


def run_inference(
    model,
    features,
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    model_inputs = features.remove_columns(POSTPROCESSING_ONLY_COLUMNS)
    model_inputs.set_format("torch")
    loader = DataLoader(model_inputs, batch_size=batch_size, collate_fn=default_data_collator)

    use_bfloat16 = device.type == "cuda" and torch.cuda.is_bf16_supported()
    start_logits: list[np.ndarray] = []
    end_logits: list[np.ndarray] = []

    model.eval()
    with torch.no_grad():
        for batch in tqdm(loader, desc="Scoring windows"):
            batch = {key: value.to(device) for key, value in batch.items()}
            if use_bfloat16:
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    outputs = model(**batch)
            else:
                outputs = model(**batch)
            start_logits.append(outputs.start_logits.float().cpu().numpy())
            end_logits.append(outputs.end_logits.float().cpu().numpy())

    return np.concatenate(start_logits, axis=0), np.concatenate(end_logits, axis=0)


def compute_category_breakdown(predictions: list[SpanPrediction]) -> list[dict[str, Any]]:
    grouped: dict[str, list[SpanPrediction]] = defaultdict(list)
    for prediction in predictions:
        grouped[extract_clause_category(prediction.question)].append(prediction)

    rows: list[dict[str, Any]] = []
    for category, items in grouped.items():
        category_metrics = compute_squad_metrics(items)
        rows.append(
            {
                "clause_category": category,
                "questions": len(items),
                "answerable": int(category_metrics["answerable_count"]),
                "f1": category_metrics["f1"],
                "exact_match": category_metrics["exact_match"],
                "has_answer_f1": category_metrics["has_answer_f1"],
            }
        )
    rows.sort(key=lambda row: row["f1"])
    return rows


def format_category_table(rows: list[dict[str, Any]], limit: int) -> str:
    header = f"{'clause_category':<48}{'n':>6}{'f1':>9}{'has_ans_f1':>12}"
    lines = [header, "-" * len(header)]
    for row in rows[:limit]:
        lines.append(
            f"{row['clause_category'][:47]:<48}{row['questions']:>6}{row['f1']:>9.2f}{row['has_answer_f1']:>12.2f}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Veridex clause extraction model on CUAD")
    parser.add_argument("--config", default=None)
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--registry-reference", default=None)
    parser.add_argument("--split", default="test", choices=["validation", "test"])
    parser.add_argument("--report-dir", default=None)
    parser.add_argument("--no-mlflow", action="store_true")
    parser.add_argument("--override", nargs="*", default=[])
    arguments = parser.parse_args()

    config = apply_overrides(load_config(arguments.config), arguments.override)
    set_global_seed(config["seed"])
    configure_mlflow(config["mlflow"])

    default_model_path = Path(config["training"]["output_dir"]) / "best-model"
    model_directory = resolve_model_directory(
        arguments.model_path or str(default_model_path), arguments.registry_reference
    )

    tokenizer = AutoTokenizer.from_pretrained(str(model_directory))
    model = AutoModelForQuestionAnswering.from_pretrained(str(model_directory), dtype=torch.float32)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    splits = load_cuad_splits(config["dataset"], config["seed"])
    examples = splits[arguments.split]
    features = build_eval_features(examples, tokenizer, config["model"], config["preprocessing"])

    start_logits, end_logits = run_inference(
        model, features, config["training"]["per_device_eval_batch_size"], device
    )
    predictions = postprocess_qa_predictions(
        examples, features, start_logits, end_logits, config["postprocessing"]
    )
    metrics = compute_all_metrics(predictions, config["metrics"])
    category_rows = compute_category_breakdown(predictions)
    error_samples = collect_error_samples(predictions, config["mlflow"]["max_error_samples"])

    report_directory = resolve_path(arguments.report_dir or Path(config["training"]["output_dir"]) / "reports")
    report_directory.mkdir(parents=True, exist_ok=True)
    metrics_file = report_directory / f"{arguments.split}_metrics.json"
    categories_file = report_directory / f"{arguments.split}_clause_categories.json"
    errors_file = report_directory / f"{arguments.split}_error_samples.json"

    for path, payload in (
        (metrics_file, metrics),
        (categories_file, category_rows),
        (errors_file, error_samples),
    ):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(f"\nVeridex evaluation on CUAD {arguments.split} split")
    print(f"model: {model_directory}")
    print(f"questions: {len(examples)} | windows: {len(features)}\n")
    for metric_name in (
        "exact_match",
        "f1",
        "has_answer_exact_match",
        "has_answer_f1",
        "no_answer_accuracy",
        "recall_at_high_precision",
        "precision_at_high_precision_point",
        "recall_at_high_precision_threshold",
    ):
        print(f"{metric_name:<36}{metrics[metric_name]:>10.4f}")

    print("\nWeakest clause categories by F1")
    print(format_category_table(category_rows, 10))
    print(f"\nreports written to {report_directory}")

    if not arguments.no_mlflow:
        with mlflow.start_run(run_name=f"evaluate-{arguments.split}-{model_directory.name}"):
            mlflow.log_params(
                {
                    "evaluated_model": str(model_directory),
                    "split": arguments.split,
                    "questions": len(examples),
                    "windows": len(features),
                    "registry_reference": arguments.registry_reference or "",
                }
            )
            mlflow.log_metrics({f"{arguments.split}_{key}": value for key, value in metrics.items()})
            mlflow.log_artifact(str(metrics_file), artifact_path="evaluation")
            mlflow.log_artifact(str(categories_file), artifact_path="evaluation")
            mlflow.log_artifact(str(errors_file), artifact_path="error_analysis")


if __name__ == "__main__":
    main()
