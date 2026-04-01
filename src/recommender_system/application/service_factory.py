"""Фабрика рекомендательного сервиса для Celery worker (модели, MinIO, данные). API её не импортирует."""
from __future__ import annotations

import os

from ..domain.interfaces import Recommender
from ..env import load_project_env
from .recommendation_model_sync import ensure_recommendation_artifacts_local
from .recommendation_service import RecommendationService
from ..infrastructure.collaborative import CollaborativeMockModel
from ..infrastructure.trained_recommender import TrainedRecommenderModel


def create_recommendation_service(recommender: Recommender | None = None) -> RecommendationService:
    """
    Создаёт RecommendationService.

    Если ``recommender`` не передан:
    - при наличии локальных ``recommendation.onnx`` + ``recommendation_meta.json`` (или после
      синхронизации из MinIO через ``ensure_recommendation_artifacts_local``) загружается
      ``TrainedRecommenderModel``;
    - иначе — ``CollaborativeMockModel`` (заглушка ЛР1).
    """
    if recommender is None:
        load_project_env()
        top_n = int(os.getenv("RECOMMENDATION_TOP_N", "5"))
        onnx_path, meta_path = ensure_recommendation_artifacts_local()
        if onnx_path.is_file() and meta_path.is_file():
            recommender = TrainedRecommenderModel(onnx_path, meta_path, top_n=top_n)
        else:
            recommender = CollaborativeMockModel()
    return RecommendationService(recommender=recommender)
