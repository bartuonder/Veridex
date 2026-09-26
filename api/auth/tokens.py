from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from api.settings import Settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    return _encode_token(
        user_id,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.access_token_expire_minutes),
        settings,
    )


def create_refresh_token(user_id: uuid.UUID, settings: Settings) -> str:
    return _encode_token(
        user_id,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.refresh_token_expire_days),
        settings,
    )


def decode_token(token: str, settings: Settings) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def _encode_token(
    user_id: uuid.UUID,
    token_type: str,
    lifetime: timedelta,
    settings: Settings,
) -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": issued_at,
        "exp": issued_at + lifetime,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
