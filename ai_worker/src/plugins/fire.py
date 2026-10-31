import logging
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory

logger = logging.getLogger(__name__)

class FirePlugin(BasePlugin):
    """
    Fire Detection Plugin Stub.
    Analyzes visual pixel values for expanding red/orange fire flames.
    """
    @property
    def name(self) -> str:
        return "fire"

    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        return []
