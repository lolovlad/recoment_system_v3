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


def test_delivery_task_returns_float(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path
    from tempfile import TemporaryDirectory

    import numpy as np
    from sklearn.linear_model import LinearRegression
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    with TemporaryDirectory() as td:
        model_path = Path(td) / "delivery_estimator.onnx"
        rng = np.random.default_rng(0)
        X = rng.normal(0, 1, size=(50, 4)).astype(np.float32)
        y = (X @ np.ones(4, dtype=np.float32)).astype(np.float32)
        lr = LinearRegression()
        lr.fit(X, y)
        onnx_model = convert_sklearn(
            lr,
            initial_types=[("float_input", FloatTensorType([None, 4]))],
            target_opset=12,
        )
        model_path.write_bytes(onnx_model.SerializeToString())

        monkeypatch.setenv("MODEL_PATH", str(model_path))
        for key in ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"):
            monkeypatch.delenv(key, raising=False)
        task_mod._get_inference_service_singleton.cache_clear()

        from src.recommender_system.presentation.tasks import estimate_delivery_task

        payload = {"distance": 5.0, "hour": 10, "day_of_week": 2, "items_count": 2}
        res = estimate_delivery_task.apply(args=(payload,))
        assert res.successful()
        assert isinstance(res.result, (int, float))
