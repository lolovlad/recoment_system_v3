from __future__ import annotations

import os
from dataclasses import dataclass

from ..domain.interfaces import IDataStorage


@dataclass(frozen=True)
class ModelSyncSpec:
    remote_path: str
    local_path: str


class ModelSyncService:
    """Скачивание файла модели из S3-совместимого хранилища (используется в worker)."""

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
