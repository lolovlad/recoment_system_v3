import sys
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from application.recommendation_service import RecommendationService
from domain.entities import UserHistory, Recommendation
from domain.interfaces import Recommender


class FakeRecommender(Recommender):
    def get_recommendations(self, history: UserHistory) -> Recommendation:
        return Recommendation(
            suggested_items=["itemA", "itemB", "itemC"],
            engine_version="test"
        )


def test_service_filters_purchased_items():
    recommender = FakeRecommender()
    service = RecommendationService(recommender)

    history = UserHistory(
        user_id="u1",
        last_items=["itemA", "itemC"]
    )

    result = service.get_recommendations(history)

    assert result.suggested_items == ["itemB"]