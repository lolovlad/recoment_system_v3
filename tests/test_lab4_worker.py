"""
ЛР4: прямое выполнение Celery-задач (worker-логика без HTTP).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.recommender_system.presentation import tasks as task_mod


def test_generate_task_returns_list_of_ints() -> None:
    from src.recommender_system.presentation.tasks import generate_recommendations_for_user

    res = generate_recommendations_for_user.apply(args=(1,))
    assert res.successful()
    assert isinstance(res.result, list)
    assert len(res.result) <= task_mod._recommendation_top_n()
    assert all(isinstance(x, int) for x in res.result)


def test_generate_task_invalid_user_id_fails() -> None:
    from src.recommender_system.presentation.tasks import generate_recommendations_for_user

    res = generate_recommendations_for_user.apply(args=(-1,))
    assert not res.successful()


def test_generate_task_handles_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ошибка в бизнес-логике не должна «глотаться» — задача в FAILURE."""
    task_mod._get_recommendation_service_singleton.cache_clear()

    mock_svc = MagicMock()
    mock_svc.get_recommendations.side_effect = RuntimeError("simulated failure")

    monkeypatch.setattr(task_mod, "_get_recommendation_service_singleton", lambda: mock_svc)

    from src.recommender_system.presentation.tasks import generate_recommendations_for_user

    res = generate_recommendations_for_user.apply(args=(1,))
    assert not res.successful()


