from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["dataset"]["cache_dir"] = str(resolve_path(config["dataset"]["cache_dir"]))
    config["training"]["output_dir"] = str(resolve_path(config["training"]["output_dir"]))
    return config


def resolve_path(relative_or_absolute: str | Path) -> Path:
    path = Path(relative_or_absolute)
    return path if path.is_absolute() else PROJECT_ROOT / path


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def flatten_for_logging(config: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in config.items():
        composite_key = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten_for_logging(value, prefix=f"{composite_key}."))
        elif isinstance(value, list):
            flat[composite_key] = ",".join(str(item) for item in value)
        else:
            flat[composite_key] = value
    return flat
