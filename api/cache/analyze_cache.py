from __future__ import annotations

import hashlib
import json

from redis.asyncio import Redis

from api.schemas import AnalyzeRequest, AnalyzeResponse
from api.settings import Settings

CACHE_KEY_PREFIX = "veridex:analyze"


def hash_document_text(document_text: str) -> str:
    return hashlib.sha256(document_text.encode("utf-8")).hexdigest()


def build_analyze_cache_key(request: AnalyzeRequest, settings: Settings) -> str:
    document_digest = hash_document_text(request.document_text)
    qualifier = json.dumps(
        {
            "categories": request.clause_categories or [],
            "threshold": settings.null_score_diff_threshold,
            "model_source": settings.model_source,
            "registered_model_name": settings.registered_model_name,
            "model_alias": settings.model_alias,
            "local_model_path": settings.local_model_path,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    qualifier_digest = hashlib.sha256(qualifier.encode("utf-8")).hexdigest()[:16]
    return f"{CACHE_KEY_PREFIX}:{document_digest}:{qualifier_digest}"


async def read_analyze_cache(client: Redis, cache_key: str) -> AnalyzeResponse | None:
    try:
        raw = await client.get(cache_key)
    except Exception:
        return None
    if raw is None:
        return None
    response = AnalyzeResponse.model_validate_json(raw)
    response.cached = True
    return response


async def write_analyze_cache(
    client: Redis,
    cache_key: str,
    response: AnalyzeResponse,
    ttl_seconds: int,
) -> None:
    payload = response.model_copy(update={"cached": False})
    try:
        await client.set(cache_key, payload.model_dump_json(), ex=ttl_seconds)
    except Exception:
        return
