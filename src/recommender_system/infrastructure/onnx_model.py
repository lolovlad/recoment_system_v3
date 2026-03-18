from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort

from ..domain.interfaces import IModel


class ONNXModel(IModel):
    def __init__(self, model_path: str | Path):
        self.model_path = str(model_path)
        self._session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name

    def predict(self, input_data: np.ndarray) -> np.ndarray:
        if not isinstance(input_data, np.ndarray):
            raise TypeError("input_data must be a numpy.ndarray")
        if input_data.ndim != 2 or input_data.shape[1] != 4:
            raise ValueError("input_data must have shape (N, 4)")

        x = input_data.astype(np.float32, copy=False)
        outputs = self._session.run([self._output_name], {self._input_name: x})
        return np.asarray(outputs[0])

