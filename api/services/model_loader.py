from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer

from api.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PYFUNC_ARTIFACT_KEY = "model_directory"
SQLITE_URI_PREFIX = "sqlite:///"


@dataclass(frozen=True)
class LoadedModel:
    tokenizer: object
    model: object
    device: torch.device
    source_description: str


def resolve_device(requested: str) -> torch.device:
    if requested == "cuda":
        return torch.device("cuda")
    if requested == "cpu":
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def resolve_local_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def resolve_tracking_uri(tracking_uri: str) -> str:
    if not tracking_uri.startswith(SQLITE_URI_PREFIX):
        return tracking_uri
    database_path = tracking_uri[len(SQLITE_URI_PREFIX) :]
    if Path(database_path).is_absolute():
        return tracking_uri
    return SQLITE_URI_PREFIX + resolve_local_path(database_path).as_posix()


def download_registry_model(settings: Settings) -> Path:
    import mlflow

    mlflow.set_tracking_uri(resolve_tracking_uri(settings.mlflow_tracking_uri))
    reference = f"models:/{settings.registered_model_name}@{settings.model_alias}"
    downloaded = Path(mlflow.artifacts.download_artifacts(reference))

    candidate = downloaded / "artifacts" / PYFUNC_ARTIFACT_KEY
    if (candidate / "config.json").exists():
        return candidate
    for config_file in downloaded.rglob("config.json"):
        if (config_file.parent / "model.safetensors").exists():
            return config_file.parent
    raise FileNotFoundError(f"No Hugging Face model directory found inside {downloaded}")


def resolve_model_directory(settings: Settings) -> tuple[Path, str]:
    if settings.model_source == "registry":
        directory = download_registry_model(settings)
        return directory, f"{settings.registered_model_name}@{settings.model_alias}"
    directory = resolve_local_path(settings.local_model_path)
    if not (directory / "config.json").exists():
        raise FileNotFoundError(f"No model found at {directory}")
    return directory, str(directory)


@lru_cache(maxsize=1)
def load_model(settings: Settings) -> LoadedModel:
    model_directory, source_description = resolve_model_directory(settings)
    device = resolve_device(settings.inference_device)
    tokenizer = AutoTokenizer.from_pretrained(str(model_directory))
    model = AutoModelForQuestionAnswering.from_pretrained(str(model_directory), dtype=torch.float32)
    model.to(device)
    model.eval()
    return LoadedModel(
        tokenizer=tokenizer,
        model=model,
        device=device,
        source_description=source_description,
    )
