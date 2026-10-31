import logging
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory

logger = logging.getLogger(__name__)

class AbandonedObjectPlugin(BasePlugin):
    """
    Abandoned Object Detection Plugin Stub.
    Monitors if a portable object is stationary without an owner for > 15 minutes.
    """
    @property
    def name(self) -> str:
        return "abandoned_object"

    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        return []
