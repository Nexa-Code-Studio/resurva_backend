import logging
import uuid

import mimetypes
from app.core.config import settings
from app.storage.interfaces.storage_provider import StorageProvider

logger = logging.getLogger(__name__)

try:
    import boto3  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
except ImportError:
    boto3 = None
    ClientError = Exception


class MinioStorageProvider(StorageProvider):
    def __init__(self):
        if boto3 is None:
            logger.warning("boto3 is not installed. MinioStorageProvider will run in mock mode.")
            self.client = None
            return

        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,  # Critical for MinIO
            region_name=settings.S3_REGION_NAME or "us-east-1"
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    async def upload_file(self, file_content: bytes, filename: str, folder: str = "") -> str:
        unique_name = f"{uuid.uuid4()}_{filename}"
        key = f"{folder}/{unique_name}" if folder else unique_name

        if not self.client:
            logger.info(f"[MOCK MINIO] Uploading file to minio://{settings.S3_BUCKET_NAME}/{key}")
            return key

        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "application/octet-stream"

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            return key
        except ClientError as e:
            logger.error(f"MinIO upload failed: {e}")
            raise Exception("Failed to upload file to MinIO")

    async def delete_file(self, file_path: str) -> bool:
        # Extract object key (handles both absolute URLs and relative paths)
        pub_endpoint = (getattr(settings, "S3_PUBLIC_URL", None) or "").rstrip("/")
        endpoint = (settings.S3_ENDPOINT_URL or "http://localhost:9000").rstrip("/")
        key = file_path
        if pub_endpoint:
            key = key.replace(f"{pub_endpoint}/{self.bucket_name}/", "")
        key = key.replace(f"{endpoint}/{self.bucket_name}/", "")
        if key.startswith("/"):
            key = key[1:]

        if not self.client:
            logger.info(f"[MOCK MINIO] Deleting file key: {key}")
            return True

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"MinIO delete failed: {e}")
            return False

    def get_file_url(self, file_path: str) -> str:
        if not file_path:
            return ""
        if file_path.startswith("http://") or file_path.startswith("https://"):
            return file_path
        base_url = (getattr(settings, "S3_PUBLIC_URL", None) or settings.S3_ENDPOINT_URL or "http://localhost:9000").rstrip("/")
        clean_path = file_path.lstrip("/")
        return f"{base_url}/{self.bucket_name}/{clean_path}"


