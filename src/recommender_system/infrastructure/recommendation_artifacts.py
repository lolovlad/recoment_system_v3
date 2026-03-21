"""
Фиксированные имена файлов рекомендаций (ЛР4).

Локально: ``models/recommendation.onnx`` + ``models/recommendation_meta.json``.
В MinIO бакет ``models`` (``MINIO_MODEL_BUCKET``): те же имена как ключи объектов.
Без переменных окружения для путей/ключей.
"""
from __future__ import annotations

from pathlib import Path

# Каталог относительно корня проекта (рабочий каталог при запуске)
MODELS_DIR = Path("models")

ONNX_FILENAME = "recommendation.onnx"
META_FILENAME = "recommendation_meta.json"


def local_onnx_path() -> Path:
    return MODELS_DIR / ONNX_FILENAME


def local_meta_path() -> Path:
    return MODELS_DIR / META_FILENAME


# Ключи в S3/MinIO (бакет models)
def remote_onnx_key() -> str:
    return ONNX_FILENAME


def remote_meta_key() -> str:
    return META_FILENAME
