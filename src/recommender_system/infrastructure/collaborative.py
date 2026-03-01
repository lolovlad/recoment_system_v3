from ..domain.interfaces import Recommender
from ..domain.entities import *


class CollaborativeMockModel(Recommender):

    def get_recommendations(self, history: UserHistory) -> Recommendation:
        if not history.last_items:
            items = ["item_1", "item_2", "item_3"]
        else:
            items = [f"{history.last_items[0]}_related"]

        return Recommendation(
            suggested_items=items,
            engine_version="mock-v1"
        )