from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis

from api.auth.deps import get_current_user
from api.cache.analyze_cache import build_analyze_cache_key, read_analyze_cache, write_analyze_cache
from api.cache.client import get_redis
from api.clause_catalog import CLAUSE_CATALOG
from api.db.models import User
from api.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from api.services.analyzer_provider import get_analyzer_state
from api.settings import Settings, get_settings

router = APIRouter(tags=["analysis"])


@router.get("/clause-categories", response_model=list[dict])
def list_clause_categories() -> list[dict]:
    return [
        {"name": entry.name, "risk_level": entry.risk_level.value, "question": entry.question}
        for entry in CLAUSE_CATALOG
    ]


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"model": ErrorResponse},
    },
)
async def analyze_contract(
    request: AnalyzeRequest,
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis),
    _: User = Depends(get_current_user),
) -> AnalyzeResponse:
    if len(request.document_text) > settings.max_document_characters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"document_text exceeds {settings.max_document_characters} characters; "
                "use the asynchronous analysis workflow for larger contracts"
            ),
        )

    cache_key = build_analyze_cache_key(request, settings)
    cached_response = await read_analyze_cache(redis, cache_key)
    if cached_response is not None:
        return cached_response

    try:
        response = get_analyzer_state(settings).analyzer.analyze(request)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    response.cached = False
    await write_analyze_cache(redis, cache_key, response, settings.analyze_cache_ttl_seconds)
    return response
