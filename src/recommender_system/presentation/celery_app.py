"""
Celery-приложение для асинхронных задач (ЛР4).

Broker и result backend — Redis. URL задаётся переменной окружения REDIS_URL.

Для pytest без Redis: установите CELERY_EAGER_TEST=1 (см. tests/conftest.py) —
используются memory:// + rpc:// и eager-режим, чтобы AsyncResult работал без брокера.
"""
from __future__ import annotations

import os

from celery import Celery

from ..env import load_project_env

# Redis, MinIO и прочие ключи — из `.env` в корне проекта (и из окружения ОС / Docker).
load_project_env()


def _is_pytest_eager_mode() -> bool:
    return os.getenv("CELERY_EAGER_TEST", "").lower() in ("1", "true", "yes")


if _is_pytest_eager_mode():
    # Без реального Redis: eager + SQLite backend (sqlalchemy) для AsyncResult в тестах.
    _broker_url = "memory://"
    _result_backend = "db+sqlite:///./.pytest_celery.sqlite"
else:
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _broker_url = _result_backend = _redis_url

celery_app = Celery(
    "recommender_system",
    broker=_broker_url,
    backend=_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=_is_pytest_eager_mode(),
    task_eager_propagates=False,
    task_store_eager_result=_is_pytest_eager_mode(),
)

# Регистрация задач (side-effect: декораторы @celery_app.task)
from . import tasks  # noqa: E402, F401
