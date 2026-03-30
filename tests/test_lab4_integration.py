"""
ЛР4: интеграционный сценарий POST → task_id → GET → результат.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.recommender_system.presentation import api as api_mod
from src.recommender_system.presentation.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_full_recommendation_cycle(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    task_id = str(uuid.uuid4())
    monkeypatch.setattr(
        api_mod.generate_recommendations_for_user,
        "delay",
        lambda _user_id: MagicMock(id=task_id),
    )
    monkeypatch.setattr(
        api_mod,
        "AsyncResult",
        lambda _task_id, app=None: MagicMock(state="SUCCESS", result=[10, 20], successful=lambda: True),
    )
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
    task_id = str(uuid.uuid4())
    monkeypatch.setattr(
        api_mod.generate_recommendations_for_user,
        "delay",
        lambda _user_id: MagicMock(id=task_id),
    )
    monkeypatch.setattr(
        api_mod,
        "AsyncResult",
        lambda _task_id, app=None: MagicMock(
            state="FAILURE",
            result=RuntimeError("worker down"),
            successful=lambda: False,
        ),
    )

    r1 = client.post("/api/v1/recommendations/generate_for_user", json={"user_id": 1})
    assert r1.status_code == 202
    task_id = r1.json()["task_id"]

    r2 = client.get(f"/api/v1/recommendations/results/{task_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "FAILURE"
    assert body["result"] is None
    assert body.get("error")
