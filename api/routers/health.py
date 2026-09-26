from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from api.schemas import HealthResponse, ModelStatus
from api.settings import Settings, get_settings

router = APIRouter(tags=["system"])
PROCESS_START_MONOTONIC = time.monotonic()


@router.get("/health", response_model=HealthResponse)
def read_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
        model_status=ModelStatus.NOT_LOADED,
        registered_model_name=settings.registered_model_name,
        model_alias=settings.model_alias,
        uptime_seconds=round(time.monotonic() - PROCESS_START_MONOTONIC, 3),
    )
