from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth.deps import get_request_user
from api.cache.analyze_cache import build_analyze_cache_key, read_analyze_cache
from api.cache.client import get_redis
from api.clause_catalog import CLAUSE_CATALOG, select_categories
from api.db.models import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_PENDING,
    AnalysisResult,
    Document,
    User,
)
from api.db.session import get_db
from api.schemas import (
    AnalyzeJobAccepted,
    AnalyzeJobStatus,
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
)
from api.settings import Settings, get_settings
from api.workers.jobs import mark_completed
from api.workers.tasks import analyze_document

router = APIRouter(tags=["analysis"])


@router.get("/clause-categories", response_model=list[dict])
def list_clause_categories() -> list[dict]:
    return [
        {"name": entry.name, "risk_level": entry.risk_level.value, "question": entry.question}
        for entry in CLAUSE_CATALOG
    ]


@router.post(
    "/analyze",
    response_model=AnalyzeJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
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
    session: Session = Depends(get_db),
    user: User = Depends(get_request_user),
) -> AnalyzeJobAccepted:
    if len(request.document_text) > settings.max_document_characters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"document_text exceeds {settings.max_document_characters} characters; "
                "use the asynchronous analysis workflow for larger contracts"
            ),
        )

    try:
        select_categories(request.clause_categories)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    job_id = str(uuid.uuid4())
    document = Document(user_id=user.id, filename=request.document_name, status=JOB_STATUS_PENDING)
    session.add(document)
    session.flush()
    analysis = AnalysisResult(
        document_id=document.id,
        model_version=settings.model_source,
        threshold_used=settings.null_score_diff_threshold,
        job_id=job_id,
        status=JOB_STATUS_PENDING,
    )
    session.add(analysis)
    session.flush()

    cache_key = build_analyze_cache_key(request, settings)
    cached_response = await read_analyze_cache(redis, cache_key)
    if cached_response is not None:
        mark_completed(session, analysis, cached_response)
        return AnalyzeJobAccepted(job_id=job_id, status=JOB_STATUS_COMPLETED, cached=True)

    session.commit()
    analyze_document.apply_async(
        args=[{"analysis_result_id": str(analysis.id), "request": request.model_dump(mode="json")}],
        task_id=job_id,
    )
    return AnalyzeJobAccepted(job_id=job_id, status=JOB_STATUS_PENDING, cached=False)


@router.get(
    "/analyze/{job_id}",
    response_model=AnalyzeJobStatus,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def read_analyze_job(
    job_id: str,
    session: Session = Depends(get_db),
    user: User = Depends(get_request_user),
) -> AnalyzeJobStatus:
    analysis = session.scalar(select(AnalysisResult).where(AnalysisResult.job_id == job_id))
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    if analysis.document.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Analysis job not found")

    result = (
        AnalyzeResponse.model_validate_json(analysis.result_payload)
        if analysis.result_payload is not None
        else None
    )
    return AnalyzeJobStatus(
        job_id=analysis.job_id,
        status=analysis.status,
        cached=bool(result.cached) if result is not None else False,
        result=result,
        error=analysis.error_message,
    )
