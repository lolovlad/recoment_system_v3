import os
import boto3
from botocore.exceptions import ClientError
from ..domain.interfaces import IDataStorage


class S3Storage(IDataStorage):
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str
    ):
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

    def download_file(self, remote_path: str, local_path: str) -> None:
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(
                self.bucket_name,
                remote_path,
                local_path
            )
        except ClientError as e:
            raise RuntimeError(f"Ошибка при скачивании файла {remote_path}: {e}")

    def upload_file(self, local_path: str, remote_path: str) -> None:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Локальный файл не найден: {local_path}")
        
        try:
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                remote_path
            )
        except ClientError as e:
            raise RuntimeError(f"Ошибка при загрузке файла {local_path}: {e}")
