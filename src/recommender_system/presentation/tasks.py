"""
Celery-задачи: рекомендации и (опционально) прогноз доставки.

Модели/сервисы не пересоздаются на каждый вызов — используются синглтоны.
"""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..application.service_factory import create_recommendation_service
from ..application.services import InferenceService, ModelSyncService, ModelSyncSpec
from ..domain.entities import DeliveryRequest, UserHistory
from ..env import load_project_env
from ..infrastructure.onnx_model import ONNXModel
from ..infrastructure.s3_storage import S3Storage
from .celery_app import celery_app

logger = logging.getLogger(__name__)

_DEFAULT_HISTORY_CSV = Path("data") / "user_history.csv"


def _recommendation_top_n() -> int:
    load_project_env()
    return int(os.getenv("RECOMMENDATION_TOP_N", "5"))


@lru_cache(maxsize=1)
def _get_recommendation_service_singleton():
    """Синглтон RecommendationService + CollaborativeMockModel (ЛР1)."""
    return create_recommendation_service()


@lru_cache(maxsize=1)
def _get_inference_service_singleton() -> InferenceService:
    """Синглтон ONNX InferenceService (ЛР3) — не загружать модель на каждый запрос."""
    load_project_env()

    model_path = os.getenv("MODEL_PATH", str(Path("models") / "delivery_estimator.onnx"))
    model_remote_path = os.getenv("MODEL_REMOTE_PATH", "delivery_estimator.onnx")
    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    bucket = os.getenv("MINIO_MODEL_BUCKET", "models")

    storage = None
    if endpoint and access_key and secret_key and bucket:
        storage = S3Storage(endpoint, access_key, secret_key, bucket)

    sync = ModelSyncService(storage=storage)
    sync.ensure_model_exists(ModelSyncSpec(remote_path=model_remote_path, local_path=model_path))

    model = ONNXModel(model_path)
    return InferenceService(model=model)


def _load_last_items_for_user(user_id: int, csv_path: Path | None = None) -> list[str]:
    """Читает историю пользователя из CSV; при отсутствии файла/строк — пустой список."""
    path = csv_path or _DEFAULT_HISTORY_CSV
    if not path.exists():
        logger.warning("user_history CSV not found at %s, using empty history", path)
        return []

    try:
        df = pd.read_csv(path)
        if "user_id" not in df.columns or "item_id" not in df.columns:
            logger.warning("CSV missing user_id/item_id columns")
            return []
        uid = str(user_id)
        df["user_id"] = df["user_id"].astype(str)
        subset = df[df["user_id"] == uid]
        if subset.empty:
            return []
        # последние взаимодействия как строки
        last = subset["item_id"].astype(str).tolist()
        return last[-50:]  # ограничение для размера
    except Exception as e:
        logger.exception("Failed to read user history: %s", e)
        return []


def _suggested_to_item_ids(suggested: list[str], max_items: int) -> list[int]:
    """Преобразует подсказки модели в список item_id (int), top-N."""
    out: list[int] = []
    for s in suggested[:max_items]:
        s = str(s).strip()
        if s.isdigit():
            out.append(int(s))
            continue
        m = re.search(r"(\d+)$", s)
        if m:
            out.append(int(m.group(1)))
        else:
            out.append(abs(hash(s)) % 1_000_000)
    return out


def _persist_recommendations_to_redis(task_id: str, item_ids: list[int]) -> None:
    """
    Сохраняет топ рекомендованных item_id в Redis (ключ по task_id).

    В pytest (CELERY_EAGER_TEST) и без валидного REDIS_URL запись пропускается.
    """
    load_project_env()
    if os.getenv("CELERY_EAGER_TEST", "").lower() in ("1", "true", "yes"):
        return
    url = os.getenv("REDIS_URL", "")
    if not url or url.startswith("memory://"):
        return
    try:
        import json

        import redis as redis_lib

        client = redis_lib.from_url(url, decode_responses=True)
        key = f"recommendations:items:{task_id}"
        ttl = int(os.getenv("RECOMMENDATION_REDIS_TTL_SECONDS", "86400"))
        client.setex(key, ttl, json.dumps(item_ids))
        logger.info("Stored %d item_ids in Redis key %s", len(item_ids), key)
    except Exception as e:
        logger.warning("Could not persist recommendations to Redis: %s", e)


@celery_app.task(bind=True, name="recommendations.generate_for_user")
def generate_recommendations_for_user(self, user_id: int) -> list[int]:
    """
    Worker: по user_id загружает модель, строит кандидатов (каталог из обучения),
    прогоняет через модель (TruncatedSVD / mock), отбирает топ-N, пишет результат в Redis.
    """
    if not isinstance(user_id, int) or user_id < 1:
        raise ValueError("user_id must be a positive integer")

    top_n = _recommendation_top_n()
    service = _get_recommendation_service_singleton()
    last_items = _load_last_items_for_user(user_id)
    history = UserHistory(user_id=str(user_id), last_items=last_items)

    try:
        rec = service.get_recommendations(history)
        item_ids = _suggested_to_item_ids(rec.suggested_items, top_n)
        task_id = getattr(self.request, "id", None) or ""
        if task_id:
            _persist_recommendations_to_redis(str(task_id), item_ids)
        return item_ids
    except Exception as e:
        logger.exception("Recommendation failed: %s", e)
        raise


@celery_app.task(bind=True, name="delivery.estimate_time")
def estimate_delivery_task(self, payload: dict[str, Any]) -> float:
    """
    Асинхронный прогноз времени доставки (ЛР3 модель) через ONNX.
    """
    req = DeliveryRequest.model_validate(payload)
    x = np.array(
        [[req.distance, req.hour, req.day_of_week, req.items_count]],
        dtype=np.float32,
    )
    service = _get_inference_service_singleton()
    return service.predict(x)
