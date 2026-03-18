from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

from ..domain.interfaces import IModel, IDataStorage


class InferenceService:
    def __init__(self, model: IModel):
        self._model = model

    def predict(self, input_data: np.ndarray) -> float:
        preds = self._model.predict(input_data)
        flat = np.asarray(preds).reshape(-1)
        return float(flat[0])


@dataclass(frozen=True)
class ModelSyncSpec:
    remote_path: str
    local_path: str


class ModelSyncService:
    """
    Отдельный use-case для синхронизации файла модели.
    Не конфликтует с DataSyncService из ЛР2 (данные user_history.csv).
    """

    def __init__(self, storage: IDataStorage | None):
        self._storage = storage

    def ensure_model_exists(self, spec: ModelSyncSpec) -> None:
        if os.path.exists(spec.local_path):
            return

        if self._storage is None:
            raise FileNotFoundError(
                f"Model not found at {spec.local_path}. "
                f"Storage is not configured, cannot download {spec.remote_path}."
            )

        self._storage.download_file(spec.remote_path, spec.local_path)

