import logging
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory

logger = logging.getLogger(__name__)

class IntrusionPlugin(BasePlugin):
    """
    Intrusion Detection Plugin Stub.
    Monitors Region of Interest (ROI) boundaries and virtual tripwires.
    """
    @property
    def name(self) -> str:
        return "intrusion"

    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        return []
