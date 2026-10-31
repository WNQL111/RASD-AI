import logging
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory

logger = logging.getLogger(__name__)

class WeaponPlugin(BasePlugin):
    """
    Weapon Detection Plugin Stub.
    Monitors target visual object classes corresponding to firearms or cold weapons.
    """
    @property
    def name(self) -> str:
        return "weapon"

    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        return []
