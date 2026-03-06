import os
from ..domain.interfaces import IDataStorage


class DataSyncService:
    def __init__(self, storage: IDataStorage):
        self.storage = storage

    def ensure_data_exists(self, remote_path: str, local_path: str) -> None:
        if not os.path.exists(local_path):
            print(f"Локальные данные не найдены: {local_path}")
            print(f"Скачивание из хранилища: {remote_path}")
            self.storage.download_file(remote_path, local_path)
            print(f"Данные успешно скачаны в: {local_path}")
        else:
            print(f"Локальные данные уже существуют: {local_path}")
