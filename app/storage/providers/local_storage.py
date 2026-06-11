import os
import uuid

import aiofiles

from app.core.config import settings
from app.storage.interfaces.storage_provider import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self):
        self.base_path = settings.LOCAL_STORAGE_PATH
        os.makedirs(self.base_path, exist_ok=True)

    async def upload_file(self, file_content: bytes, filename: str, folder: str = "") -> str:
        # Generate a unique prefix to prevent collisions
        unique_name = f"{uuid.uuid4()}_{filename}"

        # Determine destination path
        dest_folder = os.path.join(self.base_path, folder) if folder else self.base_path
        os.makedirs(dest_folder, exist_ok=True)

        file_path = os.path.join(dest_folder, unique_name)

        # Write content asynchronously
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        # Return path relative to base directory or public route
        relative_path = os.path.relpath(file_path, start=os.path.dirname(self.base_path))
        return relative_path

    async def delete_file(self, file_path: str) -> bool:
        # Check path safety (avoid path traversal attacks)
        real_path = os.path.realpath(file_path)
        base_real = os.path.realpath(self.base_path)

        # Check if the path is inside base path
        if not real_path.startswith(base_real):
            return False

        if os.path.exists(real_path) and os.path.isfile(real_path):
            os.remove(real_path)
            return True
        return False

    async def get_file_url(self, file_path: str) -> str:
        # Returns simple relative path; in production could append host url prefix
        return f"/{file_path}"
