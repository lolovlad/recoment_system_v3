from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.recommender_system.application.services import ModelSyncService, ModelSyncSpec


def test_ensure_model_exists_downloads_when_missing():
    storage = MagicMock()
    service = ModelSyncService(storage=storage)

    spec = ModelSyncSpec(remote_path="delivery_estimator.onnx", local_path="models/delivery_estimator.onnx")

    with patch("src.recommender_system.application.services.os.path.exists", return_value=False):
        service.ensure_model_exists(spec)

    storage.download_file.assert_called_once_with(spec.remote_path, spec.local_path)


def test_ensure_model_exists_does_not_download_when_present():
    storage = MagicMock()
    service = ModelSyncService(storage=storage)

    spec = ModelSyncSpec(remote_path="delivery_estimator.onnx", local_path="models/delivery_estimator.onnx")

    with patch("src.recommender_system.application.services.os.path.exists", return_value=True):
        service.ensure_model_exists(spec)

    storage.download_file.assert_not_called()


def test_ensure_model_exists_raises_when_no_storage_and_missing():
    service = ModelSyncService(storage=None)
    spec = ModelSyncSpec(remote_path="delivery_estimator.onnx", local_path="models/delivery_estimator.onnx")

    with patch("src.recommender_system.application.services.os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            service.ensure_model_exists(spec)

