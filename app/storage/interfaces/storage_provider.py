from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    async def upload_file(self, file_content: bytes, filename: str, folder: str = "") -> str:
        """
        Uploads a file's content to the storage system and returns a public URL or path string.
        """
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """
        Deletes a file from the storage system.
        """
        pass

    @abstractmethod
    def get_file_url(self, file_path: str) -> str:

        """
        Retrieves a public URL or local path for accessing the file.
        """
        pass
