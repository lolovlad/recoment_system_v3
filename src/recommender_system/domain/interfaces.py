from abc import ABC, abstractmethod
from .entities import UserHistory, Recommendation


class Recommender(ABC):

    @abstractmethod
    def get_recommendations(self, history: UserHistory) -> Recommendation:
        pass


class IDataStorage(ABC):

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> None:
        pass
