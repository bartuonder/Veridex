from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth.api_keys import hash_api_key
from api.auth.tokens import ACCESS_TOKEN_TYPE, decode_token
from api.db.models import ApiKey, User
from api.db.session import get_db
from api.settings import Settings, get_settings

BEARER_PREFIX = "Bearer "


def get_access_token(authorization: str | None = Header(default=None)) -> str:
    if authorization is None or not authorization.startswith(BEARER_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len(BEARER_PREFIX) :].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def get_current_user(
    token: str = Depends(get_access_token),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    return user_from_access_token(token, session, settings)


def get_request_user(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if x_api_key is not None and x_api_key.strip():
        return user_from_api_key(x_api_key.strip(), session)
    if authorization is not None and authorization.startswith(BEARER_PREFIX):
        token = authorization[len(BEARER_PREFIX) :].strip()
        if token:
            return user_from_access_token(token, session, settings)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def user_from_access_token(token: str, session: Session, settings: Settings) -> User:
    try:
        payload = decode_token(token, settings)
    except InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = payload.get("sub")
    try:
        user_id = uuid.UUID(str(subject))
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token subject",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def user_from_api_key(raw_key: str, session: Session) -> User:
    record = session.scalar(
        select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw_key), ApiKey.is_active.is_(True))
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    record.last_used_at = datetime.now(timezone.utc)
    user = session.get(User, record.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
