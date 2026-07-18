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


class S3StorageProvider(StorageProvider):
    def __init__(self):
        if boto3 is None:
            logger.warning("boto3 is not installed. S3StorageProvider will run in mock mode.")
            self.client = None
            return

        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION_NAME
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    async def upload_file(self, file_content: bytes, filename: str, folder: str = "") -> str:
        unique_name = f"{uuid.uuid4()}_{filename}"
        key = f"{folder}/{unique_name}" if folder else unique_name

        if not self.client:
            logger.info(f"[MOCK S3] Uploading file to s3://{settings.S3_BUCKET_NAME}/{key}")
            return key

        try:
            # S3 client upload expects a file-like object or filepath, or we can use put_object
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType="application/octet-stream"
            )
            return key
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise Exception("Failed to upload file to S3")

    async def delete_file(self, file_path: str) -> bool:
        # Extract S3 key from URL or path
        prefix = f"https://{self.bucket_name}.s3.amazonaws.com/"
        key = file_path.replace(prefix, "")
        if key.startswith("/"):
            key = key[1:]

        if not self.client:
            logger.info(f"[MOCK S3] Deleting file key: {key}")
            return True

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    def get_file_url(self, file_path: str) -> str:
        if not file_path:
            return ""
        if file_path.startswith("http://") or file_path.startswith("https://"):
            return file_path
        clean_path = file_path.lstrip("/")
        return f"https://{self.bucket_name}.s3.amazonaws.com/{clean_path}"

