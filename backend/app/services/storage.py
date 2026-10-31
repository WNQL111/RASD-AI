import os
import shutil
from abc import ABC, abstractmethod
from fastapi import UploadFile

def get_storage_dir() -> str:
    """
    Returns robust cross-platform storage directory for uploaded videos.
    Defaults to <project_root>/data/videos if STORAGE_PATH env var is not set.
    """
    env_path = os.getenv("STORAGE_PATH")
    if env_path:
        os.makedirs(env_path, exist_ok=True)
        return os.path.abspath(env_path)
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    default_dir = os.path.join(project_root, "data", "videos")
    os.makedirs(default_dir, exist_ok=True)
    return default_dir

class StorageInterface(ABC):
    @abstractmethod
    async def save_video(self, file: UploadFile, filename: str) -> str:
        """Saves a video file and returns its absolute file path."""
        pass

    @abstractmethod
    async def get_video(self, video_id: str) -> str:
        """Retrieves a video path by its ID."""
        pass

class LocalStorage(StorageInterface):
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    async def save_video(self, file: UploadFile, filename: str) -> str:
        os.makedirs(self.base_path, exist_ok=True)
        file_path = os.path.join(self.base_path, filename)
        
        # Reset file stream position before reading/saving
        try:
            file.file.seek(0)
        except Exception:
            pass

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return os.path.abspath(file_path)

    async def get_video(self, video_id: str) -> str:
        file_path = os.path.join(self.base_path, video_id)
        return os.path.abspath(file_path)

# Factory to get the active storage
def get_storage() -> StorageInterface:
    return LocalStorage(get_storage_dir())
