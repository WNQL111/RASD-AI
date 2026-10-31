import logging
from typing import Any, Optional, Dict, List
from plugins.base import BasePlugin
from memory.object_memory import ObjectMemory
from domains.violence.detector import ViolenceDomainDetector

logger = logging.getLogger(__name__)

class ViolencePlugin(BasePlugin):
    def __init__(self, rule_engine):
        super().__init__(rule_engine)
        self.domain_detector = ViolenceDomainDetector(rule_engine=rule_engine)
        self.violence_state = self.domain_detector.temporal_tracker.state_acc

    @property
    def name(self) -> str:
        return 'violence'

    def analyze(
        self,
        memory: ObjectMemory,
        frame_idx: int,
        video_id: str,
        crowd_features: dict = None,
        pose_data: list = None,
        pose_data_map: dict = None,
        verifier_3d: Any = None,
        **kwargs
    ) -> list:
        return self.domain_detector.process_frame(
            memory=memory,
            frame_idx=frame_idx,
            video_id=video_id,
            crowd_features=crowd_features,
            pose_data=pose_data or pose_data_map,
            verifier_3d=verifier_3d
        )
