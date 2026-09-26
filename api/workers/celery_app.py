from __future__ import annotations

import os

from celery import Celery

from api.cache.client import resolve_redis_url
from api.settings import get_settings


def resolve_rabbitmq_url() -> str:
    explicit = os.environ.get("RABBITMQ_URL")
    return explicit if explicit else get_settings().rabbitmq_url


def resolve_result_backend() -> str:
    return resolve_redis_url()


def create_celery_app() -> Celery:
    application = Celery("veridex")
    application.conf.update(
        broker_url=resolve_rabbitmq_url(),
        result_backend=resolve_result_backend(),
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        result_expires=86_400,
    )
    return application


celery_app = create_celery_app()
