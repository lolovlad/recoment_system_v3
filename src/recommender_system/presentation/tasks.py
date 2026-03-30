"""
Celery-задачи рекомендательной системы.

Модели/сервисы не пересоздаются на каждый вызов — используются синглтоны.
"""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..domain.entities import UserHistory
from ..env import load_project_env
from .celery_app import celery_app

logger = logging.getLogger(__name__)

_DEFAULT_HISTORY_CSV = Path("data") / "user_history.csv"


def _recommendation_top_n() -> int:
    load_project_env()
    return int(os.getenv("RECOMMENDATION_TOP_N", "5"))


@lru_cache(maxsize=1)
def _get_recommendation_service_singleton():
    """Синглтон RecommendationService (модель, MinIO, CSV — только в worker)."""
    from ..application.service_factory import create_recommendation_service

    return create_recommendation_service()


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


@celery_app.task(bind=True, name="recommendations.generate_for_user")
def generate_recommendations_for_user(self, user_id: int) -> list[int]:
    """
    Worker: по user_id загружает модель, строит кандидатов (каталог из обучения),
    прогоняет через модель (TruncatedSVD / mock), отбирает топ-N.
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
        return item_ids
    except Exception as e:
        logger.exception("Recommendation failed: %s", e)
        raise
