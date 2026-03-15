from src.recommender_system.application.recommendation_service import RecommendationService
from src.recommender_system.domain.entities import UserHistory, Recommendation
from src.recommender_system.domain.interfaces import Recommender


class FakeRecommender(Recommender):
    def get_recommendations(self, history: UserHistory) -> Recommendation:
        return Recommendation(
            suggested_items=["itemA", "itemB", "itemC"],
            engine_version="test"
        )


def test_service_filters_purchased_items():
    """Сервис исключает из рекомендаций товары, уже есть в last_items."""
    recommender = FakeRecommender()
    service = RecommendationService(recommender)

    history = UserHistory(
        user_id="u1",
        last_items=["itemA", "itemC"]
    )

    result = service.get_recommendations(history)

    assert result.suggested_items == ["itemB"]
    assert result.engine_version == "test"


def test_service_passes_engine_version_through():
    """Поле engine_version из Recommender передаётся в итоговый результат."""
    recommender = FakeRecommender()
    service = RecommendationService(recommender)

    history = UserHistory(user_id="u1", last_items=[])
    result = service.get_recommendations(history)

    assert result.engine_version == "test"


def test_empty_last_items_returns_all_recommendations():
    """Если last_items пуст — фильтрация не требуется, возвращаются все рекомендации."""
    recommender = FakeRecommender()
    service = RecommendationService(recommender)

    history = UserHistory(user_id="u1", last_items=[])

    result = service.get_recommendations(history)

    assert result.suggested_items == ["itemA", "itemB", "itemC"]
    assert result.engine_version == "test"


def test_all_recommended_already_in_history_returns_empty_list():
    """Если все рекомендованные товары уже в истории — возвращается пустой список."""
    recommender = FakeRecommender()
    service = RecommendationService(recommender)

    history = UserHistory(
        user_id="u1",
        last_items=["itemA", "itemB", "itemC"]
    )

    result = service.get_recommendations(history)

    assert result.suggested_items == []
    assert result.engine_version == "test"


def test_filtering_not_needed_when_no_overlap():
    """Когда last_items не пересекаются с рекомендациями — возвращается полный список."""
    recommender = FakeRecommender()
    service = RecommendationService(recommender)

    history = UserHistory(
        user_id="u1",
        last_items=["other1", "other2"]
    )

    result = service.get_recommendations(history)

    assert result.suggested_items == ["itemA", "itemB", "itemC"]
    assert result.engine_version == "test"