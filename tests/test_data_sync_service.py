import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.recommender_system.application.data_sync_service import DataSyncService
from src.recommender_system.domain.interfaces import IDataStorage


class FakeStorage(IDataStorage):
    def __init__(self):
        self.downloaded_files = []
        self.uploaded_files = []
    
    def download_file(self, remote_path: str, local_path: str) -> None:
        self.downloaded_files.append((remote_path, local_path))
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_text("test data")
    
    def upload_file(self, local_path: str, remote_path: str) -> None:
        self.uploaded_files.append((local_path, remote_path))


def test_data_sync_service_downloads_when_file_not_exists():
    storage = FakeStorage()
    service = DataSyncService(storage)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "data", "test.csv")
        remote_path = "test.csv"

        service.ensure_data_exists(remote_path, local_path)

        assert len(storage.downloaded_files) == 1
        assert storage.downloaded_files[0] == (remote_path, local_path)
        assert os.path.exists(local_path)
        assert Path(local_path).read_text() == "test data"


def test_data_sync_service_skips_download_when_file_exists():
    storage = FakeStorage()
    service = DataSyncService(storage)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "test.csv")
        remote_path = "test.csv"

        Path(local_path).write_text("existing data")

        service.ensure_data_exists(remote_path, local_path)

        assert len(storage.downloaded_files) == 0
        assert Path(local_path).read_text() == "existing data"


def test_data_sync_service_creates_directories():
    storage = FakeStorage()
    service = DataSyncService(storage)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "nested", "deep", "test.csv")
        remote_path = "test.csv"

        service.ensure_data_exists(remote_path, local_path)

        assert os.path.exists(os.path.dirname(local_path))
        assert os.path.exists(local_path)


def test_data_sync_service_uses_storage_interface():
    mock_storage = Mock(spec=IDataStorage)
    service = DataSyncService(mock_storage)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "test.csv")
        remote_path = "test.csv"

        def mock_download(remote, local):
            Path(local).write_text("mocked data")
        
        mock_storage.download_file.side_effect = mock_download
        
        service.ensure_data_exists(remote_path, local_path)

        mock_storage.download_file.assert_called_once_with(remote_path, local_path)
