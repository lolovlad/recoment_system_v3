"""
Celery-приложение для асинхронных задач (ЛР4).

Broker и result backend — Redis. URL задаётся переменной окружения REDIS_URL.
"""
from __future__ import annotations

import os

from celery import Celery

from ..env import load_project_env

# Redis, MinIO и прочие ключи — из `.env` в корне проекта (и из окружения ОС / Docker).
load_project_env()
_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "recommender_system",
    broker=_redis_url,
    backend=_redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Регистрация задач (side-effect: декораторы @celery_app.task)
from . import tasks  # noqa: E402, F401
