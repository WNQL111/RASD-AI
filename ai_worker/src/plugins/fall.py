import logging
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory

logger = logging.getLogger(__name__)

class FallPlugin(BasePlugin):
    """
    Fall Detection Plugin Stub.
    Identifies if a person's height-to-width ratio flips suddenly (horizontal bounding box)
    and remains stationary on the floor.
    """
    @property
    def name(self) -> str:
        return "fall"

    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        # Placeholder stub for future worker updates
        return []
