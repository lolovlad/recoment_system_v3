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
    recommender = FakeRecommender()
    service = RecommendationService(recommender)

    history = UserHistory(
        user_id="u1",
        last_items=["itemA", "itemC"]
    )

    result = service.get_recommendations(history)

    assert result.suggested_items == ["itemB"]