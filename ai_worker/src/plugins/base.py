from abc import ABC, abstractmethod
from memory.object_memory import ObjectMemory
from engines.rule_engine import RuleEngine

class BasePlugin(ABC):
    """
    Abstract Base Class for all AI Security event detection plugins.
    Allows dynamic extension of system capabilities without editing core pipelines.
    """
    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifying name of the security rule plugin."""
        pass

    @abstractmethod
    def analyze(self, memory: ObjectMemory, frame_idx: int, video_id: str) -> list:
        """
        Executes behavioral analysis on object memory state.
        Returns a list of triggered event dicts:
        [
            {
                "type": str,
                "confidence": float,
                "severity": str,
                "involved_tracks": List[int],
                "details": str
            }
        ]
        """
        pass
