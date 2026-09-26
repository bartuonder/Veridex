from __future__ import annotations

from fastapi import FastAPI

from api.routers import analyze, health
from api.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="Contract clause extraction and risk flagging service",
    )
    app.include_router(health.router)
    app.include_router(analyze.router)
    return app


app = create_app()
