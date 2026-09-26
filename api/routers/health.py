from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from api.schemas import HealthResponse, ModelStatus
from api.services.analyzer_provider import peek_analyzer_state
from api.settings import Settings, get_settings

router = APIRouter(tags=["system"])
PROCESS_START_MONOTONIC = time.monotonic()


@router.get("/health", response_model=HealthResponse)
def read_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    state = peek_analyzer_state()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
        model_status=state.model_status if state is not None else ModelStatus.NOT_LOADED,
        model_source=state.model_source if state is not None else settings.model_source,
        registered_model_name=settings.registered_model_name,
        model_alias=settings.model_alias,
        null_score_diff_threshold=settings.null_score_diff_threshold,
        model_load_error=state.load_error if state is not None else None,
        uptime_seconds=round(time.monotonic() - PROCESS_START_MONOTONIC, 3),
    )
