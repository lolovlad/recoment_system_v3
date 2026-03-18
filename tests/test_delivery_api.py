from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from fastapi.testclient import TestClient
from sklearn.linear_model import LinearRegression

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType


def _write_onnx(path: Path) -> None:
    rng = np.random.default_rng(1)
    X = rng.normal(0, 1, size=(100, 4)).astype(np.float32)
    y = (X @ np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32) + 5.0).astype(np.float32)
    lr = LinearRegression()
    lr.fit(X, y)
    onnx_model = convert_sklearn(lr, initial_types=[("float_input", FloatTensorType([None, 4]))], target_opset=12)
    path.write_bytes(onnx_model.SerializeToString())


def test_api_estimate_time_returns_estimated_minutes(monkeypatch):
    # Важно: dependencies.get_inference_service кешируется через lru_cache,
    # поэтому мы импортируем модуль после установки MODEL_PATH и чистим кеш.
    with TemporaryDirectory() as td:
        model_path = Path(td) / "delivery_estimator.onnx"
        _write_onnx(model_path)

        monkeypatch.setenv("MODEL_PATH", str(model_path))
        monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
        monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
        monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
        monkeypatch.delenv("MINIO_BUCKET", raising=False)

        from src.recommender_system.presentation import dependencies as deps  # noqa: WPS433

        deps.get_inference_service.cache_clear()

        from src.recommender_system.presentation.api import app  # noqa: WPS433

        client = TestClient(app)

        resp = client.post(
            "/api/v1/delivery/estimate_time",
            json={"distance": 12.5, "hour": 18, "day_of_week": 5, "items_count": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "estimated_minutes" in data
        assert isinstance(data["estimated_minutes"], (int, float))

