"""Общие фикстуры pytest."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_celery_singleton_caches() -> None:
    """Изолирует тесты, использующие lru_cache в задачах."""
    from src.recommender_system.presentation import tasks as task_mod

    task_mod._get_recommendation_service_singleton.cache_clear()
    yield
    task_mod._get_recommendation_service_singleton.cache_clear()
