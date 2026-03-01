from ..domain.entities import UserHistory, Recommendation
from ..domain.interfaces import Recommender


class RecommendationService:

    def __init__(self, recommender: Recommender):
        self.recommender = recommender

    def get_recommendations(self, history: UserHistory) -> Recommendation:
        result = self.recommender.get_recommendations(history)

        filtered = [
            item for item in result.suggested_items
            if item not in history.last_items
        ]

        return Recommendation(
            suggested_items=filtered,
            engine_version=result.engine_version
        )