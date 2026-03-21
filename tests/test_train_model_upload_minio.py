from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_upload_model_to_minio_uses_models_bucket_by_default(monkeypatch, tmp_path: Path):
    from scripts.train_delivery_model import upload_model_to_minio

    model_path = tmp_path / "delivery_estimator.onnx"
    model_path.write_bytes(b"fake")

    monkeypatch.setenv("MINIO_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "ak")
    monkeypatch.setenv("MINIO_SECRET_KEY", "sk")
    monkeypatch.delenv("MINIO_MODEL_BUCKET", raising=False)
    monkeypatch.delenv("MODEL_REMOTE_PATH", raising=False)

    mock_client = MagicMock()
    with patch("scripts.train_delivery_model.boto3.client", return_value=mock_client) as mock_boto3_client:
        ok = upload_model_to_minio(model_path)

    assert ok is True
    mock_boto3_client.assert_called_once()
    mock_client.upload_file.assert_called_once_with(str(model_path), "models", "delivery_estimator.onnx")


def test_upload_model_to_minio_skips_when_env_missing(monkeypatch, tmp_path: Path):
    from scripts.train_delivery_model import upload_model_to_minio

    model_path = tmp_path / "delivery_estimator.onnx"
    model_path.write_bytes(b"fake")

    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
    monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)

    # Важно: upload_model_to_minio() вызывает load_project_env(), который может подтянуть
    # значения из локального .env. Для сценария "env отсутствует" отключаем это.
    with patch("scripts.train_delivery_model.load_project_env") as _mock_load_env, patch("scripts.train_delivery_model.boto3.client") as mock_boto3_client:
        ok = upload_model_to_minio(model_path)

    assert ok is False
    mock_boto3_client.assert_not_called()

