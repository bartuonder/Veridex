from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ENVIRONMENT_PREFIX = "VERIDEX_"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, protected_namespaces=())

    app_name: str = "Veridex Clause Analysis API"
    app_version: str = "0.2.0"
    max_document_characters: int = Field(default=500_000, gt=0)
    chunk_characters: int = Field(default=4_000, gt=0)
    chunk_overlap_characters: int = Field(default=400, ge=0)

    model_source: Literal["registry", "local", "mock"] = "registry"
    registered_model_name: str = "Veridex-QA"
    model_alias: str = "staging"
    local_model_path: str = "outputs/veridex-qa/best-model"
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"

    max_seq_length: int = Field(default=384, gt=0)
    doc_stride: int = Field(default=128, ge=0)
    max_answer_length: int = Field(default=256, gt=0)
    n_best_size: int = Field(default=20, gt=0)
    null_score_diff_threshold: float = -5.0
    inference_batch_size: int = Field(default=16, gt=0)
    inference_device: Literal["auto", "cuda", "cpu"] = "auto"
    database_url: str = "postgresql+psycopg://veridex:veridex@localhost:5432/veridex"

    @classmethod
    def from_environment(cls) -> "Settings":
        overrides = {
            field_name: os.environ[f"{ENVIRONMENT_PREFIX}{field_name.upper()}"]
            for field_name in cls.model_fields
            if f"{ENVIRONMENT_PREFIX}{field_name.upper()}" in os.environ
        }
        if "DATABASE_URL" in os.environ:
            overrides["database_url"] = os.environ["DATABASE_URL"]
        return cls(**overrides)


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
