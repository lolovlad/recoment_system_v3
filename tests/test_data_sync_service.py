"""Тесты логики синхронизации DataSyncService (проверка наличия файла, вызов storage только при отсутствии)."""
from unittest.mock import MagicMock, patch

import pytest

from src.recommender_system.application.data_sync_service import DataSyncService


@pytest.fixture
def mock_storage():
    """Мок IDataStorage."""
    return MagicMock()


@pytest.fixture
def sync_service(mock_storage):
    return DataSyncService(storage=mock_storage)


def test_ensure_data_exists_calls_download_file_when_file_does_not_exist(sync_service, mock_storage):
    """Если файла нет (os.path.exists == False), вызывается storage.download_file."""
    remote_path = "data/user_history.csv"
    local_path = "data/user_history.csv"

    with patch("src.recommender_system.application.data_sync_service.os.path.exists", return_value=False):
        sync_service.ensure_data_exists(remote_path=remote_path, local_path=local_path)

    mock_storage.download_file.assert_called_once_with(remote_path, local_path)


def test_ensure_data_exists_does_not_call_download_file_when_file_exists(sync_service, mock_storage):
    """Если файл уже есть (os.path.exists == True), storage.download_file не вызывается."""
    remote_path = "data/user_history.csv"
    local_path = "data/user_history.csv"

    with patch("src.recommender_system.application.data_sync_service.os.path.exists", return_value=True):
        sync_service.ensure_data_exists(remote_path=remote_path, local_path=local_path)

    mock_storage.download_file.assert_not_called()


def test_ensure_data_exists_checks_correct_local_path(sync_service, mock_storage):
    """Проверяется именно переданный local_path."""
    remote_path = "s3/path/file.csv"
    local_path = "data/local_file.csv"

    with patch("src.recommender_system.application.data_sync_service.os.path.exists", return_value=False) as mock_exists:
        sync_service.ensure_data_exists(remote_path=remote_path, local_path=local_path)

    mock_exists.assert_called_with(local_path)
    mock_storage.download_file.assert_called_once_with(remote_path, local_path)
