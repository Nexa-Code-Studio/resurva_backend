import logging
import uuid

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
            return f"{settings.S3_ENDPOINT_URL or 'http://localhost:9000'}/{settings.S3_BUCKET_NAME}/{key}"

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType="application/octet-stream"
            )
            endpoint = (settings.S3_ENDPOINT_URL or "http://localhost:9000").rstrip("/")
            return f"{endpoint}/{self.bucket_name}/{key}"
        except ClientError as e:
            logger.error(f"MinIO upload failed: {e}")
            raise Exception("Failed to upload file to MinIO")

    async def delete_file(self, file_path: str) -> bool:
        # Extract object key
        endpoint = (settings.S3_ENDPOINT_URL or "http://localhost:9000").rstrip("/")
        prefix = f"{endpoint}/{self.bucket_name}/"
        key = file_path.replace(prefix, "")

        if not self.client:
            logger.info(f"[MOCK MINIO] Deleting file key: {key}")
            return True

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"MinIO delete failed: {e}")
            return False

    async def get_file_url(self, file_path: str) -> str:
        return file_path
