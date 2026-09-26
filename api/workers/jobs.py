from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from api.db.models import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PROCESSING,
    AnalysisResult,
    Clause,
)
from api.schemas import AnalyzeResponse


def mark_processing(session: Session, analysis: AnalysisResult) -> None:
    analysis.status = JOB_STATUS_PROCESSING
    analysis.document.status = JOB_STATUS_PROCESSING
    session.commit()


def mark_failed(session: Session, analysis: AnalysisResult, error_message: str) -> None:
    analysis.status = JOB_STATUS_FAILED
    analysis.error_message = error_message
    analysis.document.status = JOB_STATUS_FAILED
    session.commit()


def mark_completed(session: Session, analysis: AnalysisResult, response: AnalyzeResponse) -> None:
    analysis.status = JOB_STATUS_COMPLETED
    analysis.error_message = None
    analysis.model_version = response.model_source
    analysis.result_payload = response.model_dump_json()
    analysis.document.status = JOB_STATUS_COMPLETED
    for finding in response.findings:
        session.add(
            Clause(
                analysis_result_id=analysis.id,
                category=finding.category,
                text_span=finding.clause_text,
                confidence=finding.confidence,
                risk_level=finding.risk_level.value,
            )
        )
    session.commit()


def load_analysis(session: Session, analysis_result_id: str) -> AnalysisResult | None:
    analysis = session.get(AnalysisResult, uuid.UUID(analysis_result_id))
    if analysis is None:
        return None
    _ = analysis.document
    return analysis
