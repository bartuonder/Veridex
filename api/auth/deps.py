from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from api.auth.tokens import ACCESS_TOKEN_TYPE, decode_token
from api.db.models import User
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
