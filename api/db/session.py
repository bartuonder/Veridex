from __future__ import annotations

import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from api.settings import get_settings

SYNC_PSYCOPG_PREFIX = "postgresql+psycopg://"
ASYNC_PSYCOPG_PREFIX = "postgresql+psycopg_async://"
GENERIC_POSTGRES_PREFIX = "postgresql://"


def resolve_database_url() -> str:
    explicit = os.environ.get("DATABASE_URL")
    url = explicit if explicit else get_settings().database_url
    if url.startswith(GENERIC_POSTGRES_PREFIX) and not url.startswith(SYNC_PSYCOPG_PREFIX):
        return SYNC_PSYCOPG_PREFIX + url[len(GENERIC_POSTGRES_PREFIX) :]
    if url.startswith(ASYNC_PSYCOPG_PREFIX):
        return SYNC_PSYCOPG_PREFIX + url[len(ASYNC_PSYCOPG_PREFIX) :]
    return url


def resolve_async_database_url() -> str:
    url = resolve_database_url()
    if url.startswith(SYNC_PSYCOPG_PREFIX):
        return ASYNC_PSYCOPG_PREFIX + url[len(SYNC_PSYCOPG_PREFIX) :]
    if url.startswith(GENERIC_POSTGRES_PREFIX):
        return ASYNC_PSYCOPG_PREFIX + url[len(GENERIC_POSTGRES_PREFIX) :]
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(resolve_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    return create_async_engine(resolve_async_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@lru_cache(maxsize=1)
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_async_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
