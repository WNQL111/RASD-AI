import logging
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory

logger = logging.getLogger(__name__)

class CrowdPlugin(BasePlugin):
    """
    Crowd Density Analytics Plugin Stub.
    Monitors crowd levels and triggers warning if number of people > 10 in a small ROI.
    """
    @property
    def name(self) -> str:
        return "crowd"

    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        return []
