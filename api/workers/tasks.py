from __future__ import annotations

from celery.signals import worker_ready

from api.cache.analyze_cache import (
    build_analyze_cache_key,
    read_analyze_cache_sync,
    write_analyze_cache_sync,
)
from api.cache.client import create_sync_redis_client
from api.db.models import AnalysisResult
from api.db.session import get_session_factory
from api.schemas import AnalyzeRequest
from api.services.analyzer_provider import get_analyzer_state, initialise_analyzer
from api.settings import get_settings
from api.workers.celery_app import celery_app
from api.workers.jobs import load_analysis, mark_completed, mark_failed, mark_processing


@worker_ready.connect
def load_analyzer_on_worker_ready(**_: object) -> None:
    initialise_analyzer(get_settings())


@celery_app.task(bind=True, name="veridex.analyze_document")
def analyze_document(self, payload: dict) -> dict:
    settings = get_settings()
    session = get_session_factory()()
    analysis = load_analysis(session, payload["analysis_result_id"])
    if analysis is None:
        session.close()
        raise ValueError(f"AnalysisResult {payload['analysis_result_id']} was not found")

    try:
        mark_processing(session, analysis)
        request = AnalyzeRequest.model_validate(payload["request"])
        cache_key = build_analyze_cache_key(request, settings)
        redis = create_sync_redis_client()
        cached = read_analyze_cache_sync(redis, cache_key)
        if cached is not None:
            mark_completed(session, analysis, cached)
            redis.close()
            return cached.model_dump(mode="json")

        response = get_analyzer_state(settings).analyzer.analyze(request)
        response.cached = False
        write_analyze_cache_sync(redis, cache_key, response, settings.analyze_cache_ttl_seconds)
        redis.close()
        mark_completed(session, analysis, response)
        return response.model_dump(mode="json")
    except Exception as error:
        refreshed = session.get(AnalysisResult, analysis.id)
        if refreshed is not None:
            mark_failed(session, refreshed, f"{type(error).__name__}: {error}")
        raise
    finally:
        session.close()
