"""
ЛР4: тесты HTTP API рекомендаций (POST task_id, GET статус/результат, негативные сценарии).
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.recommender_system.presentation import api as api_mod
from src.recommender_system.presentation.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_post_generate_returns_task_id(client: TestClient) -> None:
    task_id = str(uuid.uuid4())
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        api_mod.generate_recommendations_for_user,
        "delay",
        lambda _user_id: SimpleNamespace(id=task_id),
    )
    resp = client.post("/api/v1/recommendations/generate_for_user", json={"user_id": 1})
    monkeypatch.undo()
    assert resp.status_code == 202
    data = resp.json()
    assert set(data.keys()) == {"task_id"}
    uuid.UUID(data["task_id"])  # валидный UUID


def test_get_unknown_task_id_returns_pending(client: TestClient) -> None:
    """Задача не ставилась — Celery даёт состояние PENDING."""
    random_id = str(uuid.uuid4())
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        api_mod,
        "AsyncResult",
        lambda _task_id, app=None: SimpleNamespace(state="PENDING", result=None, successful=lambda: False),
    )
    r = client.get(f"/api/v1/recommendations/results/{random_id}")
    monkeypatch.undo()
    assert r.status_code == 200
    body = r.json()
    assert body["task_id"] == random_id
    assert body["status"] == "PENDING"
    assert body["result"] is None


def test_get_after_post_returns_success_with_result(client: TestClient) -> None:
    task_id = str(uuid.uuid4())
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        api_mod.generate_recommendations_for_user,
        "delay",
        lambda _user_id: SimpleNamespace(id=task_id),
    )
    monkeypatch.setattr(
        api_mod,
        "AsyncResult",
        lambda _task_id, app=None: SimpleNamespace(state="SUCCESS", result=[1, 2, 3], successful=lambda: True),
    )
    resp = client.post("/api/v1/recommendations/generate_for_user", json={"user_id": 1})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    r2 = client.get(f"/api/v1/recommendations/results/{task_id}")
    monkeypatch.undo()
    assert r2.status_code == 200
    body = r2.json()
    assert body["task_id"] == task_id
    assert body["status"] == "SUCCESS"
    assert body["result"] is not None
    assert isinstance(body["result"], list)
    assert len(body["result"]) <= 5
    assert all(isinstance(x, int) for x in body["result"])


def test_invalid_user_id_rejected(client: TestClient) -> None:
    r = client.post("/api/v1/recommendations/generate_for_user", json={"user_id": -1})
    assert r.status_code == 422


def test_invalid_task_id_format_returns_422(client: TestClient) -> None:
    r = client.get("/api/v1/recommendations/results/not-a-uuid")
    assert r.status_code == 422
