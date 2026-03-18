from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from ..application.services import InferenceService, ModelSyncService, ModelSyncSpec
from ..infrastructure.onnx_model import ONNXModel
from ..infrastructure.s3_storage import S3Storage

import os


@lru_cache
def get_inference_service() -> InferenceService:
    load_dotenv()

    model_path = os.getenv("MODEL_PATH", str(Path("models") / "delivery_estimator.onnx"))
    model_remote_path = os.getenv("MODEL_REMOTE_PATH", "delivery_estimator.onnx")

    # опционально: MinIO env
    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    # Для модели используем отдельный бакет `models` (по умолчанию).
    # MINIO_BUCKET остаётся для ЛР2 (datasets), а здесь читаем MINIO_MODEL_BUCKET.
    bucket = os.getenv("MINIO_MODEL_BUCKET", "models")

    storage = None
    if endpoint and access_key and secret_key and bucket:
        storage = S3Storage(endpoint, access_key, secret_key, bucket)

    sync = ModelSyncService(storage=storage)
    sync.ensure_model_exists(ModelSyncSpec(remote_path=model_remote_path, local_path=model_path))

    model = ONNXModel(model_path)
    return InferenceService(model=model)

