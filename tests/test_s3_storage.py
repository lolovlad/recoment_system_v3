import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from botocore.exceptions import ClientError

from src.recommender_system.infrastructure.s3_storage import S3Storage


@pytest.fixture
def mock_s3_client():
    """Фикстура для создания мока S3 клиента."""
    with patch('src.recommender_system.infrastructure.s3_storage.boto3') as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        yield mock_client


@pytest.fixture
def s3_storage(mock_s3_client):
    """Фикстура для создания S3Storage с моком."""
    return S3Storage(
        endpoint_url="http://localhost:9000",
        access_key="test_key",
        secret_key="test_secret",
        bucket_name="test_bucket"
    )


def test_s3_storage_initialization(mock_s3_client):
    """Тест: S3Storage правильно инициализируется."""
    storage = S3Storage(
        endpoint_url="http://localhost:9000",
        access_key="test_key",
        secret_key="test_secret",
        bucket_name="test_bucket"
    )
    
    assert storage.endpoint_url == "http://localhost:9000"
    assert storage.bucket_name == "test_bucket"
    assert storage.s3_client is not None


def test_s3_storage_download_file_success(s3_storage, mock_s3_client):
    """Тест: S3Storage успешно скачивает файл."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "data", "test.csv")
        remote_path = "test.csv"
        
        # Настраиваем мок для успешного скачивания
        def mock_download(Bucket, Key, Filename):
            Path(Filename).parent.mkdir(parents=True, exist_ok=True)
            Path(Filename).write_text("downloaded data")
        
        mock_s3_client.download_file.side_effect = mock_download
        
        s3_storage.download_file(remote_path, local_path)
        
        # Проверяем, что метод был вызван с правильными параметрами
        mock_s3_client.download_file.assert_called_once_with(
            s3_storage.bucket_name,
            remote_path,
            local_path
        )
        
        # Проверяем, что файл создан
        assert os.path.exists(local_path)
        assert Path(local_path).read_text() == "downloaded data"


def test_s3_storage_download_file_creates_directories(s3_storage, mock_s3_client):
    """Тест: S3Storage создает директории при скачивании."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "nested", "deep", "test.csv")
        remote_path = "test.csv"
        
        def mock_download(Bucket, Key, Filename):
            Path(Filename).write_text("data")
        
        mock_s3_client.download_file.side_effect = mock_download
        
        s3_storage.download_file(remote_path, local_path)
        
        # Проверяем, что директории созданы
        assert os.path.exists(os.path.dirname(local_path))


def test_s3_storage_download_file_handles_client_error(s3_storage, mock_s3_client):
    """Тест: S3Storage обрабатывает ошибки ClientError при скачивании."""
    remote_path = "test.csv"
    local_path = "/tmp/test.csv"
    
    # Настраиваем мок для выброса ошибки
    error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}}
    mock_s3_client.download_file.side_effect = ClientError(
        error_response, 'GetObject'
    )
    
    # Проверяем, что выбрасывается RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        s3_storage.download_file(remote_path, local_path)
    
    assert "Ошибка при скачивании файла" in str(exc_info.value)
    assert remote_path in str(exc_info.value)


def test_s3_storage_upload_file_success(s3_storage, mock_s3_client):
    """Тест: S3Storage успешно загружает файл."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "test.csv")
        remote_path = "test.csv"
        
        # Создаем файл для загрузки
        Path(local_path).write_text("upload data")
        
        s3_storage.upload_file(local_path, remote_path)
        
        # Проверяем, что метод был вызван с правильными параметрами
        mock_s3_client.upload_file.assert_called_once_with(
            local_path,
            s3_storage.bucket_name,
            remote_path
        )


def test_s3_storage_upload_file_handles_missing_file(s3_storage, mock_s3_client):
    """Тест: S3Storage выбрасывает FileNotFoundError для несуществующего файла."""
    local_path = "/nonexistent/file.csv"
    remote_path = "test.csv"
    
    # Проверяем, что выбрасывается FileNotFoundError
    with pytest.raises(FileNotFoundError) as exc_info:
        s3_storage.upload_file(local_path, remote_path)
    
    assert "Локальный файл не найден" in str(exc_info.value)
    assert local_path in str(exc_info.value)
    
    # Проверяем, что upload_file не был вызван
    mock_s3_client.upload_file.assert_not_called()


def test_s3_storage_upload_file_handles_client_error(s3_storage, mock_s3_client):
    """Тест: S3Storage обрабатывает ошибки ClientError при загрузке."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "test.csv")
        remote_path = "test.csv"
        
        # Создаем файл
        Path(local_path).write_text("data")
        
        # Настраиваем мок для выброса ошибки
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        mock_s3_client.upload_file.side_effect = ClientError(
            error_response, 'PutObject'
        )
        
        # Проверяем, что выбрасывается RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            s3_storage.upload_file(local_path, remote_path)
        
        assert "Ошибка при загрузке файла" in str(exc_info.value)
        assert local_path in str(exc_info.value)


def test_s3_storage_implements_idata_storage_interface(s3_storage):
    """Тест: S3Storage реализует интерфейс IDataStorage."""
    from src.recommender_system.domain.interfaces import IDataStorage
    
    assert isinstance(s3_storage, IDataStorage)
    assert hasattr(s3_storage, 'download_file')
    assert hasattr(s3_storage, 'upload_file')
    assert callable(s3_storage.download_file)
    assert callable(s3_storage.upload_file)
