"""Фабрика для создания сервисов с правильной композицией зависимостей."""
from ..domain.interfaces import Recommender
from .recommendation_service import RecommendationService
from ..infrastructure.collaborative import CollaborativeMockModel


def create_recommendation_service(recommender: Recommender = None) -> RecommendationService:
    """
    Создает RecommendationService с дефолтной моделью или переданной.
    
    Args:
        recommender: Реализация Recommender. Если не указана, используется CollaborativeMockModel.
    
    Returns:
        RecommendationService с настроенными зависимостями
    """
    if recommender is None:
        recommender = CollaborativeMockModel()
    return RecommendationService(recommender=recommender)
