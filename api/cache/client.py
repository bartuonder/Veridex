from __future__ import annotations

import os

from fastapi import Request
from redis.asyncio import Redis

from api.settings import get_settings


def resolve_redis_url() -> str:
    explicit = os.environ.get("REDIS_URL")
    return explicit if explicit else get_settings().redis_url


def create_redis_client(url: str | None = None) -> Redis:
    return Redis.from_url(url or resolve_redis_url(), decode_responses=True)


async def close_redis_client(client: Redis) -> None:
    await client.aclose()


def get_redis(request: Request) -> Redis:
    return request.app.state.redis
