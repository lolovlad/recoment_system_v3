import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from recommender_system.application.data_sync_service import DataSyncService
from recommender_system.env import load_project_env
from recommender_system.infrastructure.s3_storage import S3Storage

load_project_env()


def main():
    endpoint_url = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    bucket_name = os.getenv("MINIO_BUCKET_NAME", "datasets")
    
    # Пути к данным
    remote_path = "user_history.csv"
    local_path = "data/user_history.csv"
    
    print("=" * 50)
    print("Инициализация данных для системы рекомендаций")
    print("=" * 50)
    print(f"Endpoint: {endpoint_url}")
    print(f"Bucket: {bucket_name}")
    print(f"Remote path: {remote_path}")
    print(f"Local path: {local_path}")
    print()
    
    # Создаем хранилище и сервис синхронизации
    storage = S3Storage(
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        bucket_name=bucket_name
    )
    
    sync_service = DataSyncService(storage)

    try:
        sync_service.ensure_data_exists(remote_path, local_path)
        print()
        print("=" * 50)
        print("Инициализация завершена успешно!")
        print("=" * 50)
    except Exception as e:
        print()
        print("=" * 50)
        print(f"ОШИБКА: {e}")
        print("=" * 50)
        print()
        print("Убедитесь, что:")
        print("1. MinIO запущен (docker-compose up -d)")
        print("2. Бакет 'datasets' создан")
        print("3. Данные загружены в MinIO (dvc push)")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
