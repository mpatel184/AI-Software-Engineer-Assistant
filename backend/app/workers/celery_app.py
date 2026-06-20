"""Celery application for background jobs (clone, index, analyze, generate)."""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(debug=settings.debug, json_logs=settings.is_production)

celery_app = Celery(
    "ai_swe_assistant",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)
