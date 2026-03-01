from abc import ABC, abstractmethod
from .entities import UserHistory, Recommendation


class Recommender(ABC):

    @abstractmethod
    def get_recommendations(self, history: UserHistory) -> Recommendation:
        pass