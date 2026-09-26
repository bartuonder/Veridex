from __future__ import annotations

from pathlib import Path
from typing import Any

import mlflow

from training.config import resolve_path

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
