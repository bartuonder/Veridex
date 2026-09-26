from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field

ENVIRONMENT_PREFIX = "VERIDEX_"


class Settings(BaseModel):
    app_name: str = "Veridex Clause Analysis API"
    app_version: str = "0.1.0"
    max_document_characters: int = Field(default=500_000, gt=0)
    chunk_characters: int = Field(default=4_000, gt=0)
    chunk_overlap_characters: int = Field(default=400, ge=0)
    registered_model_name: str = "Veridex-QA"
    model_alias: str = "staging"

    @classmethod
    def from_environment(cls) -> "Settings":
        overrides = {
            field_name: os.environ[f"{ENVIRONMENT_PREFIX}{field_name.upper()}"]
            for field_name in cls.model_fields
            if f"{ENVIRONMENT_PREFIX}{field_name.upper()}" in os.environ
        }
        return cls(**overrides)


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
