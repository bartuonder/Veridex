from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers import analyze, auth, health
from api.services.analyzer_provider import initialise_analyzer
from api.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialise_analyzer(get_settings())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="Contract clause extraction and risk flagging service",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(analyze.router)
    return app


app = create_app()
