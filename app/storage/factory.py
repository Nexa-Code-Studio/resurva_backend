from app.core.config import settings
from app.storage.interfaces.storage_provider import StorageProvider
from app.storage.providers.local_storage import LocalStorageProvider
from app.storage.providers.minio_storage import MinioStorageProvider
from app.storage.providers.s3_storage import S3StorageProvider


class StorageFactory:
    @staticmethod
    def get_storage_provider() -> StorageProvider:
        provider_name = settings.STORAGE_PROVIDER.lower()
        if provider_name == "local":
            return LocalStorageProvider()
        elif provider_name == "s3":
            return S3StorageProvider()
        elif provider_name == "minio":
            return MinioStorageProvider()
        else:
            raise ValueError(f"Unknown storage provider: {settings.STORAGE_PROVIDER}")
