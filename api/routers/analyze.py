from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.clause_catalog import CLAUSE_CATALOG
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
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"model": ErrorResponse},
    },
)
def analyze_contract(
    request: AnalyzeRequest,
    settings: Settings = Depends(get_settings),
) -> AnalyzeResponse:
    if len(request.document_text) > settings.max_document_characters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"document_text exceeds {settings.max_document_characters} characters; "
                "use the asynchronous analysis workflow for larger contracts"
            ),
        )

    try:
        return get_analyzer_state(settings).analyzer.analyze(request)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
