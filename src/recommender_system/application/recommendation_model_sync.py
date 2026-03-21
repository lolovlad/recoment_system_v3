from __future__ import annotations

import logging
import os
from pathlib import Path

from .services import ModelSyncService, ModelSyncSpec
from ..env import load_project_env
from ..infrastructure.recommendation_artifacts import (
    local_meta_path,
    local_onnx_path,
    remote_meta_key,
    remote_onnx_key,
)
from ..infrastructure.s3_storage import S3Storage

logger = logging.getLogger(__name__)


def ensure_recommendation_artifacts_local() -> tuple[Path, Path]:
    """
    Если ``recommendation.onnx`` и ``recommendation_meta.json`` уже есть локально (volume ``./models``),
    возвращает пути без сети.

    Иначе при настроенном MinIO пытается скачать объекты из бакета ``models``.
    При ошибке (объекта нет, сеть) **не бросает исключение** — worker сможет работать на mock.
    """
    load_project_env()
    onnx_path = local_onnx_path()
    meta_path = local_meta_path()

    if onnx_path.is_file() and meta_path.is_file():
        return onnx_path, meta_path

    remote_onnx = remote_onnx_key()
    remote_meta = remote_meta_key()

    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    bucket = os.getenv("MINIO_MODEL_BUCKET", "models")

    if not endpoint or not access_key or not secret_key:
        return onnx_path, meta_path

    storage = S3Storage(endpoint, access_key, secret_key, bucket)
    sync = ModelSyncService(storage=storage)
    try:
        sync.ensure_model_exists(ModelSyncSpec(remote_path=remote_onnx, local_path=str(onnx_path)))
        sync.ensure_model_exists(ModelSyncSpec(remote_path=remote_meta, local_path=str(meta_path)))
    except OSError as e:
        logger.warning("Recommendation artifacts sync skipped or failed: %s", e)
    except Exception as e:
        logger.warning("Recommendation artifacts could not be downloaded from MinIO: %s", e)
    return onnx_path, meta_path
