from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LinearRegression

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType


def _write_onnx(path: Path) -> None:
    rng = np.random.default_rng(7)
    X = rng.normal(0, 1, size=(200, 4)).astype(np.float32)
    y = (X @ np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32) + 10.0).astype(np.float32)
    lr = LinearRegression()
    lr.fit(X, y)
    onnx_model = convert_sklearn(lr, initial_types=[("float_input", FloatTensorType([None, 4]))], target_opset=12)
    path.write_bytes(onnx_model.SerializeToString())


@pytest.fixture
def client(monkeypatch) -> TestClient:
    with TemporaryDirectory() as td:
        model_path = Path(td) / "delivery_estimator.onnx"
        _write_onnx(model_path)

        monkeypatch.setenv("MODEL_PATH", str(model_path))
        monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
        monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
        monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
        monkeypatch.delenv("MINIO_MODEL_BUCKET", raising=False)
        monkeypatch.delenv("MODEL_REMOTE_PATH", raising=False)

        from src.recommender_system.presentation import dependencies as deps

        deps.get_inference_service.cache_clear()

        from src.recommender_system.presentation.api import app

        yield TestClient(app)


def test_post_estimate_time_success(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/delivery/estimate_time",
        json={"distance": 12.5, "hour": 18, "day_of_week": 5, "items_count": 3},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload.keys()) == {"estimated_minutes"}
    assert isinstance(payload["estimated_minutes"], (int, float))


@pytest.mark.parametrize(
    "bad_payload",
    [
        # invalid types
        {"distance": "far", "hour": 18, "day_of_week": 5, "items_count": 3},
        # out of bounds hour
        {"distance": 10.0, "hour": 25, "day_of_week": 5, "items_count": 3},
        # out of bounds day_of_week
        {"distance": 10.0, "hour": 12, "day_of_week": 7, "items_count": 3},
        # invalid items_count
        {"distance": 10.0, "hour": 12, "day_of_week": 2, "items_count": 0},
        # negative distance
        {"distance": -1.0, "hour": 12, "day_of_week": 2, "items_count": 3},
        # missing field
        {"distance": 10.0, "hour": 12, "day_of_week": 2},
    ],
)
def test_post_estimate_time_validation_error(client: TestClient, bad_payload: dict) -> None:
    resp = client.post("/api/v1/delivery/estimate_time", json=bad_payload)
    assert resp.status_code == 422

