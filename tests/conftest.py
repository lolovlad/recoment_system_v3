"""
Общие фикстуры pytest.

ВАЖНО: переменная CELERY_EAGER_TEST должна быть установлена до импорта celery_app
(иначе подтянется Redis). Поэтому она задаётся в pytest_configure.
"""
from __future__ import annotations

import os

import pytest


def pytest_configure() -> None:
    """Настройка до коллекции тестов: in-process Celery без Redis."""
    os.environ.setdefault("CELERY_EAGER_TEST", "1")


@pytest.fixture(autouse=True)
def _clear_celery_singleton_caches() -> None:
    """Изолирует тесты, использующие lru_cache в задачах."""
    from src.recommender_system.presentation import tasks as task_mod

    task_mod._get_recommendation_service_singleton.cache_clear()
    task_mod._get_inference_service_singleton.cache_clear()
    yield
    task_mod._get_recommendation_service_singleton.cache_clear()
    task_mod._get_inference_service_singleton.cache_clear()
