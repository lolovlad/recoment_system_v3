"""
ЛР4: интеграционный сценарий POST → task_id → GET → результат.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.recommender_system.presentation.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_full_recommendation_cycle(client: TestClient) -> None:
    r1 = client.post("/api/v1/recommendations/generate_for_user", json={"user_id": 42})
    assert r1.status_code == 202
    task_id = r1.json()["task_id"]

    r2 = client.get(f"/api/v1/recommendations/results/{task_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["task_id"] == task_id
    assert body["status"] == "SUCCESS"
    assert isinstance(body["result"], list)


def test_full_cycle_worker_failure_exposed_via_get(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Падение worker → GET /results возвращает FAILURE и error."""
    from src.recommender_system.presentation import tasks as task_mod

    task_mod._get_recommendation_service_singleton.cache_clear()
    mock_svc = MagicMock()
    mock_svc.get_recommendations.side_effect = RuntimeError("worker down")
    monkeypatch.setattr(task_mod, "_get_recommendation_service_singleton", lambda: mock_svc)

    r1 = client.post("/api/v1/recommendations/generate_for_user", json={"user_id": 1})
    assert r1.status_code == 202
    task_id = r1.json()["task_id"]

    r2 = client.get(f"/api/v1/recommendations/results/{task_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "FAILURE"
    assert body["result"] is None
    assert body.get("error")
