import logging
from typing import Optional, Dict, Any, List
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory
from domains.collision.detector import CollisionDomainDetector

logger = logging.getLogger(__name__)

class CollisionPlugin(BasePlugin):
    """
    Collision Domain Plugin Adapter.
    Thin integration adapter connecting core ASIS-V2 pipeline to isolated CollisionDomainDetector.
    """
    def __init__(self, rule_engine: Any = None):
        super().__init__(rule_engine)
        self.domain_detector = CollisionDomainDetector(rule_engine=rule_engine)

    @property
    def name(self) -> str:
        return "collision"

    def analyze(
        self,
        memory: ObjectMemory,
        frame_idx: int,
        video_id: str,
        crowd_features: Optional[Dict[str, Any]] = None,
        camera_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        return self.domain_detector.process_frame(
            memory=memory,
            frame_idx=frame_idx,
            video_id=video_id,
            crowd_features=crowd_features,
            camera_context=camera_context,
            verifier_3d=kwargs.get('verifier_3d')
        )
