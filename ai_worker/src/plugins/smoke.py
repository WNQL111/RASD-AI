import logging
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory

logger = logging.getLogger(__name__)

class SmokePlugin(BasePlugin):
    """
    Smoke Detection Plugin Stub.
    Analyzes visual pixel values for expanding gray/opaque regions.
    """
    @property
    def name(self) -> str:
        return "smoke"

    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        return []
