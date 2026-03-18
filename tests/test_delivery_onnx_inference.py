from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest
from sklearn.linear_model import LinearRegression

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

from src.recommender_system.infrastructure.onnx_model import ONNXModel
from src.recommender_system.application.services import InferenceService


def _make_tiny_onnx_model(path: Path) -> None:
    # y = 2*distance + 1*hour + 0.5*day + 3*items + 10
    rng = np.random.default_rng(0)
    X = rng.normal(0, 1, size=(200, 4)).astype(np.float32)
    coef = np.array([2.0, 1.0, 0.5, 3.0], dtype=np.float32)
    y = (X @ coef + 10.0).astype(np.float32)

    model = LinearRegression()
    model.fit(X, y)

    onnx_model = convert_sklearn(
        model,
        initial_types=[("float_input", FloatTensorType([None, 4]))],
        target_opset=12,
    )
    path.write_bytes(onnx_model.SerializeToString())


def test_onnx_model_predict_returns_numpy_array():
    with TemporaryDirectory() as td:
        model_path = Path(td) / "m.onnx"
        _make_tiny_onnx_model(model_path)

        model = ONNXModel(model_path)
        x = np.array([[12.5, 18, 5, 3]], dtype=np.float32)
        y = model.predict(x)

        assert isinstance(y, np.ndarray)
        assert y.shape[0] == 1


def test_inference_service_returns_float():
    with TemporaryDirectory() as td:
        model_path = Path(td) / "m.onnx"
        _make_tiny_onnx_model(model_path)

        model = ONNXModel(model_path)
        service = InferenceService(model=model)

        x = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
        minutes = service.predict(x)

        assert isinstance(minutes, float)


def test_onnx_model_rejects_wrong_shape():
    with TemporaryDirectory() as td:
        model_path = Path(td) / "m.onnx"
        _make_tiny_onnx_model(model_path)

        model = ONNXModel(model_path)
        bad = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)  # (4,)

        with pytest.raises(ValueError):
            model.predict(bad)

